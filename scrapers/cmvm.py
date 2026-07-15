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
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class CMVMError(Exception):
    """Falha que deve abortar o pipeline em vez de esvaziar o universo."""


class CMVMTokensExpired(CMVMError):
    pass


class CMVMEmptyUniverse(CMVMError):
    pass


class CMVMFetchFailed(CMVMError):
    pass

CMVM_API = (
    "https://investidor.cmvm.pt/pinvestidor/screenservices/"
    "PInvestidor/Comparator/PPRList/DataActionGetPPRs"
)
CMVM_PAGE = "https://investidor.cmvm.pt/pinvestidor/PPRList"

# Estes valores foram capturados via DevTools. moduleVersion / apiVersion
# / OutSystems-Request-Token podem mudar quando a CMVM faz redeploy.
# Se começar a falhar, voltar a copiar o cURL do request DataActionGetPPRs.
# Última recaptura: 15-Jul-2026 (redeploy quebrou o run de 13/Jul).
MODULE_VERSION = "8ujtX5WEwGO88FPP9JTdjQ"
API_VERSION = "6aGkSbrBCH7kns4ai4YbaA"
OS_REQUEST_TOKEN = "6182376737813365"
CSRF_TOKEN = "T6C+9iB49TLra4jEsMeSckDMNhQ="

# Discriminador introduzido no redeploy de Jul/2026. A API devolve 200 com
# lista vazia para o valor errado, sem qualquer erro:
#   1 = fundos poupança-reforma  <- o nosso universo
#   2 = fundos de investimento (não-PPR)
#   3 = fundos imobiliários
#   0 = nenhum (é o que a página envia no load inicial, devolve vazio)
FUND_COMPARATOR_TYPE_ID = 1


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
                    "FundComparatorTypeId": FUND_COMPARATOR_TYPE_ID,
                    "CreatedOn": "1900-01-01T00:00:00", "ModifiedOn": "1900-01-01T00:00:00",
                    "IsSynced": False,
                },
                # Introduzidos no redeploy de Jul/2026: sem FetchDecryptInputs
                # a API responde 200 com data:{} em vez de erro.
                "Request": "",
                "_requestInDataFetchStatus": 1,
                "FetchDecryptInputs": {
                    "FundComparatorTypeId": FUND_COMPARATOR_TYPE_ID,
                    "DataFetchStatus": 1,
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
        if sc in (401, 403, 419):
            raise CMVMTokensExpired(
                f"HTTP {sc} — CSRF/Request token provavelmente expiraram.\n"
                "       1) Abre https://investidor.cmvm.pt/pinvestidor/PPRList\n"
                "       2) DevTools > Network > XHR > DataActionGetPPRs\n"
                "       3) Copia os novos valores para MODULE_VERSION,\n"
                "          API_VERSION, OS_REQUEST_TOKEN, CSRF_TOKEN em\n"
                "          scrapers/cmvm.py"
            ) from e
        raise CMVMFetchFailed(f"HTTP {sc}: {e}") from e
    except Exception as e:
        raise CMVMFetchFailed(str(e)) from e

    # A CMVM responde 200 com data:{} quando faz redeploy do OutSystems — os
    # tokens capturados deixam de servir sem que haja HTTPError para apanhar.
    version = data.get("versionInfo") or {}
    if version.get("hasModuleVersionChanged") or version.get("hasApiVersionChanged"):
        raise CMVMTokensExpired(
            "CMVM fez redeploy: MODULE_VERSION/API_VERSION estão desactualizados.\n"
            "       1) Abre https://investidor.cmvm.pt/pinvestidor/PPRList\n"
            "       2) DevTools > Network > XHR > DataActionGetPPRs\n"
            "       3) Copia os novos valores para MODULE_VERSION,\n"
            "          API_VERSION, OS_REQUEST_TOKEN, CSRF_TOKEN em\n"
            "          scrapers/cmvm.py"
        )

    items = data.get("data", {}).get("PPRList", {}).get("List", [])
    print(f"[cmvm] total PPR devolvidos: {len(items)}")

    fundos = filter_fundos_investimento(items)
    print(f"[cmvm] fundos de investimento (filtrado): {len(fundos)}")

    # Nunca escrever lista vazia: data/raw/ é gitignored, logo o ficheiro em
    # cache é a única cópia que o runner tem. Sobrepô-lo com [] esvazia o
    # universo e o pipeline publica um latest.json sem fundos.
    if not fundos:
        raise CMVMEmptyUniverse(
            f"CMVM devolveu {len(items)} PPR e 0 fundos após filtro; "
            "cmvm_ppr_list.json não foi tocado."
        )

    (DATA_DIR / "cmvm_ppr_list.json").write_text(
        json.dumps(fundos, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return fundos


if __name__ == "__main__":
    try:
        run()
    except CMVMError as e:
        print(f"[cmvm] ERROR: {e}")
        sys.exit(1)
