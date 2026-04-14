"""
Scraper fallback para Investing.com.

Investing.com tem proteção Cloudflare - temos de usar curl_cffi para
fazer TLS fingerprint de browser real.

O endpoint de historical data devolve JSON com OHLC diários.
"""
import time
import re
import json
import pandas as pd
from pathlib import Path

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_fund_page(url: str) -> str:
    """Puxa HTML da pagina do fundo usando curl_cffi (bypass Cloudflare)."""
    if cffi_requests is None:
        raise RuntimeError("curl_cffi não instalado. `pip install curl_cffi`")
    r = cffi_requests.get(url, impersonate="chrome120", timeout=20)
    r.raise_for_status()
    return r.text


def extract_pair_id(html: str) -> str | None:
    """
    Investing.com usa um pair_id interno para o endpoint de histórico.
    Extrai-o do HTML (normalmente aparece em data-pair-id ou num script).
    """
    m = re.search(r'data-pair-id="(\d+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'pairId["\']?\s*[:=]\s*["\']?(\d+)', html)
    if m:
        return m.group(1)
    return None


def fetch_history(investing_url: str) -> pd.DataFrame:
    """
    Puxa histórico completo. Retorna DataFrame com Date (index) e Close.

    NOTA: o endpoint exato muda ao longo do tempo. Abre DevTools → Network
    na página do fundo, clica "1 Year" no gráfico, e inspeciona o XHR.
    Replica aqui. Atualmente (2026) é algo como:
      POST /instruments/HistoricalDataAjax
      com form data: curr_id, smlID, header, st_date, end_date, interval_sec, action
    """
    html = fetch_fund_page(investing_url)
    pair_id = extract_pair_id(html)
    if not pair_id:
        print(f"[investing] WARN: pair_id não encontrado em {investing_url}")
        return pd.DataFrame()

    # TODO: replicar o endpoint exato via inspeccao DevTools.
    # Placeholder - precisa ser implementado com base em request real.
    print(f"[investing] pair_id={pair_id} - implementar chamada ao endpoint histórico")
    return pd.DataFrame()


def run(funds: list[dict]) -> dict[str, pd.DataFrame]:
    results = {}
    for f in funds:
        if f.get("source") != "investing":
            continue
        url = f.get("investing_url")
        if not url:
            continue
        print(f"[investing] {f['id']}...")
        try:
            df = fetch_history(url)
            if not df.empty:
                results[f["id"]] = df
                df.to_csv(DATA_DIR / f"{f['id']}.csv")
        except Exception as e:
            print(f"[investing] ERROR {f['id']}: {e}")
        time.sleep(2)
    return results


if __name__ == "__main__":
    from universe import get_funds
    run(get_funds())
