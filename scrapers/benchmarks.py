"""
Scraper para ETFs benchmark usados como referência por nível de risco.

Mapeamento PPR risk_class → ETF:
  risk_class 2   → V20A  (Vanguard LifeStrategy 20% Equity, Amsterdam)
  risk_class 3   → V40A  (Vanguard LifeStrategy 40% Equity, Milan)
  risk_class 4   → V60A  (Vanguard LifeStrategy 60% Equity, Amsterdam)
  risk_class 5   → V80A  (Vanguard LifeStrategy 80% Equity, Amsterdam)
  risk_class 6-7 → IWDA  (iShares Core MSCI World UCITS ETF Acc)

Usa scrapers/investing.py como transport (API Investing.com via curl_cffi).
"""
from pathlib import Path
import pandas as pd

from scrapers import investing

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARKS = {
    "V20A": {"pair_id": 1188907, "name": "Vanguard LifeStrategy 20% Equity (EUR)", "risk": [1, 2]},
    "V40A": {"pair_id": 1168631, "name": "Vanguard LifeStrategy 40% Equity (EUR)", "risk": [3]},
    "V60A": {"pair_id": 1188924, "name": "Vanguard LifeStrategy 60% Equity (EUR)", "risk": [4]},
    "V80A": {"pair_id": 1188906, "name": "Vanguard LifeStrategy 80% Equity (EUR)", "risk": [5]},
    "IWDA": {"pair_id": 47285,   "name": "iShares Core MSCI World (EUR)",          "risk": [6, 7]},
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


def run() -> dict[str, pd.Series]:
    """Descarrega cotações diárias dos 5 ETFs. Retorna {ticker: Close Series}."""
    results: dict[str, pd.Series] = {}
    for ticker, info in BENCHMARKS.items():
        print(f"[bench] {ticker} ({info['name']}) pair_id={info['pair_id']}...")
        try:
            df = investing.fetch_history(info["pair_id"], start="2010-01-01")
            if df.empty:
                print(f"[bench]   sem dados")
                continue
            s = df["Close"].dropna().sort_index()
            results[ticker] = s
            df.to_csv(DATA_DIR / f"{ticker}.csv")
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
