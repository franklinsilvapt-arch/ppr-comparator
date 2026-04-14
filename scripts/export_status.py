"""
Gera data/ppr_status.xlsx com o estado de automação de cada fundo:
  - "Com histórico automatizado" (linha contínua no chart)
  - "Sem histórico (só métricas CMVM)" (linha tracejada estimada)

Corre:
  python -m scripts.export_status
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
LATEST = ROOT / "data" / "latest.json"
OUT = ROOT / "data" / "ppr_status.xlsx"


def main() -> None:
    data = json.loads(LATEST.read_text(encoding="utf-8"))
    funds = data["funds"]

    cols = [
        "id", "name", "manager", "source", "data_origin",
        "fund_type", "last_price_date",
        "tec", "risk_class", "isin", "min_subs",
        "cmvm_des_tip",
    ]
    rows = []
    for f in funds:
        rows.append({c: f.get(c) for c in cols})
    df = pd.DataFrame(rows)

    automated = df[df["data_origin"] == "historical"].copy()
    cmvm_only = df[df["data_origin"] == "cmvm"].copy()

    with pd.ExcelWriter(OUT, engine="openpyxl") as xl:
        automated.sort_values("name").to_excel(
            xl, sheet_name="Com histórico", index=False
        )
        cmvm_only.sort_values("name").to_excel(
            xl, sheet_name="Só métricas CMVM", index=False
        )
        df.sort_values("name").to_excel(
            xl, sheet_name="Todos", index=False
        )

    print(f"OK: {OUT}")
    print(f"  com histórico   : {len(automated)}")
    print(f"  só métricas CMVM: {len(cmvm_only)}")


if __name__ == "__main__":
    main()
