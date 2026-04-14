"""
Scraper para fundos Golden SGF (e outros geridos pela SGF).

Excel publicado em https://goldensgf.pt/dos-fundos/ → link "Histórico de
Cotações". URL real (extraída do HTML):
  https://goldensgf.pt/wp-content/uploads/2024/08/HISTORICO-DE-COTACOES.xlsx

Estrutura observada (Sheet1, formato long, ~83k linhas):
  Nome do Fundo | Cotação | Data
"""
import pandas as pd
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_XLSX = DATA_DIR / "golden_sgf_historico.xlsx"

XLSX_URL = "https://goldensgf.pt/wp-content/uploads/2024/08/HISTORICO-DE-COTACOES.xlsx"
SGF_PAGE = "https://goldensgf.pt/dos-fundos/"


def _resolve_xlsx_url() -> str:
    """Faz scrape da página dos fundos para encontrar o link XLSX atual.
    Cai para XLSX_URL se falhar."""
    try:
        from bs4 import BeautifulSoup
        r = requests.get(SGF_PAGE, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".xlsx") and "historico" in href.lower():
                return href
    except Exception as e:
        print(f"[sgf] aviso: não consegui resolver URL via página ({e})")
    return XLSX_URL


def download_xlsx() -> Path:
    url = _resolve_xlsx_url()
    print(f"[sgf] downloading {url}...")
    r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    CACHE_XLSX.write_bytes(r.content)
    return CACHE_XLSX


# Mapeia nome exato (case-insensitive, trim) do Excel → fund_id do universo.
# Adicionar entradas conforme universe.py for crescendo.
NAME_TO_FUND_ID = {
    "sgf dr finanças": "sgf-dr-financas",
    "golden sgf top gestores": "golden-sgf-top-gestores",
    "golden sgf reforma equilibrada": "golden-sgf-reforma-equilibrada",
    "golden sgf reforma conservadora": "golden-sgf-reforma-conservadora",
    "golden sgf reforma dinamica": "golden-sgf-reforma-dinamica",
    "golden sgf reforma garantida": "golden-sgf-reforma-garantida",
    "golden sgf poupança ativa": "golden-sgf-poupanca-ativa",
    "golden sgf poupança conservadora": "golden-sgf-poupanca-conservadora",
    "golden sgf poupança dinamica": "golden-sgf-poupanca-dinamica",
    "golden sgf poupança equilibrada": "golden-sgf-poupanca-equilibrada",
    "golden sgf poupança garantida": "golden-sgf-poupanca-garantida",
    "golden sgf etf plus": "golden-sgf-etf-plus",
    "golden sgf etf start": "golden-sgf-etf-start",
    "ppr sgf stoik": "sgf-stoik",
    "sgf reforma stoik": "sgf-reforma-stoik",
    "sgf square ações": "sgf-square-acoes",
    "sgf ppr deco proteste": "sgf-deco-proteste",
}


def _name_to_fund_id(name: str) -> str | None:
    if not isinstance(name, str):
        return None
    return NAME_TO_FUND_ID.get(name.strip().lower())


def parse_excel(path: Path) -> dict[str, pd.DataFrame]:
    """Lê o Excel SGF em formato long e devolve {fund_id: DataFrame[Close]}."""
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]

    name_col = next((c for c in df.columns if "fundo" in c.lower()), df.columns[0])
    price_col = next((c for c in df.columns if "cota" in c.lower()), df.columns[1])
    date_col = next((c for c in df.columns if "data" in c.lower()), df.columns[2])

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, name_col, price_col])

    results: dict[str, pd.DataFrame] = {}
    for name, group in df.groupby(name_col):
        fund_id = _name_to_fund_id(name)
        if not fund_id:
            continue
        s = (
            group.set_index(date_col)[price_col]
            .sort_index()
            .groupby(level=0).last()
        )
        results[fund_id] = pd.DataFrame({"Close": s})
        print(f"[sgf]   {name!r} -> {fund_id}: {len(s)} obs")
    return results


def run(funds: list[dict]) -> dict[str, pd.DataFrame]:
    sgf_funds = [f for f in funds if f.get("source") == "golden_sgf"]
    if not sgf_funds:
        return {}

    try:
        xlsx_path = download_xlsx()
    except Exception as e:
        print(f"[sgf] ERROR ao descarregar Excel: {e}")
        if not CACHE_XLSX.exists():
            return {}
        print(f"[sgf] usando cache: {CACHE_XLSX}")
        xlsx_path = CACHE_XLSX

    all_data = parse_excel(xlsx_path)

    wanted_ids = {f["id"] for f in sgf_funds}
    results = {fid: df for fid, df in all_data.items() if fid in wanted_ids}

    for fid, df in results.items():
        df.to_csv(DATA_DIR / f"{fid}.csv")

    missing = wanted_ids - set(results.keys())
    if missing:
        print(f"[sgf] WARN sem match no Excel: {sorted(missing)}")

    return results


if __name__ == "__main__":
    from universe import get_funds
    run(get_funds())
