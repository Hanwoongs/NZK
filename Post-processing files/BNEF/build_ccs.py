#!/usr/bin/env python3
"""Coal CCS and gas CCS, using Japan as the proxy for Korea.

BNEF's Sheet3 carries CCS costs for China, Japan and the United States only —
there is no South Korea row. Japan is adopted as the proxy: its EPC cost
structure is the closest of the three to Korea's, and the model's existing CCS
fixed O&M already matches Japan Mid to within 0.12%, so this also makes the
inputs internally consistent.

Rejected alternative: a three-country average. China is 878 $/kW against the
United States at 5,646 — a 6.4x spread — so the mean is dominated by the US
and is not a meaningful central value.

Japan CCS data runs 2022-2050, and **2021 is deliberately omitted**. The first
year available, 2022, is a first-of-a-kind cost — 10,100 $/kW for coal CCS
against 2,697 the following year — and carrying it back to 2021 would put a
4x spike at the front of the series. The model has no CCS asset in 2021
either: assets_2021 contains neither coalpowerCCS nor NaturalGasPowerCCS.

Output: outputs/ccs_japan_proxy.csv  (same shape as the BNEF long file)
"""
import csv
from pathlib import Path
import openpyxl

HERE = Path(__file__).resolve().parent
XLSX = HERE.parent.parent / "20251205 BNEF Korea data .xlsx"
OUT = HERE / "outputs"

DEFL = 0.870        # 2024$ -> 2021$
CPI = 5.0400        # 2021$ -> 1975$
YR = [2025, 2030, 2035, 2040, 2045, 2050]      # no 2021: see the docstring

# BNEF label -> model label
TECH = {"Coal CCS": "Coal CCS", "CCGT CCS": "Gas CCS"}
SPEC = {
    "Capex":        ("$/kW",    "$/MW",    1000.0, "$/kW",    1.0),
    "Fixed O&M":    ("$/MW/yr", "$/MW-yr",    1.0, "$/kW/yr", 0.001),
    "Variable O&M": ("$/MWh",   "$/MWh",      1.0, "$/GJ",    1/3.6),
}


def num(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    rows = list(wb["Sheet3"].iter_rows(min_row=2, values_only=True))
    hdr = rows[0]
    yi = {y: 5 + i for i, y in enumerate(hdr[5:]) if isinstance(y, int)}

    out = []
    for bt, mt in TECH.items():
        for metric, (b_u, m_u, m_f, g_u, g_f) in SPEC.items():
            for scen in ("Low", "Mid", "High"):
                src = next((r for r in rows[1:]
                            if r[0] == metric and r[1] == "Japan"
                            and r[2] == bt and r[3] == scen), None)
                if src is None:
                    print(f"  ! missing {bt} {metric} {scen}")
                    continue
                for y in YR:
                    v = num(src[yi[y]])
                    if v is None:
                        continue
                    out.append({
                        "metric": metric,
                        "technology_bnef": f"{bt} (Japan)",
                        "technology_model": mt,
                        "scenario": scen,
                        "year": y,
                        "bnef_value": round(v, 4),
                        "bnef_unit": f"2024$ {b_u}",
                        "macro_value": round(v * DEFL * m_f, 4),
                        "macro_unit": f"2021$ {m_u}",
                        "gcam_value": round(v * DEFL / CPI * g_f, 6),
                        "gcam_unit": f"1975$ {g_u}",
                        "note": "Japan proxy; no Korean CCS data in BNEF",
                    })

    f = OUT / "ccs_japan_proxy.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(f"  + {f.name}  ({len(out)} rows)")

    mid = {(r["technology_model"], r["metric"], r["year"]): r
           for r in out if r["scenario"] == "Mid"}
    print(f"\n  Japan Mid, MACRO units (2021$)")
    print(f"  {'tech':10s}{'metric':14s}{'unit':12s}" + "".join(f"{y:>12}" for y in YR))
    for mt in ("Coal CCS", "Gas CCS"):
        for metric in SPEC:
            r0 = mid.get((mt, metric, 2050))
            if not r0:
                continue
            u = r0["macro_unit"].replace("2021$ ", "")
            print(f"  {mt:10s}{metric:14s}{u:12s}" +
                  "".join(f"{mid[(mt,metric,y)]['macro_value']:>12,.2f}"
                          if (mt, metric, y) in mid else f"{'-':>12}" for y in YR))


if __name__ == "__main__":
    main()
