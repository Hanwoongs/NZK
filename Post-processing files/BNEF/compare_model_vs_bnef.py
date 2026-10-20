#!/usr/bin/env python3
"""Compare what is actually in the model asset files against BNEF Mid in
MACRO units, so the harmonisation can be audited.

Output: outputs/model_vs_bnef_mid.csv
"""
import csv, glob
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "outputs"
YR = [2021, 2025, 2030, 2035, 2040, 2045, 2050]
SFX = ["21", "25", "30", "35", "40", "45", "50"]

# label -> (metric, model tech, asset glob, id fragment, column)
MAP = [
    ("Capex",        "Capex",        "Solar PV",      "VRE",             "utility_pv",    "edges--edge--investment_cost"),
    ("Capex",        "Capex",        "Onshore wind",  "VRE",             "onshore_wind",  "edges--edge--investment_cost"),
    ("Capex",        "Capex",        "Offshore wind", "VRE",             "offshore_wind", "edges--edge--investment_cost"),
    ("Capex",        "Capex",        "Coal",          "coalpower",       "Coal_power",    "edges--elec_edge--investment_cost"),
    ("Capex",        "Capex",        "Gas CCGT",      "NaturalGasPower", "natgas_CCGT",   "edges--elec_edge--investment_cost"),
    ("Fixed O&M",    "Fixed O&M",    "Solar PV",      "VRE",             "utility_pv",    "edges--edge--fixed_om_cost"),
    ("Fixed O&M",    "Fixed O&M",    "Onshore wind",  "VRE",             "onshore_wind",  "edges--edge--fixed_om_cost"),
    ("Fixed O&M",    "Fixed O&M",    "Coal",          "coalpower",       "Coal_power",    "edges--elec_edge--fixed_om_cost"),
    ("Fixed O&M",    "Fixed O&M",    "Gas CCGT",      "NaturalGasPower", "natgas_CCGT",   "edges--elec_edge--fixed_om_cost"),
    ("Variable O&M", "Variable O&M", "Coal",          "coalpower",       "Coal_power",    "edges--elec_edge--variable_om_cost"),
    ("Variable O&M", "Variable O&M", "Gas CCGT",      "NaturalGasPower", "natgas_CCGT",   "edges--elec_edge--variable_om_cost"),
]

bnef = {}
for r in csv.DictReader(open(OUT / "bnef_korea_three_units_model_years.csv")):
    bnef[(r["metric"], r["technology_model"], r["scenario"], int(r["year"]))] = float(r["macro_value"])

rows = []
for _, metric, tech, pat, idf, col in MAP:
    for y, s in zip(YR, SFX):
        f = glob.glob(str(ROOT / f"Ref/assets/assets_{y}/{pat}_{s}.csv"))
        mv = None
        if f:
            for x in csv.DictReader(open(f[0], encoding="utf-8-sig")):
                if idf in x["id"]:
                    try: mv = float(x[col])
                    except (ValueError, KeyError): pass
                    break
        if mv is None:
            continue
        lo  = bnef.get((metric, tech, "Low", y))
        mid = bnef.get((metric, tech, "Mid", y))
        hi  = bnef.get((metric, tech, "High", y))
        best = None
        cand = [(s_, v) for s_, v in (("Low", lo), ("Mid", mid), ("High", hi)) if v is not None]
        if cand:
            best = min(cand, key=lambda t: abs(t[1] - mv))[0]
        rows.append({
            "metric": metric, "technology": tech, "year": y,
            "model_value": round(mv, 4),
            "bnef_low": round(lo, 4) if lo is not None else "",
            "bnef_mid": round(mid, 4) if mid is not None else "",
            "bnef_high": round(hi, 4) if hi is not None else "",
            "pct_vs_mid": round(100 * (mv - mid) / mid, 2) if mid else "",
            "closest_scenario": best or "",
        })

f = OUT / "model_vs_bnef_mid.csv"
with open(f, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"  + {f.name}  ({len(rows)} rows)")

off = [r for r in rows if r["pct_vs_mid"] != "" and abs(r["pct_vs_mid"]) > 1.5 and r["year"] != 2021]
print(f"  rows more than 1.5% from BNEF Mid, excluding 2021: {len(off)} of {len(rows)}")
for r in off[:14]:
    print(f"    {r['metric']:14s}{r['technology']:14s}{r['year']}  model {r['model_value']:>12,.1f}"
          f"  Mid {r['bnef_mid']:>12,.1f}  {r['pct_vs_mid']:+7.1f}%")
