#!/usr/bin/env python3
"""
Rebuild the model transmission file from the injection-capped ITLs, and
apply distance-scaled investment cost and losses.

Differences from build_transmission_ITL.py:
  * reads outputs/province_ITL_capped.csv (injection-capped LP)
  * investment_cost and loss_fraction scale with corridor length instead
    of being flat, calibrated so the mean corridor is unchanged
  * prints a comparison against the current model file and the metro
    import diagnostic

Output: outputs/transmission_v2_2021_ITL_capped.csv
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "inputs/transmission_v2_2021_MODEL_TEMPLATE.csv"
ITLCSV = HERE / "outputs/province_ITL_capped.csv"
HVDCCSV = HERE / "inputs/gist_data_newest/results/results_by_voltage/hvdc_lines.csv"
CURRENT = HERE.parent.parent.parent / "assets/assets_2021/transmission_v2_2021.csv"
DEMAND = HERE.parent.parent.parent / "system/demand_ref.csv"

LEVEL = "itl_n1"
CAPCOL = "edges--transmission_edge--existing_capacity"
DISTCOL = "edges--transmission_edge--distance"
COSTCOL = "edges--transmission_edge--investment_cost"
LOSSCOL = "edges--transmission_edge--loss_fraction"

FLAT_COST = 443637.83     # $/MW, the template's single value
FLAT_LOSS = 0.03

CODE = {"서울특별시":"SEL","부산광역시":"PUS","대구광역시":"TAE","인천광역시":"INC",
        "광주광역시":"KWJ","대전광역시":"DJJ","울산광역시":"USN","세종특별자치시":"SJG",
        "경기도":"GGI","강원도":"GWN","강원특별자치도":"GWN","충청북도":"CNB",
        "충청남도":"CNA","전라북도":"JNB","전북특별자치도":"JNB","전라남도":"JNA",
        "경상북도":"GNB","경상남도":"GNA","제주특별자치도":"JEJ"}
METRO = {"SEL", "INC", "GGI"}


def read(path, enc="utf-8-sig"):
    with open(path, encoding=enc) as fh:
        return list(csv.DictReader(fh))


def main():
    tmpl = read(TEMPLATE)
    itl = {frozenset((r["code_a"], r["code_b"])): r for r in read(ITLCSV)}

    hvdc = defaultdict(float)
    if HVDCCSV.exists():
        for r in read(HVDCCSV):
            a = CODE.get((r.get("from_region") or "").strip())
            b = CODE.get((r.get("to_region") or "").strip())
            if a and b and a != b:
                hvdc[frozenset((a, b))] += float(r["rate_a_mva"] or 0)
    print("HVDC by corridor (MW, additive, not de-rated): "
          + ", ".join(f"{'-'.join(sorted(k))} {v:,.0f}" for k, v in hvdc.items()))

    # distance scaling calibrated to leave the mean corridor unchanged
    dists = [float(t[DISTCOL]) for t in tmpl]
    dmean = sum(dists) / len(dists)
    cost_per_km = FLAT_COST / dmean
    loss_per_km = FLAT_LOSS / dmean
    print(f"distance: mean {dmean:.1f} km  ->  {cost_per_km:,.0f} $/MW/km, "
          f"{loss_per_km*100:.4f} %/km\n")

    rows, cmp_rows = [], []
    for t in tmpl:
        a, b = t["id"].replace("_transmission", "").split("_to_")
        corr = frozenset((a, b))
        rec = itl.get(corr)
        dc = hvdc.get(corr, 0.0)
        if rec is None:
            ac = 0.0
        else:
            vals = []
            for k in (f"{LEVEL}_a_to_b", f"{LEVEL}_b_to_a"):
                try:
                    v = float(rec[k])
                except (TypeError, ValueError):
                    continue
                if not math.isnan(v):
                    vals.append(abs(v))
            ac = min(vals) if vals else 0.0

        d = float(t[DISTCOL])
        row = dict(t)
        row[CAPCOL] = round(ac + dc, 1)
        row[COSTCOL] = round(cost_per_km * d, 2)
        row[LOSSCOL] = round(loss_per_km * d, 5)
        row["_ac_mw"] = round(ac, 1)
        row["_hvdc_mw"] = round(dc, 1)
        rows.append(row)
        cmp_rows.append((a, b, float(t[CAPCOL]), ac + dc, d))

    out = HERE / "outputs/transmission_v2_2021_ITL_capped.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- comparison ----
    cur = {frozenset(r["id"].replace("_transmission", "").split("_to_")):
           float(r[CAPCOL]) for r in read(CURRENT)}
    print(f"{'corridor':12}{'current GW':>12}{'capped GW':>12}{'change':>10}{'km':>7}")
    for a, b, _, new, d in sorted(cmp_rows, key=lambda r: -cur[frozenset((r[0], r[1]))]):
        old = cur[frozenset((a, b))]
        ch = f"{(new-old)/old*100:+.0f}%" if old else "  n/a"
        print(f"{a}-{b:<8}{old/1000:12.1f}{new/1000:12.1f}{ch:>10}{d:7.0f}")

    tot_old = sum(cur.values()) / 1000
    tot_new = sum(r[3] for r in cmp_rows) / 1000
    print(f"\n{'TOTAL':12}{tot_old:12.1f}{tot_new:12.1f}"
          f"{(tot_new-tot_old)/tot_old*100:+9.0f}%")

    # ---- metro diagnostic ----
    def metro_import(capmap):
        return sum(v for k, v in capmap.items()
                   if len({*k} & METRO) == 1) / 1000
    newmap = {frozenset((a, b)): v for a, b, _, v, _ in cmp_rows}
    mrows = read(DEMAND)
    mpeak = max(sum(float(r[f"Demand_MW_{p}"]) for p in METRO) for r in mrows) / 1000
    npeak = max(sum(float(r[f"Demand_MW_{p}"]) for p in
                    ["SEL","PUS","TAE","INC","KWJ","DJJ","USN","SJG","GGI","GWN",
                     "CNB","CNA","JNB","JNA","GNB","GNA","JEJ"]) for r in mrows) / 1000
    print(f"\nmetro (SEL+INC+GGI) peak demand        {mpeak:7.1f} GW")
    print(f"  interface capacity, current          {metro_import(cur):7.1f} GW"
          f"   ({metro_import(cur)/mpeak:.2f}x peak)")
    print(f"  interface capacity, capped           {metro_import(newmap):7.1f} GW"
          f"   ({metro_import(newmap)/mpeak:.2f}x peak)")
    print(f"\nnational peak demand                   {npeak:7.1f} GW")
    print(f"  total network, current               {tot_old:7.1f} GW   ({tot_old/npeak:.2f}x)")
    print(f"  total network, capped                {tot_new:7.1f} GW   ({tot_new/npeak:.2f}x)")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
