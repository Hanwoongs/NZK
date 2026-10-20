#!/usr/bin/env python3
"""BNEF Korea cost metrics in three unit systems: BNEF native, MACRO, GCAM.

BNEF publishes 2024$. MACRO runs in 2021$. GCAM runs in 1975$.

  2024$ -> 2021$   x 0.870      (deflator already used for the model inputs,
                                 verified: PV Mid 2050  436.7 x 0.870 = 380.0
                                 against the model's 380,073 $/MW)
  2021$ -> 1975$   / 5.0400     (US CPI ratio, the same factor used in reverse
                                 for the GCAM fuel-price conversion)
  2024$ -> 1975$   x 0.172619

Unit handling per metric:

  metric        BNEF          MACRO           GCAM
  Capex         $/kW          $/MW            $/kW
  Fixed O&M     $/MW/yr       $/MW-yr         $/kW/yr
  Variable O&M  $/MWh         $/MWh           $/GJ
  LCOE          $/MWh         $/MWh           $/GJ
  SRMC          $/MWh         $/MWh           $/GJ

GCAM caveat: 1975$/kW and 1975$/kW/yr match GCAM's electricity capital and
fixed-O&M convention. Variable terms are given in 1975$/GJ because GCAM's
energy unit is EJ; if the target GCAM input expects 1975$/MWh instead,
multiply the GCAM column by 3.6.

Output: outputs/bnef_korea_three_units_long.csv   (every year 2018-2050)
        outputs/bnef_korea_three_units_model_years.csv  (7 model periods)
        outputs/bnef_korea_mid_macro_wide.csv     (what the model actually uses)
"""
import csv
from pathlib import Path
import openpyxl

HERE = Path(__file__).resolve().parent
XLSX = HERE.parent.parent / "20251205 BNEF Korea data .xlsx"
OUT = HERE / "outputs"; OUT.mkdir(exist_ok=True)

DEFL_2024_2021 = 0.870          # BNEF 2024$ -> model 2021$
CPI_1975_2021 = 5.0400          # 2021$ = 1975$ x 5.0400
DEFL_2024_1975 = DEFL_2024_2021 / CPI_1975_2021
MODEL_YEARS = [2021, 2025, 2030, 2035, 2040, 2045, 2050]

# metric -> (bnef unit, macro unit, macro factor, gcam unit, gcam factor)
# factors are applied to the BNEF number AFTER the currency deflator
SPEC = {
    "Capex":                  ("$/kW",    "$/MW",    1000.0, "$/kW",    1.0),
    "Fixed O&M":              ("$/MW/yr", "$/MW-yr",    1.0, "$/kW/yr", 0.001),
    "Variable O&M":           ("$/MWh",   "$/MWh",      1.0, "$/GJ",    1/3.6),
    "LCOE":                   ("$/MWh",   "$/MWh",      1.0, "$/GJ",    1/3.6),
    "Short-run marginal cost":("$/MWh",   "$/MWh",      1.0, "$/GJ",    1/3.6),
}
# BNEF label -> the name used in the model
MODEL_NAME = {
    "CCGT":          "Gas CCGT",
    "Coal":          "Coal",
    "PV fixed-axis": "Solar PV",
    "Wind onshore":  "Onshore wind",
    "Wind offshore": "Offshore wind",
    "OCGT":          "Gas CT",
}


def num(v):
    if v is None or v is False or v == "False":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f          # drop NaN


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    rows = list(wb["Sheet1"].iter_rows(min_row=2, values_only=True))
    hdr = rows[0]
    years = [(y, 5 + i) for i, y in enumerate(hdr[5:]) if isinstance(y, int)]

    long_rows = []
    for r in rows[1:]:
        metric, region, tech, scen, unit = r[0], r[1], r[2], r[3], r[4]
        if metric not in SPEC:
            continue
        b_unit, m_unit, m_f, g_unit, g_f = SPEC[metric]
        if unit != b_unit:
            print(f"  ! unit mismatch {metric}/{tech}: sheet says {unit}, expected {b_unit}")
        for yr, col in years:
            v = num(r[col])
            if v is None:
                continue
            long_rows.append({
                "metric": metric,
                "technology_bnef": tech,
                "technology_model": MODEL_NAME.get(tech, tech),
                "scenario": scen,
                "year": yr,
                "bnef_value": round(v, 4),
                "bnef_unit": f"2024$ {b_unit}",
                "macro_value": round(v * DEFL_2024_2021 * m_f, 4),
                "macro_unit": f"2021$ {m_unit}",
                "gcam_value": round(v * DEFL_2024_1975 * g_f, 6),
                "gcam_unit": f"1975$ {g_unit}",
            })

    cols = list(long_rows[0])
    order = {s: i for i, s in enumerate(["Low", "Mid", "High"])}
    long_rows.sort(key=lambda d: (d["metric"], d["technology_model"],
                                  order.get(d["scenario"], 9), d["year"]))

    f1 = OUT / "bnef_korea_three_units_long.csv"
    with open(f1, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(long_rows)
    print(f"  + {f1.name}  ({len(long_rows)} rows, {years[0][0]}-{years[-1][0]})")

    my = [d for d in long_rows if d["year"] in MODEL_YEARS]
    f2 = OUT / "bnef_korea_three_units_model_years.csv"
    with open(f2, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(my)
    print(f"  + {f2.name}  ({len(my)} rows, 7 model periods)")

    # wide: Mid scenario in MACRO units, the form the model consumes
    keys, wide = [], {}
    for d in my:
        if d["scenario"] != "Mid":
            continue
        k = (d["metric"], d["technology_model"], d["macro_unit"])
        wide.setdefault(k, {})[d["year"]] = d["macro_value"]
        if k not in keys:
            keys.append(k)
    f3 = OUT / "bnef_korea_mid_macro_wide.csv"
    with open(f3, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "technology", "unit"] + MODEL_YEARS)
        for k in sorted(keys):
            w.writerow(list(k) + [wide[k].get(y, "") for y in MODEL_YEARS])
    print(f"  + {f3.name}  ({len(keys)} rows, Mid only, MACRO units)")

    print(f"\n  deflators:  2024$->2021$ x{DEFL_2024_2021}"
          f"   2021$->1975$ /{CPI_1975_2021}"
          f"   2024$->1975$ x{DEFL_2024_1975:.6f}")


if __name__ == "__main__":
    main()
