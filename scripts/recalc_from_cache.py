"""Recalcula latest.json a partir dos CSVs em data/raw/, sem re-fetch.
Uso quando só mudou calc_metrics.py ou universe.py."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from universe import get_funds
import calc_metrics

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "latest.json"


def load_benchmark() -> pd.Series | None:
    p = RAW / "URTH.csv"
    if not p.exists():
        try:
            from scrapers import yahoo
            df = yahoo.fetch_history("URTH", period="10y")
            if df.empty:
                return None
            df.to_csv(p)
        except Exception as e:
            print(f"[bench] erro: {e}")
            return None
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    col = "Close" if "Close" in df.columns else df.columns[0]
    return df[col].dropna()


def load_prices(fid: str) -> pd.Series | None:
    p = RAW / f"{fid}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    col = "Close" if "Close" in df.columns else df.columns[0]
    return df[col].dropna().sort_index()


def main():
    funds = get_funds()
    bench = load_benchmark()
    out_funds = []
    latest_dates = []

    for f in funds:
        fid = f["id"]
        entry = {
            "id": fid, "name": f["name"], "manager": f["manager"],
            "isin": f.get("isin"), "tec": f.get("tec"),
            "min_subs": f.get("min_subs"),
            "risk_class": f.get("risk_class"),
            "source": f.get("source"),
            "cmvm_des_tip": f.get("cmvm_des_tip"),
            "fund_type": f.get("fund_type"),
            "prospectus_url": f.get("prospectus_url"),
            "notes": f.get("notes"),
            "hidden": bool(f.get("hidden")),
        }
        prices = load_prices(fid)
        if prices is not None and not prices.empty:
            # Clip à data de constituição real se fornecida.
            inc = f.get("inception")
            if inc:
                prices = prices[prices.index >= pd.Timestamp(inc)]
        if prices is not None and not prices.empty:
            latest_dates.append(prices.index[-1])
            entry["returns"] = calc_metrics.calc_returns(prices)
            entry["risk"] = calc_metrics.calc_risk(prices, bench)
            entry["series"] = {
                p: calc_metrics.build_chart_series(prices, p)
                for p in ["ytd", "1y", "3y", "5y", "10y", "since"]
            }
            entry["last_price_date"] = prices.index[-1].strftime("%Y-%m-%d")
            entry["data_origin"] = "historical"
            out_funds.append(entry)
            continue

        m = f.get("cmvm_metrics")
        if m and any(v is not None for v in m.values()):
            entry["returns"] = {
                "ytd": m.get("ytd"), "1y": m.get("1y"),
                "3y": m.get("3y"), "5y": m.get("5y"),
                "10y": m.get("10y"),
                "since": m.get("10y") if m.get("10y") is not None else m.get("5y"),
                "ann": None,
            }
            entry["risk"] = {}
            entry["series"] = {}
            entry["last_price_date"] = None
            entry["data_origin"] = "cmvm"
            out_funds.append(entry)

    # Benchmark (URTH) exportado como série diária ao longo do período
    # relevante. Serve para o embed recalcular beta na janela comum dos
    # fundos seleccionados (o beta no campo fund.risk.beta é sobre toda
    # a história individual, não comparable entre fundos).
    bench_payload = None
    if bench is not None and not bench.empty:
        b = bench.dropna().sort_index()
        # limita ao período relevante (a partir de 2015) para poupar bytes
        b = b[b.index >= pd.Timestamp("2015-01-01")]
        bench_payload = {
            "labels": [d.strftime("%Y-%m-%d") for d in b.index],
            "data": [round(float(v), 4) for v in b.values],
            "ticker": "URTH",
            "name": "MSCI World (iShares URTH, EUR)",
        }

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_as_of": min(latest_dates).strftime("%Y-%m-%d") if latest_dates else None,
        "latest_data_date": max(latest_dates).strftime("%Y-%m-%d") if latest_dates else None,
        "benchmark": bench_payload,
        "funds": out_funds,
    }
    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"OK {OUT} ({len(out_funds)} fundos)")


if __name__ == "__main__":
    main()
