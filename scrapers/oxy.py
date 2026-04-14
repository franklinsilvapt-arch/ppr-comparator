"""
Scraper da Oxy Capital public markets strategy.

A Oxy não publica cotações por categoria ao retalho; apenas a Categoria
DA (ISIN PTOXCUHM0006) é publicamente comercializada. A página
oxycapital.com/public-markets/ carrega um gráfico da performance
agregada da estratégia de public markets a partir de uma Google Sheet:

  https://docs.google.com/spreadsheets/d/<SHEET_ID>/gviz/tq?tqx=out:json&gid=0

As colunas relevantes: Year, Date (YYYY-MM-DD), Oxy Capital aggregate
(NAV indexado a 100 em 2018-12-28), MSCI Europe Small Cap Index, MSCI
ACWI. Usamos Oxy Capital aggregate como proxy para a cotação da Cat DA
(mensal). Tem limitações: parte do histórico anterior a 2022 é da
estratégia da Oxy (não do PPR), pois o PPR só foi constituído em
2022-12-21 e iniciou actividade em 2023-03-02.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SHEET_ID = "1RHn2DC4olj4XQmwnhdJj9loT1iKQYZR9Q61zUb52_dU"
GVIZ_URL = (
    "https://docs.google.com/spreadsheets/d/{sheet}/gviz/tq?tqx=out:json&gid=0"
)
OXY_CAT_DA_ISIN = "PTOXCUHM0006"
# O PPR foi constituído em 2022-12-21 e iniciou actividade em 2023-03-02.
# A série na Google Sheet começa em 2018 (track record da estratégia
# agregada Oxy public markets), mas só a partir da constituição é que
# reflecte o PPR propriamente dito. Cortamos aqui.
OXY_PPR_START = "2022-12-21"


def fetch_aggregate_series() -> pd.DataFrame:
    """Devolve DataFrame com Date (index) e Close para a estratégia Oxy
    public markets aggregate (indexado a 100 em 2018-12-28)."""
    url = GVIZ_URL.format(sheet=SHEET_ID)
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    m = re.search(r"setResponse\((.+)\);?\s*$", r.text, re.DOTALL)
    if not m:
        raise RuntimeError("gviz response format inesperado")
    data = json.loads(m.group(1))
    rows = data.get("table", {}).get("rows", [])
    dates = []
    closes = []
    for row in rows:
        cells = row.get("c") or []
        if len(cells) < 3:
            continue
        d = cells[1] and cells[1].get("v")
        v = cells[2] and cells[2].get("v")
        if not d or v is None:
            continue
        dates.append(pd.to_datetime(d))
        closes.append(float(v))
    if not dates:
        return pd.DataFrame()
    return (
        pd.DataFrame({"Date": dates, "Close": closes})
        .set_index("Date")
        .sort_index()
    )


def run(funds: list[dict], already_fetched: set | None = None) -> dict[str, pd.DataFrame]:
    """Aplica a série Oxy aggregate aos fundos cujo ISIN é o da Cat DA.
    Esperamos um único match (Cat DA); outras cats são `hidden=True` em
    universe.py e não aparecem no embed."""
    already = already_fetched or set()
    results: dict[str, pd.DataFrame] = {}
    targets = [f for f in funds if f.get("isin") == OXY_CAT_DA_ISIN and f["id"] not in already]
    if not targets:
        return results
    try:
        df = fetch_aggregate_series()
    except Exception as e:
        print(f"[oxy] ERROR: {e}")
        return results
    if df.empty:
        print("[oxy] sheet vazia")
        return results
    # Corta para o PPR, rebaseia a 100 na 1ª cotação pós-constituição
    df = df[df.index >= pd.Timestamp(OXY_PPR_START)]
    if df.empty:
        print("[oxy] sem dados pós-constituição")
        return results
    df = df / df.iloc[0] * 100
    for f in targets:
        results[f["id"]] = df
        df.to_csv(DATA_DIR / f"{f['id']}.csv")
        print(f"[oxy] {f['id']} <- aggregate sheet ({len(df)} obs, "
              f"{df.index[0].date()} a {df.index[-1].date()})")
    return results


if __name__ == "__main__":
    from universe import get_funds
    run(get_funds())
