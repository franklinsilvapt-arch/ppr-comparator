"""
Scraper para ETFs benchmark usados como referência por nível de risco.

Mapeamento PPR risk_class → ETF:
  risk_class 1-2 → V20A  (Vanguard LifeStrategy 20% Equity)
  risk_class 3   → V40A  (Vanguard LifeStrategy 40% Equity)
  risk_class 4   → V60A  (Vanguard LifeStrategy 60% Equity)
  risk_class 5   → V80A  (Vanguard LifeStrategy 80% Equity)
  risk_class 6-7 → IWDA  (iShares Core MSCI World UCITS ETF Acc)

Fonte actual: Yahoo Finance (Amsterdam listing, sufixo .AS).
A Investing.com foi descartada porque bloqueia o IP range dos runners do
GitHub Actions (403) e matava o update semanal.

Histórico pré-Yahoo: `data/bench_seed/{ticker}.csv` (opcional). Usado
apenas para dates < primeira observação Yahoo. Actualmente só o V40A tem
seed relevante (2020-12-10 → 2021-02-17, ~2 meses que o Yahoo não cobre).
"""
from pathlib import Path
import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
SEED_DIR = Path(__file__).parent.parent / "data" / "bench_seed"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARKS = {
    "V20A": {"yahoo": "V20A.AS", "name": "Vanguard LifeStrategy 20% Equity (EUR)", "risk": [1, 2]},
    "V40A": {"yahoo": "V40A.AS", "name": "Vanguard LifeStrategy 40% Equity (EUR)", "risk": [3]},
    "V60A": {"yahoo": "V60A.AS", "name": "Vanguard LifeStrategy 60% Equity (EUR)", "risk": [4]},
    "V80A": {"yahoo": "V80A.AS", "name": "Vanguard LifeStrategy 80% Equity (EUR)", "risk": [5]},
    "IWDA": {"yahoo": "IWDA.AS", "name": "iShares Core MSCI World (EUR)",          "risk": [6, 7]},
}


def risk_to_ticker(risk_class) -> str | None:
    """Devolve o ticker do ETF de referência para um risk_class (1-7).
    Retorna None se a classe não estiver mapeada ou for None."""
    if risk_class is None:
        return None
    try:
        rc = int(risk_class)
    except (TypeError, ValueError):
        return None
    for ticker, info in BENCHMARKS.items():
        if rc in info["risk"]:
            return ticker
    return None


def _load_seed(ticker: str) -> pd.Series | None:
    """Carrega histórico pré-Yahoo de data/bench_seed/{ticker}.csv se existir."""
    p = SEED_DIR / f"{ticker}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    col = "Close" if "Close" in df.columns else df.columns[0]
    s = df[col].dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s.sort_index()


def run() -> dict[str, pd.Series]:
    """Descarrega cotações diárias dos 5 ETFs via Yahoo. Para dates < primeira
    observação Yahoo, completa com seed de data/bench_seed/ (Investing legacy).
    Yahoo sempre ganha no overlap — só se puxa seed para o tail anterior."""
    results: dict[str, pd.Series] = {}
    for ticker, info in BENCHMARKS.items():
        y_ticker = info["yahoo"]
        print(f"[bench] {ticker} ({info['name']}) yahoo={y_ticker}...")
        try:
            hist = yf.Ticker(y_ticker).history(period="max", auto_adjust=False)
            if hist.empty:
                print(f"[bench]   sem dados Yahoo")
                continue
            yahoo_s = hist["Close"].dropna()
            yahoo_s.index = pd.to_datetime(yahoo_s.index).tz_localize(None)
            yahoo_s = yahoo_s.sort_index()

            seed_s = _load_seed(ticker)
            if seed_s is not None and not seed_s.empty:
                yahoo_start = yahoo_s.index[0]
                seed_tail = seed_s[seed_s.index < yahoo_start]
                if len(seed_tail) > 0:
                    merged = pd.concat([seed_tail, yahoo_s]).sort_index()
                    merged = merged[~merged.index.duplicated(keep="last")]
                    print(f"[bench]   seed: +{len(seed_tail)} obs pre-{yahoo_start.date()} (Investing legacy)")
                    s = merged
                else:
                    s = yahoo_s
            else:
                s = yahoo_s

            results[ticker] = s
            s.to_frame("Close").to_csv(DATA_DIR / f"{ticker}.csv")
            print(f"[bench]   {len(s)} obs ({s.index[0].date()} a {s.index[-1].date()})")
        except Exception as e:
            print(f"[bench] ERROR {ticker}: {e}")
    return results


def load_cached() -> dict[str, pd.Series]:
    """Carrega as séries dos CSVs em data/raw/ (para recalc sem re-fetch)."""
    results: dict[str, pd.Series] = {}
    for ticker in BENCHMARKS:
        p = DATA_DIR / f"{ticker}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p, index_col=0, parse_dates=True)
        col = "Close" if "Close" in df.columns else df.columns[0]
        results[ticker] = df[col].dropna().sort_index()
    return results


if __name__ == "__main__":
    run()
