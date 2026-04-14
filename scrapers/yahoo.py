"""
Scraper de cotacoes historicas via Yahoo Finance.

Usa yfinance. Para fundos PPR portugueses, o ticker tipicamente segue
o formato `0P...F` (Morningstar ID + sufixo .F).

Ex: Invest Alves Ribeiro PPR = 0P000011IR.F
"""
import time
import pandas as pd
import yfinance as yf
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_history(ticker: str, period: str = "10y") -> pd.DataFrame:
    """
    Puxa histórico de cotações para um ticker Yahoo.

    Returns DataFrame com colunas: Date (index), Close.
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, auto_adjust=False)
        if hist.empty:
            print(f"[yahoo] WARN: sem dados para {ticker}")
            return pd.DataFrame()
        df = hist[["Close"]].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except Exception as e:
        print(f"[yahoo] ERROR {ticker}: {e}")
        return pd.DataFrame()


def search_ticker_by_isin(isin: str) -> str | None:
    """
    Usa endpoint de search do Yahoo para mapear ISIN → ticker.
    Retorna None se nao encontrar.
    """
    import requests
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        quotes = data.get("quotes", [])
        for q in quotes:
            symbol = q.get("symbol", "")
            if symbol.startswith("0P") and symbol.endswith(".F"):
                return symbol
        return quotes[0]["symbol"] if quotes else None
    except Exception as e:
        print(f"[yahoo search] ERROR {isin}: {e}")
        return None


def run(funds: list[dict]) -> dict[str, pd.DataFrame]:
    """
    Puxa cotacoes para todos os fundos com source=yahoo.
    Returns dict: {fund_id: DataFrame}
    """
    results = {}
    for f in funds:
        if f.get("source") != "yahoo":
            continue
        ticker = f.get("yahoo_ticker")
        if not ticker and f.get("isin"):
            print(f"[yahoo] procurando ticker para ISIN {f['isin']}...")
            ticker = search_ticker_by_isin(f["isin"])
            if ticker:
                print(f"[yahoo]   encontrado: {ticker}")
        if not ticker:
            print(f"[yahoo] skip {f['id']} (sem ticker)")
            continue

        print(f"[yahoo] {f['id']} ({ticker})...")
        df = fetch_history(ticker)
        if not df.empty:
            results[f["id"]] = df
            df.to_csv(DATA_DIR / f"{f['id']}.csv")
        time.sleep(1)  # politeness

    return results


if __name__ == "__main__":
    from universe import get_funds
    run(get_funds())
