"""
Scraper para fundos Golden SGF (e outros geridos pela SGF).

A SGF publica um Excel com histórico de cotações em:
  https://goldensgf.pt/dos-fundos/
  Link "Histórico de Cotações" (XLSX).

Parsing:
1. Descarregar XLSX
2. Cada fundo tem a sua folha ou colunas
3. Converter para DataFrame {Date: Close}
"""
import time
import pandas as pd
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_XLSX = DATA_DIR / "golden_sgf_historico.xlsx"

# TODO: confirmar URL exato do XLSX. Ir a https://goldensgf.pt/dos-fundos/
# e copiar o link direto do botão "Histórico de Cotações".
XLSX_URL = "https://goldensgf.pt/wp-content/uploads/HISTORICO-COTACOES.xlsx"


def download_xlsx() -> Path:
    """Descarrega o Excel mais recente da SGF."""
    print(f"[sgf] downloading {XLSX_URL}...")
    r = requests.get(XLSX_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    CACHE_XLSX.write_bytes(r.content)
    return CACHE_XLSX


def parse_excel(path: Path) -> dict[str, pd.DataFrame]:
    """
    Parse do Excel SGF.

    ESTRUTURA A CONFIRMAR após download. Tipicamente:
    - Folha única com coluna "Data" e uma coluna por fundo
    OU
    - Uma folha por fundo com colunas "Data" e "Cotação"

    Retorna dict: {fund_id: DataFrame com Date index e Close column}
    """
    xl = pd.ExcelFile(path)
    print(f"[sgf] folhas encontradas: {xl.sheet_names}")

    results = {}
    # Exemplo - ajustar após ver o Excel real:
    for sheet in xl.sheet_names:
        try:
            df = pd.read_excel(path, sheet_name=sheet)
            # Heuristica: primeira coluna é data, segunda é cotação
            date_col = df.columns[0]
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col]).set_index(date_col)

            # Normalizar nome de folha → fund_id
            fund_id = _sheet_to_fund_id(sheet)
            if fund_id and len(df.columns) >= 1:
                value_col = df.columns[0]
                results[fund_id] = pd.DataFrame({"Close": df[value_col]})
                print(f"[sgf]   {sheet} → {fund_id}: {len(df)} obs")
        except Exception as e:
            print(f"[sgf]   erro na folha {sheet}: {e}")

    return results


def _sheet_to_fund_id(sheet_name: str) -> str | None:
    """
    Mapeia nome de folha do Excel SGF para o fund_id do universo.
    AJUSTAR após ver os nomes reais.
    """
    mapping = {
        # "PPR SGF Stoik": "sgf-stoik",
        # "PPR Doutor Finanças": "sgf-dr-financas",
        # "Golden PPR Retorno Acionista": "golden-sgf-ret-acc",
    }
    for k, v in mapping.items():
        if k.lower() in sheet_name.lower():
            return v
    return None


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
        xlsx_path = CACHE_XLSX

    all_data = parse_excel(xlsx_path)

    # Filtra apenas os fundos do universo
    wanted_ids = {f["id"] for f in sgf_funds}
    results = {fid: df for fid, df in all_data.items() if fid in wanted_ids}

    # Guardar CSVs individuais
    for fid, df in results.items():
        df.to_csv(DATA_DIR / f"{fid}.csv")

    return results


if __name__ == "__main__":
    from universe import get_funds
    run(get_funds())
