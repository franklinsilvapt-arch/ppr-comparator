"""
Scraper de cotações históricas via Financial Times (markets.ft.com).

A FT tem fichas para milhares de fundos PPR portugueses. Dado o ISIN,
a URL pública é:

  https://markets.ft.com/data/funds/tearsheet/charts?s={ISIN}:EUR

Essa página embute um identificador numérico interno (`symbol` no JSON
do `HistoricalPricesApp`), que é o que o endpoint de dados aceita:

  POST https://markets.ft.com/data/chartapi/series
  Body:
    { "days": 3650, "dataPeriod":"Day", "dataInterval":1,
      "timeServiceFormat":"JSON", "returnDateType":"ISO8601",
      "elements":[{"Type":"price","Symbol":"<FT_SYMBOL>",...}] }

Devolve `Dates` + `ComponentSeries` (Open/High/Low/Close).
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
import requests

from .sites import _get as _get_html

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TEARSHEET_HIST = "https://markets.ft.com/data/funds/tearsheet/historical?s={isin}:EUR"
TEARSHEET_CHART = "https://markets.ft.com/data/funds/tearsheet/charts?s={isin}:EUR"
CHARTAPI = "https://markets.ft.com/data/chartapi/series"

# A página historical publica o id numérico como data-mod-config={..."symbol":"NNNN"}.
# A charts publica-o via "xid":"NNNN". Tentamos ambos. Usamos o _get do
# scrapers.sites porque o servidor FT devolve HTML diferente consoante headers
# (o `requests` cru perde o bloco HistoricalPricesApp).
_ID_PATTERNS = [
    re.compile(r'HistoricalPricesApp[^}]*?"symbol"\s*:\s*"(\d+)"'),
    re.compile(r'"symbol"\s*:\s*"(\d+)"'),
    re.compile(r'"xid"\s*:\s*"(\d+)"'),
]


def resolve_ft_symbol(isin: str) -> str | None:
    """Dado um ISIN, devolve o símbolo numérico FT (ou None)."""
    for url in (TEARSHEET_HIST.format(isin=isin), TEARSHEET_CHART.format(isin=isin)):
        html = _get_html(url)
        if not html:
            continue
        for pat in _ID_PATTERNS:
            m = pat.search(html)
            if m:
                return m.group(1)
    return None


def fetch_history(ft_symbol: str, days: int = 3650) -> pd.DataFrame:
    """Devolve DataFrame com Date (index) e Close para o símbolo FT."""
    body = {
        "days": days,
        "dataNormalized": False,
        "dataPeriod": "Day",
        "dataInterval": 1,
        "realtime": False,
        "yFormat": "0.###",
        "timeServiceFormat": "JSON",
        "returnDateType": "ISO8601",
        "elements": [{
            "Label": "1",
            "Type": "price",
            "Symbol": ft_symbol,
            "OverlayIndicators": [],
            "Params": {},
        }],
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Referer": "https://markets.ft.com/",
        "Origin": "https://markets.ft.com",
    }
    r = requests.post(CHARTAPI, json=body, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"chartapi HTTP {r.status_code}: {r.text[:160]}")
    data = r.json()
    dates = data.get("Dates", [])
    elements = data.get("Elements") or []
    if not elements:
        return pd.DataFrame()
    comps = elements[0].get("ComponentSeries", [])
    close = next((c.get("Values", []) for c in comps if c.get("Type") == "Close"), [])
    if not dates or not close:
        return pd.DataFrame()
    df = pd.DataFrame({
        "Date": pd.to_datetime(dates),
        "Close": close,
    })
    return df.set_index("Date").sort_index()


def run(funds: list[dict], already_fetched: set | None = None) -> dict[str, pd.DataFrame]:
    """Tenta FT para todos os fundos com ISIN que ainda não tenham série
    histórica de outra fonte. `already_fetched` é o set de fund_ids já
    resolvidos por scrapers anteriores (yahoo/investing/golden_sgf) —
    saltados aqui para não duplicar.
    """
    results: dict[str, pd.DataFrame] = {}
    already = already_fetched or set()
    for f in funds:
        if f.get("id") in already:
            continue
        isin = f.get("isin")
        # Fontes já cobertas por scrapers dedicados — saltamos mesmo sem fetch
        # anterior (ex: investing ainda não corrido).
        dedicated = {"yahoo", "investing", "golden_sgf"}
        if f.get("source") in dedicated:
            continue
        if not isin:
            continue

        print(f"[ft] {f['id']} (ISIN {isin})...")
        try:
            sym = resolve_ft_symbol(isin)
            if not sym:
                print(f"[ft]   símbolo FT não encontrado para {isin}")
                continue
            df = fetch_history(sym)
            if df.empty:
                print(f"[ft]   {isin} sem dados")
                continue
            results[f["id"]] = df
            df.to_csv(DATA_DIR / f"{f['id']}.csv")
            print(f"[ft]   {len(df)} obs ({df.index[0].date()} → {df.index[-1].date()})")
        except Exception as e:
            print(f"[ft] ERROR {f['id']}: {e}")
        time.sleep(1.2)
    return results


if __name__ == "__main__":
    from universe import get_funds
    run(get_funds())
