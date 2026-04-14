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
    # --- Plataforma IMGA (hospeda ABANCA + IMGA) ---
    # ISINs ABANCA obtidos via search FT (IMGA não os expõe no HTML).
    # O FT fallback no main.py usa estes para puxar a série histórica.
    {"match": "ciclo de vida +55",     "site_url": "https://www.imga.pt/fim/ppr/abanca-pproicvm-ciclo-de-vida-plus55/", "isin": "PTAFIYHM0012"},
    {"match": "ciclo de vida -34",     "site_url": "https://www.imga.pt/fim/ppr/abanca-pproicvm-ciclo-de-vida-34/",     "isin": "PTAFIUHM0016"},
    {"match": "ciclo de vida 35-44",   "site_url": "https://www.imga.pt/fim/ppr/abanca-pproicvm-ciclo-de-vida-35-44/",  "isin": "PTAFIVHM0015"},
    {"match": "ciclo de vida 45-54",   "site_url": "https://www.imga.pt/fim/ppr/abanca-pproicvm-ciclo-de-vida-45-54/",  "isin": "PTAFIWHM0014"},
    {"match": "imga crescimento ppr",  "site_url": "https://www.imga.pt/fim/ppr/imga-crescimento-pproicvm/"},
    {"match": "imga investimento ppr", "site_url": "https://www.imga.pt/fim/ppr/imga-investimento-pproicvm/"},
    {"match": "imga poupança ppr",     "site_url": "https://www.imga.pt/fim/ppr/imga-poupança-pproicvm/"},
    # --- BIZ Capital ---
    {"match": "biz europa valoriza",   "site_url": "https://bizcapital.eu/biz-europa-ppr/",
     "isin": "PTBZSKHM0003", "min_subs": 100},
    # --- Bankinter (precisa curl_cffi) ---
    # Mega TT: histórico via FT (ISIN → FT symbol → chartapi).
    {"match": "bankinter mega tt",     "site_url": "https://www.bankinter.pt/fundos/fundo-mega-tt",
     "source": "ft"},
    {"match": "bankinter 25 ppr",      "site_url": "https://www.bankinter.pt/fundos/bankinter-ppr-25"},
    {"match": "bankinter 50 ppr",      "site_url": "https://www.bankinter.pt/fundos/bankinter-ppr-50"},
    {"match": "bankinter 75 ppr",      "site_url": "https://www.bankinter.pt/fundos/bankinter-ppr-75"},
    {"match": "bankinter 100 ppr",     "site_url": "https://www.bankinter.pt/fundos/investir-em-fundos"},
    # Bankinter Obrigações — várias famílias partilham ISIN por família
    {"match": "obrigações eur 2027",   "isin": "PTBKCCHM0008"},
    {"match": "obrigações eur 2030",   "isin": "PTBKCKHM0008"},
    {"match": "obrigações eur 2034",   "isin": None},  # TODO: ISIN não fornecido
    {"match": "bankinter obrigações ppr / oicvm - categoria", "isin": "PTYBCDLM0005"},
    {"match": "bankinter rendimento ppr / oicvm - categoria", "isin": "PTYBCJHM0013"},
    # --- BlueCrow ---
    {"match": "bluecrow global opportunities", "site_url": "https://www.bluecrowcapital.com/pt/fundos-em-subscricao/global-opportunities-ppr/211/"},
    # --- GNB (ordem: genérico primeiro, específico depois sobrescreve) ---
    {"match": "gnb ppr/oicvm",                 "site_url": "https://www.gnbga.pt/SF_FichaFundo_FO/codfun/14165990076"},
    {"match": "gnb ppr/oicvm global equities", "site_url": "https://www.gnbga.pt/SF_FichaFundo_FO/codfun/14165992247"},
    # --- Optimize ---
    {"match": "optimize ppr/oicvm agressivo",  "site_url": "https://optimize.pt/ppr/agressivo/"},
    {"match": "optimize ppr/oicvm ativo",      "site_url": "https://optimize.pt/ppr/ativo/"},
    {"match": "optimize ppr/oicvm equilibrado","site_url": "https://optimize.pt/ppr/equilibrado/"},
    {"match": "optimize ppr/oicvm moderado",   "site_url": "https://optimize.pt/ppr/moderado/"},
    # Optimize LFO Leopardo: dados vindos do IFI PDF (hardcoded).
    # Premium=P, Discount=D, Standard=S
    {"match": "optimize lfo ppr/oicvm leopardo - categoria p",
     "isin": "PTOPZQHM0005", "min_subs": 500000, "tec": 1.11},
    {"match": "optimize lfo ppr/oicvm leopardo - categoria d",
     "isin": "PTOPZUHM0009", "min_subs": 10000, "tec": 2.19},
    {"match": "optimize lfo ppr/oicvm leopardo - categoria s",
     "isin": "PTOPZVHM0008", "min_subs": 1000, "tec": 2.47},
    # --- Sixty Degrees ---
    {"match": "sixty degrees ppr/oicvm flexível",     "site_url": "https://sixty-degrees.com/fund/sixty-degrees-ppr-oicvm-flexivel/"},
    {"match": "sixty degrees ações globais ppr",      "site_url": "https://sixty-degrees.com/fund/sixty-degrees-acoes-globais-ppr-oicvm/"},
    {"match": "sixty degrees medina ppr",             "site_url": "https://sixty-degrees.com/fund/sixty-degrees-medina-ppr-oiavm-flexivel/"},
    # --- BPI (só URL para Global Equities confirmada; outras páginas não expõem ISIN em HTML) ---
    {"match": "bpi reforma global equities",   "site_url": "https://www.bancobpi.pt/particulares/poupar-investir/ppr/bpi-reforma-global-equities-ppr/oicvm"},
    # --- Caixa / CGD ---
    # ISIN correcto do Caixa ALG é PTCXGUHM0006 (o extractor CGD apanha
    # PTIXAEHM0006 que é outro fundo referenciado na página).
    {"match": "caixa ações líderes globais",   "site_url": "https://www.cgd.pt/Particulares/Poupanca-Investimento/Fundos-de-Investimento/Pages/CaixaALG_PPR_OICVM.aspx",
     "isin": "PTCXGUHM0006", "min_subs": 100},
    # Caixa Wealth IFI PDFs (um ISIN por PDF; aplica-se a todas as categorias
    # do mesmo sub-fundo - A/B/C/D - com o mesmo ISIN como aproximação, até
    # existir ISIN diferenciado por categoria).
    {"match": "caixa wealth ações",            "site_url": "https://www.cgd.pt/Particulares/Poupanca-Investimento/Fundos-de-Investimento/Documents/IFI/FII0003641551.PDF"},
    {"match": "caixa wealth arrojado",         "site_url": "https://www.cgd.pt/Particulares/Poupanca-Investimento/Fundos-de-Investimento/Documents/IFI/FII0003641552.pdf"},
    {"match": "caixa wealth defensivo",        "site_url": "https://www.cgd.pt/Particulares/Poupanca-Investimento/Fundos-de-Investimento/Documents/IFI/FII0003642188.pdf"},
    {"match": "caixa wealth moderado",         "site_url": "https://www.cgd.pt/Particulares/Poupanca-Investimento/Fundos-de-Investimento/Documents/IFI/FII0003641550.pdf"},
    # --- Santander ---
    {"match": "santander aforro",              "site_url": "https://www.santander.pt/poupanca-reforma/fundo-aforro-fpr"},
    {"match": "santander poupança prudente",   "site_url": "https://www.santander.pt/poupanca-reforma/poupanca-prudente-fpr"},
    {"match": "santander poupança valorização","site_url": "https://www.santander.pt/poupanca-reforma/poupanca-valorizacao-fpr"},
    # --- Smart Invest (Banco Invest, 1 URL cobre os 3) ---
    {"match": "smart invest ppr",              "site_url": "https://www.bancoinvest.pt/poupanca-e-investimento/pprs/smart-invest"},
    # --- Oxy Capital (1 URL cobre todas as ~52 categorias) ---
    {"match": "oxy capital liquid opportunities","site_url": "https://oxycapital.com/public-markets/"},
    # Oxy per-categoria: ISIN + min_subs + TEC do IFI PDF. Overrides
    # específicos a seguir sobrescrevem o genérico acima.
    # TEC usa o escalão >€15M AuM (mais baixo; se o fundo ainda estiver
    # abaixo, o real é marginalmente superior).
    # Min subs por grupo:
    #   A/C/E: sem mínimo      B/D: €100.000 (apenas empresas p/ colabs)
    #   F: €2.000
]

# Per-categoria ISINs do IFI Oxy (PDF fornecido pelo utilizador).
# Formato: match_substring → (isin, min_subs, tec)
_OXY_MAP = {
    "categoria aa": ("PTOXCRHM0001", None,   0.16),
    "categoria ba": ("PTOXCSHM0000", 100000, 0.76),
    "categoria bb": ("PTOYAAHM0001", 100000, 0.76),
    "categoria bc": ("PTOYABHM0000", 100000, 0.76),
    "categoria bd": ("PTOYACHM0009", 100000, 0.76),
    "categoria be": ("PTOYADHM0008", 100000, 0.76),
    "categoria bf": ("PTOYAEHM0007", 100000, 0.76),
    "categoria bg": ("PTOYAFHM0006", 100000, 0.76),
    "categoria ca": ("PTOXCTHM0009", None,   0.16),
    "categoria da": ("PTOXCUHM0006", 100000, 0.76),
    "categoria db": ("PTOYAIHM0003", 100000, 0.76),
    "categoria dc": ("PTOYAJHM0002", 100000, 0.76),
    "categoria dd": ("PTOYAKHM0009", 100000, 0.76),
    "categoria de": ("PTOYALHM0008", 100000, 0.76),
    "categoria df": ("PTOYAMHM0007", 100000, 0.76),
    "categoria dg": ("PTOYANHM0006", 100000, 0.76),
    "categoria dh": ("PTOYAOHM0005", 100000, 0.76),
    "categoria ea": ("PTOXTAHM0001", None,   0.56),
    "categoria eb": ("PTOYAQHM0003", None,   0.56),
    "categoria ec": ("PTOYARHM0002", None,   0.56),
    "categoria ed": ("PTOYASHM0001", None,   0.56),
    "categoria ee": ("PTOYATHM0000", None,   0.56),
    "categoria ef": ("PTOYAUHM0007", None,   0.56),
    "categoria eg": ("PTOYAVHM0006", None,   0.56),
    "categoria eh": ("PTOYAWHM0005", None,   0.56),
    "categoria ei": ("PTOYAXHM0004", None,   0.56),
    "categoria ej": ("PTOXS3HM0000", None,   0.56),
    "categoria ek": ("PTOXS4HM0009", None,   0.56),
    "categoria el": ("PTOXS5HM0008", None,   0.56),
    "categoria fa": ("PTOXTBHM0000", 2000,   1.06),
    "categoria fb": ("PTOYAYHM0003", 2000,   1.06),
    "categoria fc": ("PTOYAZHM0002", 2000,   1.06),
    "categoria fd": ("PTOYA1HM0008", 2000,   1.06),
    "categoria fe": ("PTOYA2HM0007", 2000,   1.06),
    "categoria ff": ("PTOYA3HM0006", 2000,   1.06),
    "categoria fg": ("PTOYA4HM0005", 2000,   1.06),
    "categoria fh": ("PTOYA5HM0004", 2000,   1.06),
    "categoria fi": ("PTOYA6HM0003", 2000,   1.06),
    "categoria fj": ("PTOXSMHM0008", 2000,   1.06),
    "categoria fk": ("PTOXSNHM0007", 2000,   1.06),
    "categoria fl": ("PTOXSOHM0006", 2000,   1.06),
    "categoria fm": ("PTOXSPHM0005", 2000,   1.06),
    "categoria fn": ("PTOXS6HM0007", 2000,   1.06),
    "categoria fo": ("PTOXS7HM0006", 2000,   1.06),
    "categoria fp": ("PTOXS8HM0005", 2000,   1.06),
    "categoria fq": ("PTOXS9HM0004", 2000,   1.06),
    "categoria fr": ("PTOXZUHM0009", 2000,   1.06),
    "categoria fs": ("PTOXZVHM0008", 2000,   1.06),
}
for _cat, (_isin, _min, _tec) in _OXY_MAP.items():
    ov = {"match": f"oxy capital liquid opportunities a, ppr - {_cat}",
          "isin": _isin, "tec": _tec}
    if _min is not None:
        ov["min_subs"] = _min
    MANUAL_OVERRIDES.append(ov)

# Save & Grow PPR (Casa de Investimentos) - 2 classes únicas (id explícito).
MANUAL_OVERRIDES.extend([
    {
        "match": "save & grow ppr/oicvm - categoria 01",
        "id": "casa-inv-sg-founders",
        "name": "Casa de Investimentos Save & Grow PPR - Founders",
        "manager": "Casa de Investimentos",
        "isin": "PTCUUBHM0004",
        "tec": 1.45,
        # Founders: €250.000 para novas subscrições (primeiros 2630 investidores
        # já encerrados em 2021). Valores do IFI Save & Grow (11-02-2026).
        "min_subs": 250000,
        "investing_url": "https://www.investing.com/funds/ptcuubhm0004",
        "investing_pair_id": 1169681,
        "source": "investing",
    },
    {
        "match": "save & grow ppr/oicvm - categoria 02",
        "id": "casa-inv-sg-prime",
        "name": "Casa de Investimentos Save & Grow PPR - Prime",
        "manager": "Casa de Investimentos",
        "isin": "PTCUUAHM0005",
        "tec": 1.66,
        "min_subs": 1000,   # IFI: 1.000 EUR inicial; 100 EUR subsequentes
        "investing_url": "https://www.investing.com/funds/ptcuuahm0005",
        "investing_pair_id": 1169680,
        "source": "investing",
    },
])

# Fundos não listados na CMVM (vêm só do Excel da Golden SGF). O scraper
# SGF mapeia o nome no Excel → este id via NAME_TO_FUND_ID em
# scrapers/golden_sgf.py - manter os ids alinhados.
# ISINs confirmados nos PDFs Doc-Informativo da Golden SGF + cruzamento
# por data de autorização/início com histórico no Excel da SGF.
# min_subs das classes Plus/Start do ETF PDF; demais fundos TBC.
EXTRA_FUNDS = [
    {"id": "sgf-dr-financas",                "name": "SGF DR FINANÇAS",                 "manager": "SGF"},
    {"id": "golden-sgf-top-gestores",        "name": "Golden SGF TOP GESTORES",         "manager": "Golden SGF"},
    {"id": "golden-sgf-reforma-conservadora","name": "Golden SGF Reforma Conservadora", "manager": "Golden SGF", "isin": "PTFP00000515"},
    {"id": "golden-sgf-reforma-equilibrada", "name": "Golden SGF Reforma Equilibrada",  "manager": "Golden SGF", "isin": "PTFP00000507"},
    {"id": "golden-sgf-reforma-dinamica",    "name": "Golden SGF Reforma Dinâmica",     "manager": "Golden SGF", "isin": "PTFP00000879"},
    {"id": "golden-sgf-reforma-garantida",   "name": "Golden SGF Reforma Garantida",    "manager": "Golden SGF", "isin": "PTFP00000473"},
    {"id": "golden-sgf-poupanca-ativa",      "name": "Golden SGF Poupança Ativa",       "manager": "Golden SGF", "isin": "PTFP00000416"},
    {"id": "golden-sgf-poupanca-conservadora","name": "Golden SGF Poupança Conservadora","manager": "Golden SGF", "isin": "PTFP00000424"},
    {"id": "golden-sgf-poupanca-equilibrada","name": "Golden SGF Poupança Equilibrada", "manager": "Golden SGF", "isin": "PTFP00000432"},
    {"id": "golden-sgf-poupanca-dinamica",   "name": "Golden SGF Poupança Dinâmica",    "manager": "Golden SGF", "isin": "PTFP00000382"},
    {"id": "golden-sgf-poupanca-garantida",  "name": "Golden SGF Poupança Garantida",   "manager": "Golden SGF"},
    {"id": "golden-sgf-etf-plus",            "name": "Golden SGF ETF Plus",             "manager": "Golden SGF", "isin": "PTFP00000762", "min_subs": 10000, "tec": 0.75},
    {"id": "golden-sgf-etf-start",           "name": "Golden SGF ETF Start",            "manager": "Golden SGF", "isin": "PTFP00000861", "min_subs": 1500,  "tec": 1.00},
    {"id": "sgf-stoik",                      "name": "PPR SGF Stoik",                   "manager": "SGF",        "isin": "PTFP00000390"},
    {"id": "sgf-reforma-stoik",              "name": "SGF Reforma Stoik",               "manager": "SGF"},
    {"id": "sgf-square-acoes",               "name": "SGF Square Ações",                "manager": "SGF"},
    {"id": "sgf-deco-proteste",              "name": "SGF PPR DECO PROTESTE",           "manager": "SGF",        "isin": "PTFP00000770"},
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
        "fund_type": "FI-PPR",  # Fundo de Investimento PPR, regulado pela CMVM
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
    """Aplica overrides. Se `id` está definido, assume override único (1 fundo).
    Senão aplica a TODOS os fundos cujo nome contém `match` (ex: site_url
    comum a várias categorias do mesmo fundo)."""
    for ov in MANUAL_OVERRIDES:
        match = ov["match"].lower()
        unique = bool(ov.get("id"))
        applied = 0
        for f in funds:
            if match not in f["name"].lower():
                continue
            for k, v in ov.items():
                if k == "match":
                    continue
                f[k] = v
            applied += 1
            if unique:
                break
        if applied == 0:
            print(f"[universe] aviso: override sem match: {ov['match']!r}")
    return funds


_cache: list[dict] | None = None


def get_funds() -> list[dict]:
    global _cache
    if _cache is not None:
        return _cache

    if not CMVM_JSON.exists():
        print(f"[universe] {CMVM_JSON} não existe - corre `python -m scrapers.cmvm` primeiro")
        _cache = []
        return _cache

    raw = json.loads(CMVM_JSON.read_text(encoding="utf-8"))
    funds = [_from_cmvm_entry(it) for it in raw]

    for ex in EXTRA_FUNDS:
        funds.append({
            "id": ex["id"],
            "name": ex["name"],
            "manager": ex["manager"],
            "isin": ex.get("isin"),
            "yahoo_ticker": None,
            "investing_url": None,
            "source": "golden_sgf",
            "tec": ex.get("tec"),
            "min_subs": ex.get("min_subs"),
            "risk_class": None,
            "cmvm_id": None,
            "cmvm_des_tip": None,
            # SGF são Fundos de Pensões PPR (regulados pela ASF), não
            # Fundos de Investimento PPR. Incluídos pela procura elevada.
            "fund_type": "FP-PPR",
            "cmvm_metrics": None,
        })

    funds = _apply_overrides(funds)
    _apply_xlsx_overrides(funds)
    _cache = funds
    return funds


def _apply_xlsx_overrides(funds: list[dict]) -> None:
    """Lê data/overrides.xlsx (se existir) e aplica override_* aos fundos."""
    xlsx = Path(__file__).parent / "data" / "overrides.xlsx"
    if not xlsx.exists():
        return
    try:
        import pandas as pd
    except ImportError:
        print("[universe] pandas não disponível - overrides.xlsx ignorado")
        return
    try:
        df = pd.read_excel(xlsx, sheet_name="Overrides")
    except Exception as e:
        print(f"[universe] overrides.xlsx não pôde ser lido: {e}")
        return

    by_id = {f["id"]: f for f in funds}
    applied = 0
    for _, row in df.iterrows():
        fid = row.get("id")
        f = by_id.get(fid)
        if not f:
            continue
        mapping = {
            "override_isin": "isin",
            "override_min_subs": "min_subs",
            "override_tec": "tec",
            "override_manager": "manager",
            "prospectus_url": "prospectus_url",
            "notes": "notes",
        }
        for src, dst in mapping.items():
            v = row.get(src)
            if pd.notna(v) and v not in ("", None):
                f[dst] = float(v) if dst in ("tec", "min_subs") else v
                applied += 1
    if applied:
        print(f"[universe] overrides.xlsx: {applied} campos aplicados")


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
