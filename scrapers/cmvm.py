"""
Scraper do universo CMVM PPRList.

A página investidor.cmvm.pt/pinvestidor/PPRList é SPA (JS-rendered),
mas os dados vêm de um endpoint XHR. Para o descobrir:

1. Abrir https://investidor.cmvm.pt/pinvestidor/PPRList
2. DevTools → Network → filtrar XHR
3. Copiar o request que devolve a lista de PPR
4. Replicar em Python com requests

Este endpoint devolve todos os PPR registados na CMVM com:
- Nome, ISIN, entidade gestora, TEC, subscrição mínima, classe de risco

Output: atualiza universe.py com a lista completa.
"""
import requests
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# TODO: descobrir via DevTools. Placeholder:
CMVM_API = "https://investidor.cmvm.pt/pinvestidor/api/PPRList"


def fetch_ppr_list() -> list[dict]:
    """Puxa lista de PPR da API CMVM."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://investidor.cmvm.pt/pinvestidor/PPRList",
    }
    try:
        r = requests.get(CMVM_API, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[cmvm] ERROR: {e}")
        print("Descobre o endpoint real via DevTools → Network na página PPRList")
        return []


def filter_fundos_investimento(all_ppr: list[dict]) -> list[dict]:
    """Filtra apenas PPR sob forma de fundo de investimento."""
    # Ajustar conforme a estrutura da resposta real
    return [p for p in all_ppr if "fundo" in p.get("tipo", "").lower()]


def run():
    data = fetch_ppr_list()
    if not data:
        return []

    fundos = filter_fundos_investimento(data)
    print(f"[cmvm] {len(fundos)} PPR fundos de investimento encontrados")

    # Guardar snapshot bruto
    (DATA_DIR / "cmvm_ppr_list.json").write_text(
        json.dumps(fundos, indent=2, ensure_ascii=False)
    )

    # TODO: merge com universe.py preservando overrides manuais
    return fundos


if __name__ == "__main__":
    run()
