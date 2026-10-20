#!/usr/bin/env python3
"""Write Korean costs into the GCAM electricity_water cost XML.

Reads  : electricity_water_cost_updated.xml            (untouched)
Writes : electricity_water_cost_updated_KR.xml         (the edited copy)
Logs   : outputs/gcam_edit_log.csv

Scope
  * `electricity` sector only, inside <global-technology-database>.
    The elec_<fuel> cooling variants carry the incremental cooling cost
    (OCC about 10) and are deliberately left alone.
  * eight technologies, three parameters each:
      capital-overnight, OM-fixed, OM-var
  * years 2021 through 2050 take the Korean value;
    2055 through 2100 are held flat at the 2050 Korean value.
  * capacity-factor and fixed-charge-rate are NOT touched.
  * CCS takes Japan as the proxy (BNEF has no Korean CCS row). CCS has no
    2021 value, so the 2021 period of the two CCS technologies is left alone.

Edits are line-based, so formatting, comments and whitespace survive and the
line numbers recorded in gcam_current_costs.csv stay valid.
"""
import csv, re, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
SRC = Path("/Users/hanwoongkim/Desktop/1. Net-Zero_Korea/Bucket/0."
           "/gcam-v8.2-Mac-Release-Package/exe/electricity_water_cost_updated.xml")
DST = SRC.with_name("electricity_water_cost_updated_KR.xml")

MAP = {"Coal": "coal (conv pul)", "Gas CCGT": "gas (CC)", "Solar PV": "PV",
       "Onshore wind": "wind", "Offshore wind": "wind_offshore",
       "Nuclear": "Gen_III",
       "Coal CCS": "coal (conv pul CCS)", "Gas CCS": "gas (CC CCS)"}
PARAM = {"Capex": ("OCC", "capital-overnight"),
         "Fixed O&M": ("OM-fixed", "OM-fixed"),
         "Variable O&M": ("OM-var", "OM-var")}
DATA_YEARS = [2021, 2025, 2030, 2035, 2040, 2045, 2050]
HOLD_FROM = 2050          # years after this take the 2050 value


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def main():
    # proposed values, in GCAM units
    prop = {}
    for r in csv.DictReader(open(OUT / "bnef_korea_three_units_model_years.csv")):
        if r["scenario"] == "Mid":
            prop[(r["metric"], r["technology_model"], int(r["year"]))] = float(r["gcam_value"])
    for r in csv.DictReader(open(OUT / "nuclear_from_macro.csv")):
        prop[(r["metric"], r["technology_model"], int(r["year"]))] = float(r["gcam_value"])
    for r in csv.DictReader(open(OUT / "ccs_japan_proxy.csv")):
        if r["scenario"] == "Mid":
            prop[(r["metric"], r["technology_model"], int(r["year"]))] = float(r["gcam_value"])

    # current values and their line numbers
    cur = list(csv.DictReader(open(OUT / "gcam_current_costs.csv")))
    byline = {}
    for r in cur:
        byline[int(r["xml_line"])] = r

    shutil.copy2(SRC, DST)
    lines = DST.read_text().split("\n")

    log, skipped = [], []
    for ln, r in sorted(byline.items()):
        gtech, gparam, year = r["technology"], r["parameter"], int(r["year"])
        mtech = next((m for m, g in MAP.items() if g == gtech), None)
        if mtech is None:
            continue
        metric = next((m for m, (p, _) in PARAM.items() if p == gparam), None)
        if metric is None:                       # FCR, capacity-factor
            continue
        src_year = year if year in DATA_YEARS else (HOLD_FROM if year > HOLD_FROM else None)
        if src_year is None:                     # 1975..2015, left alone
            continue
        v = prop.get((metric, mtech, src_year))
        if v is None:
            skipped.append((mtech, gparam, year))
            continue

        tag = PARAM[metric][1]
        old_line = lines[ln - 1]
        new_line, n = re.subn(rf"(<{tag}>)[\d.eE+-]+(</{tag}>)",
                              rf"\g<1>{fmt(v)}\g<2>", old_line)
        assert n == 1, f"line {ln}: expected one <{tag}>, got {n}"
        lines[ln - 1] = new_line
        log.append({"xml_line": ln, "gcam_technology": gtech,
                    "macro_technology": mtech, "parameter": gparam,
                    "year": year, "value_source_year": src_year,
                    "old_value": float(r["value"]), "new_value": round(v, 6),
                    "held_flat": year > HOLD_FROM})

    DST.write_text("\n".join(lines))

    f = OUT / "gcam_edit_log.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(log[0])); w.writeheader(); w.writerows(log)

    print(f"  wrote {DST.name}")
    print(f"  + {f.name}  ({len(log)} values changed)")
    if skipped:
        print(f"  skipped (no Korean value): {len(skipped)}")
        for s in skipped[:6]:
            print(f"      {s[0]} {s[1]} {s[2]}")

    import collections
    c = collections.Counter((r["macro_technology"], r["parameter"]) for r in log)
    print(f"\n  {'technology':15s}{'OCC':>6}{'OM-fixed':>10}{'OM-var':>8}")
    for t in MAP:
        print(f"  {t:15s}{c[(t,'OCC')]:>6}{c[(t,'OM-fixed')]:>10}{c[(t,'OM-var')]:>8}")
    nf = sum(1 for r in log if r["held_flat"])
    print(f"\n  of which held flat at the 2050 value: {nf}")


if __name__ == "__main__":
    main()
