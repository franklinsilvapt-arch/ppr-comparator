"""
Scraper Investing.com via API moderna (api.investing.com).

Endpoint:
  GET https://api.investing.com/api/financialdata/historical/{pair_id}
      ?start-date=YYYY-MM-DD&end-date=YYYY-MM-DD&time-frame=Daily
      &add-missing-rows=false
  Headers: domain-id: www, Origin/Referer www.investing.com

Cloudflare é contornado com `curl_cffi` (TLS fingerprint de Chrome).

Como obter o pair_id de um fundo:
  1. Abre a página do fundo em www.investing.com
  2. DevTools > Network > XHR > clica num período do gráfico
  3. Vê o request /historical/{NUMERO} - esse NUMERO é o pair_id

Configuração do fund_id → pair_id está em MANUAL_OVERRIDES de universe.py
no campo `investing_pair_id`.
"""
import time
from datetime import date
from pathlib import Path
import pandas as pd

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

API_URL = "https://api.investing.com/api/financialdata/historical/{pair_id}"


def fetch_history(pair_id: str | int, start: str = "2010-01-01") -> pd.DataFrame:
    """Devolve DataFrame com Date (index) e Close para o pair_id pedido."""
    if cffi_requests is None:
        raise RuntimeError("curl_cffi não instalado. `pip install curl_cffi`")

    end = date.today().isoformat()
    params = {
        "start-date": start,
        "end-date": end,
        "time-frame": "Daily",
        "add-missing-rows": "false",
    }
    headers = {
        "domain-id": "www",
        "Origin": "https://www.investing.com",
        "Referer": "https://www.investing.com/",
    }
    r = cffi_requests.get(
        API_URL.format(pair_id=pair_id),
        params=params,
        headers=headers,
        impersonate="chrome120",
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json().get("data", [])
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        [
            {
                "Date": pd.to_datetime(row["rowDateTimestamp"]).tz_localize(None),
                "Close": float(row["last_closeRaw"]),
            }
            for row in rows
        ]
    )
    return df.set_index("Date").sort_index()


def run(funds: list[dict]) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}
    for f in funds:
        if f.get("source") != "investing":
            continue
        pair_id = f.get("investing_pair_id")
        if not pair_id:
            print(f"[investing] skip {f['id']} (sem investing_pair_id no override)")
            continue
        print(f"[investing] {f['id']} (pair_id={pair_id})...")
        try:
            df = fetch_history(pair_id)
            if df.empty:
                print(f"[investing]   sem dados")
                continue
            results[f["id"]] = df
            df.to_csv(DATA_DIR / f"{f['id']}.csv")
            print(f"[investing]   {len(df)} obs ({df.index[0].date()} a {df.index[-1].date()})")
        except Exception as e:
            print(f"[investing] ERROR {f['id']}: {e}")
        time.sleep(1.5)
    return results


if __name__ == "__main__":
    from universe import get_funds
    run(get_funds())
