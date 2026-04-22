"""
Orchestrator principal. Corre:
1. Scrapers (Yahoo → Investing → Golden SGF)
2. Consolida dados
3. Calcula metricas
4. Escreve data/latest.json para consumo do embed Webflow
"""
import json
import sys
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from universe import get_funds
from scrapers import yahoo, investing, golden_sgf, sites, ft, oxy
from scrapers import benchmarks as bench_module
import calc_metrics

DATA_DIR = Path(__file__).parent / "data"
OUTPUT = DATA_DIR / "latest.json"


def load_benchmark() -> pd.Series | None:
    """MSCI World EUR via Yahoo (URTH.DE ou similar)."""
    try:
        df = yahoo.fetch_history("URTH", period="10y")
        if df.empty:
            return None
        return df["Close"]
    except Exception as e:
        print(f"[benchmark] falha: {e}")
        return None


def main():
    funds = get_funds()
    print(f"Universo: {len(funds)} fundos")

    # 0. Scrape sites das gestoras (min_subs, isin, tec)
    print("\n== SITES GESTORAS ==")
    sites.run(funds)

    # 1. Scrape todas as fontes de cotações
    print("\n== YAHOO ==")
    yahoo_data = yahoo.run(funds)

    print("\n== INVESTING ==")
    investing_data = investing.run(funds)

    print("\n== GOLDEN SGF ==")
    sgf_data = golden_sgf.run(funds)

    print("\n== OXY CAPITAL ==")
    oxy_data = oxy.run(funds)

    print("\n== FINANCIAL TIMES ==")
    fetched_so_far = set(yahoo_data) | set(investing_data) | set(sgf_data) | set(oxy_data)
    ft_data = ft.run(funds, already_fetched=fetched_so_far)

    all_prices = {**yahoo_data, **investing_data, **sgf_data, **oxy_data, **ft_data}

    # Fallback: se um fundo não veio de nenhum scraper mas tem CSV em
    # data/history_cache/, usa esse histórico (evita perder fundos quando
    # a fonte primária falha — ex: Investing.com a bloquear o runner).
    # Regra do projecto: nunca apagar PPR da lista por falha de fetch.
    CACHE_DIR = DATA_DIR / "history_cache"
    if CACHE_DIR.exists():
        for f in funds:
            fid = f["id"]
            if fid in all_prices:
                continue
            cache_path = CACHE_DIR / f"{fid}.csv"
            if not cache_path.exists():
                continue
            try:
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                if not df.empty:
                    all_prices[fid] = df
                    src = f.get("source", "?")
                    last = df.index[-1].date()
                    print(f"[WARN] {fid}: fetch {src} falhou, a usar history_cache (last={last})")
            except Exception as e:
                print(f"[WARN] {fid}: cache read falhou: {e}")

    print(f"\nTotal fundos com dados: {len(all_prices)}/{len(funds)}")

    # 2. Benchmark
    print("\n== BENCHMARK ==")
    benchmark = load_benchmark()

    # 3. Calcular metricas e series
    output_funds = []
    latest_dates = []

    for f in funds:
        fid = f["id"]
        entry = {
            "id": fid,
            "name": f["name"],
            "manager": f["manager"],
            "isin": f.get("isin"),
            "tec": f.get("tec"),
            "min_subs": f.get("min_subs"),
            "risk_class": f.get("risk_class"),
            "source": f.get("source"),
            "cmvm_des_tip": f.get("cmvm_des_tip"),
            "fund_type": f.get("fund_type"),
            "prospectus_url": f.get("prospectus_url"),
            "notes": f.get("notes"),
            "hidden": bool(f.get("hidden")),
            "benchmark_ticker": f.get("benchmark_ticker_override") or bench_module.risk_to_ticker(f.get("risk_class")),
        }

        if fid in all_prices:
            prices = all_prices[fid]["Close"] if "Close" in all_prices[fid].columns else all_prices[fid].iloc[:, 0]
            prices = prices.dropna().sort_index()
            # Clipar ao último gap >60 dias: algumas categorias têm
            # histórico antigo da UP-mãe seguido de longa lacuna antes
            # da própria categoria arrancar. Ver comentário em
            # scripts/recalc_from_cache.py:_clip_after_major_gap.
            if len(prices) >= 2:
                deltas = prices.index.to_series().diff().dt.days
                big = deltas[deltas > 60]
                if not big.empty:
                    prices = prices.loc[big.index[-1]:]
            # Clip à data de constituição real se fornecida (útil quando o
            # scraper devolve a série NAV da família em vez da data de
            # criação da categoria específica).
            inc = f.get("inception")
            if inc:
                prices = prices[prices.index >= pd.Timestamp(inc)]
            if not prices.empty:
                # Só fundos visíveis contam para data_as_of. Hidden funds
                # (ex: BIZ Europa descontinuado em 2025-11) ficariam com
                # latest date antigo e puxariam o rodapé "Atualizado a..."
                # para uma data enganadora.
                if not bool(f.get("hidden")):
                    latest_dates.append(prices.index[-1])
                entry["returns"] = calc_metrics.calc_returns(prices)
                entry["risk"] = calc_metrics.calc_risk(prices, benchmark)
                entry["series"] = {
                    p: calc_metrics.build_chart_series(prices, p)
                    for p in ["ytd", "1y", "3y", "5y", "10y", "since"]
                }
                entry["last_price_date"] = prices.index[-1].strftime("%Y-%m-%d")
                entry["data_origin"] = "historical"
                output_funds.append(entry)
                continue

        # Fallback: usar métricas pré-calculadas pela CMVM
        m = f.get("cmvm_metrics")
        if m and any(v is not None for v in m.values()):
            entry["returns"] = {
                "ytd": m.get("ytd"),
                "1y": m.get("1y"),
                "3y": m.get("3y"),
                "5y": m.get("5y"),
                "10y": m.get("10y"),
                "since": m.get("10y") if m.get("10y") is not None else m.get("5y"),
                "ann": None,
            }
            entry["risk"] = {}
            entry["series"] = {}
            entry["last_price_date"] = None
            entry["data_origin"] = "cmvm"
            output_funds.append(entry)
        else:
            print(f"  skip {fid} (sem dados)")

    # Benchmark URTH (MSCI World) — referência para cálculo de Beta.
    bench_payload = None
    if benchmark is not None and not benchmark.empty:
        b = benchmark.dropna().sort_index()
        b = b[b.index >= pd.Timestamp("2015-01-01")]
        b.to_csv(DATA_DIR / "raw" / "URTH.csv")
        bench_payload = {
            "labels": [d.strftime("%Y-%m-%d") for d in b.index],
            "data": [round(float(v), 4) for v in b.values],
            "ticker": "URTH",
            "name": "MSCI World (iShares URTH, EUR)",
        }

    # ETFs de referência visual por nível de risco (LifeStrategy + IWDA).
    print("\n== BENCHMARK ETFs ==")
    try:
        bench_module.run()
    except Exception as e:
        print(f"[bench] fetch falhou: {e}; usar cache se disponível")
    cached_etfs = bench_module.load_cached()
    etf_payloads = {}
    for ticker, info in bench_module.BENCHMARKS.items():
        s = cached_etfs.get(ticker)
        if s is None or s.empty:
            continue
        s = s.sort_index()
        etf_payloads[ticker] = {
            "labels": [d.strftime("%Y-%m-%d") for d in s.index],
            "data": [round(float(v), 4) for v in s.values],
            "ticker": ticker,
            "name": info["name"],
            "risk": info["risk"],
        }

    # 4. Escrever JSON
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_as_of": min(latest_dates).strftime("%Y-%m-%d") if latest_dates else None,
        "latest_data_date": max(latest_dates).strftime("%Y-%m-%d") if latest_dates else None,
        "benchmark": bench_payload,
        "benchmarks": etf_payloads,
        "funds": output_funds,
    }

    DATA_DIR.mkdir(exist_ok=True)
    # allow_nan=False garante que Infinity/NaN fazem falhar aqui em vez
    # de gerar JSON inválido que o browser rejeita.
    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"\n✓ {OUTPUT} escrito ({len(output_funds)} fundos)")
    print(f"  Data dos dados: {output['data_as_of']} (mais antigo) → {output['latest_data_date']} (mais recente)")


if __name__ == "__main__":
    main()
