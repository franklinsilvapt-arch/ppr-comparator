"""
Universo de fundos PPR.

Lista gerada automaticamente a partir de data/raw/cmvm_ppr_list.json
(scraper: scrapers/cmvm.py). MANUAL_OVERRIDES adiciona/edita entradas
para fornecer ticker Yahoo, URL Investing, ISIN, etc.

Para cada fundo:
  id, name, manager, source, isin?, yahoo_ticker?, investing_url?,
  tec, risk_class, cmvm_metrics? (REND_* já calculados pela CMVM)

Sources:
- "yahoo"      ticker 0P...F
- "investing"  URL Investing.com (fallback)
- "golden_sgf" Excel SGF
- "cmvm"       sem histórico próprio; usa só métricas REND_* da CMVM
"""
import json
import re
import unicodedata
from pathlib import Path

CMVM_JSON = Path(__file__).parent / "data" / "raw" / "cmvm_ppr_list.json"

# Match nome CMVM (substring, case-insensitive) → overrides.
# A entrada é fundida com a derivada da CMVM (overrides ganham).
MANUAL_OVERRIDES = [
    {
        "match": "alves ribeiro ppr",
        "id": "invest-ar",
        "yahoo_ticker": "0P000011IR.F",
        "isin": "PTYINVIM0007",
        "source": "yahoo",
    },
    # Save & Grow PPR (Casa de Investimentos) tem 2 classes:
    #   Categoria 01 = Founders (ISIN PTCUUBHM0004, pair 1169681)
    #   Categoria 02 = Prime    (ISIN PTCUUAHM0005, pair 1169680)
    {
        "match": "save & grow ppr/oicvm - categoria 01",
        "id": "casa-inv-sg-founders",
        "name": "Casa de Investimentos Save & Grow PPR — Founders",
        "manager": "Casa de Investimentos",
        "isin": "PTCUUBHM0004",
        "investing_url": "https://www.investing.com/funds/ptcuubhm0004",
        "investing_pair_id": 1169681,
        "source": "investing",
    },
    {
        "match": "save & grow ppr/oicvm - categoria 02",
        "id": "casa-inv-sg-prime",
        "name": "Casa de Investimentos Save & Grow PPR — Prime",
        "manager": "Casa de Investimentos",
        "isin": "PTCUUAHM0005",
        "investing_url": "https://www.investing.com/funds/ptcuuahm0005",
        "investing_pair_id": 1169680,
        "source": "investing",
    },
]

# Fundos não listados na CMVM (vêm só do Excel da Golden SGF). O scraper
# SGF mapeia o nome no Excel → este id via NAME_TO_FUND_ID em
# scrapers/golden_sgf.py — manter os ids alinhados.
EXTRA_FUNDS = [
    {"id": "sgf-dr-financas",                "name": "SGF DR FINANÇAS",                 "manager": "SGF"},
    {"id": "golden-sgf-top-gestores",        "name": "Golden SGF TOP GESTORES",         "manager": "Golden SGF"},
    {"id": "golden-sgf-reforma-conservadora","name": "Golden SGF Reforma Conservadora", "manager": "Golden SGF"},
    {"id": "golden-sgf-reforma-equilibrada", "name": "Golden SGF Reforma Equilibrada",  "manager": "Golden SGF"},
    {"id": "golden-sgf-reforma-dinamica",    "name": "Golden SGF Reforma Dinâmica",     "manager": "Golden SGF"},
    {"id": "golden-sgf-reforma-garantida",   "name": "Golden SGF Reforma Garantida",    "manager": "Golden SGF"},
    {"id": "golden-sgf-poupanca-ativa",      "name": "Golden SGF Poupança Ativa",       "manager": "Golden SGF"},
    {"id": "golden-sgf-poupanca-conservadora","name": "Golden SGF Poupança Conservadora","manager": "Golden SGF"},
    {"id": "golden-sgf-poupanca-equilibrada","name": "Golden SGF Poupança Equilibrada", "manager": "Golden SGF"},
    {"id": "golden-sgf-poupanca-dinamica",   "name": "Golden SGF Poupança Dinâmica",    "manager": "Golden SGF"},
    {"id": "golden-sgf-poupanca-garantida",  "name": "Golden SGF Poupança Garantida",   "manager": "Golden SGF"},
    {"id": "golden-sgf-etf-plus",            "name": "Golden SGF ETF Plus",             "manager": "Golden SGF"},
    {"id": "golden-sgf-etf-start",           "name": "Golden SGF ETF Start",            "manager": "Golden SGF"},
    {"id": "sgf-stoik",                      "name": "PPR SGF Stoik",                   "manager": "SGF"},
    {"id": "sgf-reforma-stoik",              "name": "SGF Reforma Stoik",               "manager": "SGF"},
    {"id": "sgf-square-acoes",               "name": "SGF Square Ações",                "manager": "SGF"},
    {"id": "sgf-deco-proteste",              "name": "SGF PPR DECO PROTESTE",           "manager": "SGF"},
]


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:60]


# Regex que apanha a descrição técnica usada pela CMVM:
#   "Fundo de Investimento [Mobiliário] [Alternativo] [Aberto]
#    [de Ações|Obrigações|Poupança] [Flexível] [de] Poupança-?Reforma"
# Pode aparecer a meio (precedida de "-" ou ",") ou como prefixo. Remove
# até encontrar "Poupança Reforma"/"Poupança-Reforma", mas pára em "-"
# para não cortar a " - Categoria X" a seguir.
_CMVM_TECH_RE = re.compile(
    r"[\s,-]*Fundo\s+de\s+Investimento[^-]*?Poupan[çc]a[\s-]?Reforma",
    re.IGNORECASE,
)


def _clean_name(name: str) -> str:
    """Remove a descrição técnica CMVM redundante dos nomes dos fundos."""
    n = _CMVM_TECH_RE.sub(" ", name)
    n = re.sub(r"\s+", " ", n).strip(" -,")
    return n or name


def _guess_manager(name: str) -> str:
    # CMVM payload não traz NOM_ENT preenchido. Heurística: 1ª palavra
    # ou marca antes de "PPR".
    n = name.strip()
    m = re.match(r"^([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wáéíóúâêôãõç&\.]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wáéíóúâêôãõç&\.]+){0,2})", n)
    return m.group(1).strip() if m else n.split()[0]


def _f(s: str | None) -> float | None:
    if s in (None, "", "0", "0.0"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _from_cmvm_entry(item: dict) -> dict:
    raw_name = item.get("NOM_FUN", "").strip()
    name = _clean_name(raw_name)
    fund_id = f"{_slug(raw_name)}-{item['Id']}"

    return {
        "id": fund_id,
        "name": name,
        "manager": _guess_manager(name),
        "isin": None,
        "yahoo_ticker": None,
        "investing_url": None,
        "source": "cmvm",
        "tec": _f(item.get("TAXA_TEC")) if item.get("HAS_TAXA_TEC") else None,
        "min_subs": None,
        "risk_class": item.get("PPRRiskClassId") or None,
        "cmvm_id": item.get("Id"),
        "cmvm_des_tip": item.get("DES_TIP"),
        "cmvm_metrics": {
            "ytd": _f(item.get("REND_YTD")) if item.get("HAS_REND_YTD") else None,
            "1y": _f(item.get("REND_1Y")) if item.get("HAS_REND_1Y") else None,
            "2y": _f(item.get("REND_2Y")) if item.get("HAS_REND_2Y") else None,
            "3y": _f(item.get("REND_3Y")) if item.get("HAS_REND_3Y") else None,
            "5y": _f(item.get("REND_5Y")) if item.get("HAS_REND_5Y") else None,
            "10y": _f(item.get("REND_10Y")) if item.get("HAS_REND_10Y") else None,
        },
    }


def _apply_overrides(funds: list[dict]) -> list[dict]:
    for ov in MANUAL_OVERRIDES:
        match = ov["match"].lower()
        for f in funds:
            if match in f["name"].lower():
                for k, v in ov.items():
                    if k == "match":
                        continue
                    f[k] = v
                break
        else:
            print(f"[universe] aviso: override sem match: {ov['match']!r}")
    return funds


_cache: list[dict] | None = None


def get_funds() -> list[dict]:
    global _cache
    if _cache is not None:
        return _cache

    if not CMVM_JSON.exists():
        print(f"[universe] {CMVM_JSON} não existe — corre `python -m scrapers.cmvm` primeiro")
        _cache = []
        return _cache

    raw = json.loads(CMVM_JSON.read_text(encoding="utf-8"))
    funds = [_from_cmvm_entry(it) for it in raw]

    for ex in EXTRA_FUNDS:
        funds.append({
            "id": ex["id"],
            "name": ex["name"],
            "manager": ex["manager"],
            "isin": None,
            "yahoo_ticker": None,
            "investing_url": None,
            "source": "golden_sgf",
            "tec": None,
            "min_subs": None,
            "risk_class": None,
            "cmvm_id": None,
            "cmvm_des_tip": None,
            "cmvm_metrics": None,
        })

    funds = _apply_overrides(funds)
    _cache = funds
    return funds


def get_fund(fund_id: str) -> dict | None:
    for f in get_funds():
        if f["id"] == fund_id:
            return f
    return None


if __name__ == "__main__":
    funds = get_funds()
    print(f"Total: {len(funds)} fundos")
    by_source: dict[str, int] = {}
    for f in funds:
        by_source[f["source"]] = by_source.get(f["source"], 0) + 1
    print("Por source:", by_source)
