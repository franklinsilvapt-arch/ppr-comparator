"""
Gera data/overrides_template.xlsx: um Excel com uma linha por PPR e
colunas que o utilizador pode preencher manualmente (ISIN, subscrição
mínima, TEC, URL prospecto, etc).

Depois, corre `python -m scripts.import_overrides` com o ficheiro
preenchido em data/overrides.xlsx para aplicar nos dados.

Corre:
  python -m scripts.export_overrides_template
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
LATEST = ROOT / "data" / "latest.json"
OUT = ROOT / "data" / "overrides_template.xlsx"


def main() -> None:
    data = json.loads(LATEST.read_text(encoding="utf-8"))
    funds = data["funds"]

    rows = []
    for f in funds:
        rows.append({
            "id": f["id"],
            "name": f["name"],
            # campos pré-preenchidos (read-only para referência)
            "current_tec": f.get("tec"),
            "current_risk_class": f.get("risk_class"),
            "current_isin": f.get("isin"),
            # colunas a preencher (deixar em branco = não altera)
            "override_isin": "",
            "override_min_subs": "",
            "override_tec": "",
            "override_manager": "",
            "prospectus_url": "",
            "notes": "",
        })

    df = pd.DataFrame(rows).sort_values("name")
    with pd.ExcelWriter(OUT, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="Overrides", index=False)

    print(f"OK: {OUT}")
    print(f"Total linhas: {len(df)}")
    print("Preenche as colunas 'override_*' e guarda como data/overrides.xlsx")


if __name__ == "__main__":
    main()
