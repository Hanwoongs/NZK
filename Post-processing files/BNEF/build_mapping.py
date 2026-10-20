#!/usr/bin/env python3
"""Nuclear from the MACRO asset files + the MACRO->GCAM technology mapping.

Nuclear is not in the BNEF Korea workbook. Its values come from the model's
own asset files and are treated as the Mid case here, flagged as a separate
source.

Outputs: outputs/nuclear_from_macro.csv
         outputs/macro_to_gcam_mapping.csv
"""
import csv, glob
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "outputs"
YR = [2021, 2025, 2030, 2035, 2040, 2045, 2050]
SFX = ["21", "25", "30", "35", "40", "45", "50"]
CPI = 5.0400                       # 2021$ = 1975$ x 5.0400

# ---------- 1. nuclear out of the asset files ---------------------------
nuc = {}
for y, s in zip(YR, SFX):
    g = glob.glob(str(ROOT / f"Ref/assets/assets_{y}/nuclear_{s}.csv"))
    if not g:
        continue
    r = list(csv.DictReader(open(g[0], encoding="utf-8-sig")))[0]
    nuc[y] = {
        "Capex":        float(r["edges--elec_edge--investment_cost"]),   # $/MW
        "Fixed O&M":    float(r["edges--elec_edge--fixed_om_cost"]),     # $/MW-yr
        "Variable O&M": float(r["edges--elec_edge--variable_om_cost"]),  # $/MWh
    }

SPEC = {  # metric -> (macro unit, gcam unit, macro->gcam factor before deflating)
    "Capex":        ("$/MW",    "$/kW",    0.001),
    "Fixed O&M":    ("$/MW-yr", "$/kW/yr", 0.001),
    "Variable O&M": ("$/MWh",   "$/GJ",    1/3.6),
}

rows = []
for metric, (m_u, g_u, f) in SPEC.items():
    for y in YR:
        if y not in nuc:
            continue
        mv = nuc[y][metric]
        rows.append({
            "metric": metric, "technology_model": "Nuclear",
            "scenario": "Mid", "year": y,
            "source": "MACRO asset files (not BNEF)",
            "macro_value": round(mv, 4), "macro_unit": f"2021$ {m_u}",
            "gcam_value": round(mv * f / CPI, 6), "gcam_unit": f"1975$ {g_u}",
        })

f1 = OUT / "nuclear_from_macro.csv"
with open(f1, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"  + {f1.name}  ({len(rows)} rows)")

# ---------- 2. MACRO -> GCAM mapping ------------------------------------
# model technology -> (GCAM subsector, GCAM technology)
MAP = [
    ("Coal",          "coal",    "coal (conv pul)"),
    ("Gas CCGT",      "gas",     "gas (CC)"),
    ("Solar PV",      "solar",   "PV"),
    ("Onshore wind",  "wind",    "wind"),
    ("Offshore wind", "wind",    "wind_offshore"),
    ("Nuclear",       "nuclear", "Gen_III"),
]
PARAM = {"Capex": "OCC", "Fixed O&M": "OM-fixed", "Variable O&M": "OM-var"}

# proposed values: BNEF Mid in GCAM units, plus nuclear from the asset files
prop = {}
for r in csv.DictReader(open(OUT / "bnef_korea_three_units_model_years.csv")):
    if r["scenario"] == "Mid":
        prop[(r["metric"], r["technology_model"], int(r["year"]))] = float(r["gcam_value"])
for r in rows:
    prop[(r["metric"], r["technology_model"], r["year"])] = r["gcam_value"]

# current GCAM values, with line numbers
cur, line = {}, {}
for r in csv.DictReader(open(OUT / "gcam_current_costs.csv")):
    k = (r["technology"], r["parameter"], int(r["year"]))
    cur[k] = float(r["value"]); line[k] = int(r["xml_line"])

out = []
for mtech, sub, gtech in MAP:
    for metric, gparam in PARAM.items():
        for y in YR:
            if y == 2021:
                continue                 # GCAM has no 2021 period
            c = cur.get((gtech, gparam, y))
            p = prop.get((metric, mtech, y))
            if p is None:          # nothing proposed, nothing to map
                continue
            out.append({
                "macro_technology": mtech,
                "gcam_subsector": sub,
                "gcam_technology": gtech,
                "metric": metric,
                "gcam_parameter": gparam,
                "unit_1975usd": {"Capex": "$/kW", "Fixed O&M": "$/kW/yr",
                                 "Variable O&M": "$/GJ"}[metric],
                "year": y,
                "gcam_current": round(c, 4) if c is not None else "",
                "proposed_korea": round(p, 4) if p is not None else "",
                "pct_change": (round(100 * (p - c) / c, 1)
                               if (c and p is not None) else ""),
                "xml_line": line.get((gtech, gparam, y), ""),
            })

# capacity factors, which must move with the costs or the LCOE is wrong
KOREA_CF = {"Solar PV": 0.134, "Onshore wind": 0.238, "Offshore wind": 0.337,
            "Coal": 0.65, "Nuclear": 0.85}
for mtech, sub, gtech in MAP:
    if mtech not in KOREA_CF:
        continue
    for y in YR:
        if y == 2021:
            continue
        c = cur.get((gtech, "capacity-factor", y))
        if c is None:
            continue
        p = KOREA_CF[mtech]
        out.append({
            "macro_technology": mtech, "gcam_subsector": sub,
            "gcam_technology": gtech, "metric": "Capacity factor",
            "gcam_parameter": "capacity-factor", "unit_1975usd": "fraction",
            "year": y, "gcam_current": round(c, 4), "proposed_korea": p,
            "pct_change": round(100 * (p - c) / c, 1),
            "xml_line": line.get((gtech, "capacity-factor", y), ""),
        })

f2 = OUT / "macro_to_gcam_mapping.csv"
with open(f2, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(f"  + {f2.name}  ({len(out)} rows)")

print("\n  2050 snapshot, 1975$:")
print(f"    {'tech':14s}{'param':12s}{'GCAM':>12}{'Korea':>12}{'change':>10}  line")
for r in out:
    if r["year"] == 2050 and r["gcam_current"] != "" and r["proposed_korea"] != "":
        print(f"    {r['macro_technology']:14s}{r['gcam_parameter']:12s}"
              f"{r['gcam_current']:>12,.2f}{r['proposed_korea']:>12,.2f}"
              f"{r['pct_change']:>9}%  {r['xml_line']}")
