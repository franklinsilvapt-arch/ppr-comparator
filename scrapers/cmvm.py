"""
Scraper do universo CMVM PPRList.

A página investidor.cmvm.pt/pinvestidor/PPRList é OutSystems SPA. A lista
de PPR vem de um endpoint XHR POST. Replicado abaixo.

Output:
- data/raw/cmvm_ppr_list.json (snapshot bruto)
- lista de dicts com {Id, NUM_FUN, NOM_FUN, DES_TIP, REND_*, TAXA_TEC,
  PPRRiskClassId, ...}

Filtra "FUNDOS DE POUPANÇA-REFORMA HARMONIZADOS" (i.e. fundos de
investimento, exclui adesões coletivas / seguros).
"""
import requests
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CMVM_API = (
    "https://investidor.cmvm.pt/pinvestidor/screenservices/"
    "PInvestidor/Comparator/PPRList/DataActionGetPPRs"
)
CMVM_PAGE = "https://investidor.cmvm.pt/pinvestidor/PPRList"

# Estes valores foram capturados via DevTools. moduleVersion / apiVersion
# / OutSystems-Request-Token podem mudar quando a CMVM faz redeploy.
# Se começar a falhar, voltar a copiar o cURL do request DataActionGetPPRs.
MODULE_VERSION = "LFbypQlBH03EnErbeERS3g"
API_VERSION = "EZF5sU_aIF7FskAry+x05w"
OS_REQUEST_TOKEN = "2860846940243845"
CSRF_TOKEN = "T6C+9iB49TLra4jEsMeSckDMNhQ="


def _build_body(max_records: int = 1000) -> dict:
    return {
        "versionInfo": {
            "moduleVersion": MODULE_VERSION,
            "apiVersion": API_VERSION,
        },
        "viewName": "Comparator.PPRList",
        "screenData": {
            "variables": {
                "RiskClasses_Options": {"List": [], "EmptyListItem": {"Value": "", "Label": "", "ImageUrlOrIconClass": ""}},
                "ManagingEntities_Options": {"List": [], "EmptyListItem": {"Value": "", "Label": "", "ImageUrlOrIconClass": ""}},
                "FundTypes_Options": {"List": [], "EmptyListItem": {"Value": "", "Label": "", "ImageUrlOrIconClass": ""}},
                "TableSort": "NOM_FUN",
                "StartIndex": 0,
                "MaxRecords": max_records,
                "SelectedFilters": {
                    "FundTypes": {"List": [], "EmptyListItem": {"TIP_FUN": ""}},
                    "ManagingEntities": {"List": [], "EmptyListItem": {"NUM_ENT": 0}},
                    "RiskClasses": {"List": [], "EmptyListItem": {"PPRRiskClassId": 0}},
                    "SearchCode": "",
                },
                "Locale2": "",
                "ShowRiskClassHistoryPopUp": False,
                "PPRForPopUp": {
                    "Id": "0", "NUM_FUN": 0, "NUM_CPA": 0, "CAT_UPS": "", "NOM_FUN": "",
                    "TIP_FUN": "", "DES_TIP": "", "NUM_ENT": 0, "NOM_ENT": "",
                    "REND_YTD": "0", "HAS_REND_YTD": False, "REND_1Y": "0", "HAS_REND_1Y": False,
                    "REND_2Y": "0", "HAS_REND_2Y": False, "REND_3Y": "0", "HAS_REND_3Y": False,
                    "REND_5Y": "0", "HAS_REND_5Y": False, "REND_10Y": "0", "HAS_REND_10Y": False,
                    "ISRR": "0", "HAS_ISRR": False, "TAXA_TEC": "0", "HAS_TAXA_TEC": False,
                    "PPRRiskClassId": 0,
                    "CreatedOn": "1900-01-01T00:00:00", "ModifiedOn": "1900-01-01T00:00:00",
                    "IsSynced": False,
                },
            }
        },
        "clientVariables": {
            "PortalId": "2",
            "TD_2062_New": True,
            "TD_3562_New": True,
            "HasLocaleChanged": True,
            "Language": "pt-PT",
        },
    }


def fetch_ppr_list(max_records: int = 1000) -> dict:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=UTF-8",
        "Origin": "https://investidor.cmvm.pt",
        "Referer": CMVM_PAGE,
        "User-Agent": "Mozilla/5.0",
        "OutSystems-Request-Token": OS_REQUEST_TOKEN,
        "OutSystems-locale": "pt-PT",
        "X-CSRFToken": CSRF_TOKEN,
    }
    cookies = {
        "nr2Users": f"crf%3d{CSRF_TOKEN.replace('+', '%2b').replace('=', '%3d')}%3buid%3d0%3bunm%3d",
    }
    r = requests.post(
        CMVM_API,
        headers=headers,
        cookies=cookies,
        json=_build_body(max_records),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def filter_fundos_investimento(items: list[dict]) -> list[dict]:
    """Mantém apenas PPR fundos de investimento harmonizados."""
    return [
        p for p in items
        if "FUNDOS DE POUPANÇA-REFORMA HARMONIZADOS" in (p.get("DES_TIP") or "").upper()
        or "FUNDO" in (p.get("DES_TIP") or "").upper()
    ]


def run() -> list[dict]:
    try:
        data = fetch_ppr_list()
    except requests.HTTPError as e:
        sc = e.response.status_code if e.response is not None else "?"
        print(f"[cmvm] ERROR HTTP {sc}: {e}")
        if sc in (401, 403, 419):
            print(
                "[cmvm] CSRF/Request token provavelmente expiraram.\n"
                "       1) Abre https://investidor.cmvm.pt/pinvestidor/PPRList\n"
                "       2) DevTools > Network > XHR > DataActionGetPPRs\n"
                "       3) Copia os novos valores para MODULE_VERSION,\n"
                "          API_VERSION, OS_REQUEST_TOKEN, CSRF_TOKEN em\n"
                "          scrapers/cmvm.py"
            )
        return []
    except Exception as e:
        print(f"[cmvm] ERROR: {e}")
        return []

    items = data.get("data", {}).get("PPRList", {}).get("List", [])
    print(f"[cmvm] total PPR devolvidos: {len(items)}")

    fundos = filter_fundos_investimento(items)
    print(f"[cmvm] fundos de investimento (filtrado): {len(fundos)}")

    (DATA_DIR / "cmvm_ppr_list.json").write_text(
        json.dumps(fundos, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return fundos


if __name__ == "__main__":
    run()
