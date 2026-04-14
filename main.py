"""
Orchestrator principal. Corre:
1. Scrapers (Yahoo → Investing → Golden SGF)
2. Consolida dados
3. Calcula metricas
4. Escreve data/latest.json para consumo do embed Webflow
"""
import json
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from universe import get_funds
from scrapers import yahoo, investing, golden_sgf
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

    # 1. Scrape todas as fontes
    print("\n== YAHOO ==")
    yahoo_data = yahoo.run(funds)

    print("\n== INVESTING ==")
    investing_data = investing.run(funds)

    print("\n== GOLDEN SGF ==")
    sgf_data = golden_sgf.run(funds)

    all_prices = {**yahoo_data, **investing_data, **sgf_data}
    print(f"\nTotal fundos com dados: {len(all_prices)}/{len(funds)}")

    # 2. Benchmark
    print("\n== BENCHMARK ==")
    benchmark = load_benchmark()

    # 3. Calcular metricas e series
    output_funds = []
    latest_dates = []

    for f in funds:
        fid = f["id"]
        if fid not in all_prices:
            print(f"  skip {fid} (sem dados)")
            continue

        prices = all_prices[fid]["Close"] if "Close" in all_prices[fid].columns else all_prices[fid].iloc[:, 0]
        prices = prices.dropna().sort_index()
        if prices.empty:
            continue

        latest_dates.append(prices.index[-1])

        returns = calc_metrics.calc_returns(prices)
        risk = calc_metrics.calc_risk(prices, benchmark)

        series = {
            p: calc_metrics.build_chart_series(prices, p)
            for p in ["ytd", "1y", "3y", "5y"]
        }

        output_funds.append({
            "id": fid,
            "name": f["name"],
            "manager": f["manager"],
            "isin": f.get("isin"),
            "tec": f.get("tec"),
            "min_subs": f.get("min_subs"),
            "risk_class": f.get("risk_class"),
            "returns": returns,
            "risk": risk,
            "series": series,
            "last_price_date": prices.index[-1].strftime("%Y-%m-%d"),
        })

    # 4. Escrever JSON
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_as_of": min(latest_dates).strftime("%Y-%m-%d") if latest_dates else None,
        "latest_data_date": max(latest_dates).strftime("%Y-%m-%d") if latest_dates else None,
        "funds": output_funds,
    }

    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n✓ {OUTPUT} escrito ({len(output_funds)} fundos)")
    print(f"  Data dos dados: {output['data_as_of']} (mais antigo) → {output['latest_data_date']} (mais recente)")


if __name__ == "__main__":
    main()
