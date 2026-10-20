#!/usr/bin/env python3
"""
Option (a): flat simultaneity de-rating on the injection-capped ITLs,
calibrated so metro import capability matches the published figure.

Why a de-rating is needed at all
--------------------------------
The 32 ITLs are each solved independently, with the rest of the network
free to redispatch to maximise flow across that one interface. They are
not simultaneously achievable, but a transport model treats them as 32
independent constraints and will load all of them at once. Korea also
plans these corridors to N-2, while the ITL LP uses a simplified N-1.

Calibration anchor
------------------
KPX, 2024 electricity system operation record:
  * 41.1% of national demand is in the metro area (SEL + INC + GGI)
  * 30.3% of supply capability is generated there
  * 11.1% is imported from outside the metro (융통전력)
  * the metro import limit was exceeded once in 2024, so it binds

At the model's 2021 national peak that puts metro import at about 10 GW.
The model's own metro demand share is 40.9%, matching the published
41.1%, so the demand side is already consistent.

Output: outputs/transmission_v2_2021_ITL_derated.csv
"""
import csv
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "inputs/transmission_v2_2021_MODEL_TEMPLATE.csv"
CAPPED = HERE / "outputs/transmission_v2_2021_ITL_capped.csv"
CURRENT = HERE.parent.parent.parent / "assets/assets_2021/transmission_v2_2021.csv"
DEMAND = HERE.parent.parent.parent / "system/demand_ref.csv"

CAPCOL = "edges--transmission_edge--existing_capacity"
METRO = {"SEL", "INC", "GGI"}
PROV = ["SEL", "PUS", "TAE", "INC", "KWJ", "DJJ", "USN", "SJG", "GGI",
        "GWN", "CNB", "CNA", "JNB", "JNA", "GNB", "GNA", "JEJ"]

METRO_IMPORT_SHARE = 0.111       # KPX 2024: 11.1% of national supply capability


def read(p, enc="utf-8-sig"):
    with open(p, encoding=enc) as fh:
        return list(csv.DictReader(fh))


def corr(row_id):
    return frozenset(row_id.replace("_transmission", "").split("_to_"))


def crosses_metro(c):
    return len({*c} & METRO) == 1


def main():
    rows = read(CAPPED)
    cur = {corr(r["id"]): float(r[CAPCOL]) for r in read(CURRENT)}
    cap = {corr(r["id"]): float(r[CAPCOL]) for r in rows}

    d = read(DEMAND)
    npeak = max(sum(float(r[f"Demand_MW_{p}"]) for p in PROV) for r in d) / 1000
    mpeak = max(sum(float(r[f"Demand_MW_{p}"]) for p in METRO) for r in d) / 1000
    target = METRO_IMPORT_SHARE * npeak

    m_cur = sum(v for c, v in cur.items() if crosses_metro(c)) / 1000
    m_cap = sum(v for c, v in cap.items() if crosses_metro(c)) / 1000
    ac = {corr(r["id"]): float(r.get("_ac_mw", r[CAPCOL])) for r in rows}
    dc = {corr(r["id"]): float(r.get("_hvdc_mw", 0)) for r in rows}
    m_ac = sum(v for c, v in ac.items() if crosses_metro(c)) / 1000
    m_dc = sum(v for c, v in dc.items() if crosses_metro(c)) / 1000
    factor = max(0.0, (target - m_dc) / m_ac)   # HVDC is not de-rated

    print(f"national peak        {npeak:7.1f} GW")
    print(f"metro peak           {mpeak:7.1f} GW   ({mpeak/npeak*100:.1f}% of national; "
          f"KPX reports 41.1%)")
    print(f"metro import target  {target:7.1f} GW   (KPX: 11.1% of supply capability)\n")
    print(f"metro import, current ITL        {m_cur:7.1f} GW  ({m_cur/target:.2f}x target)")
    print(f"metro import, injection-capped   {m_cap:7.1f} GW  ({m_cap/target:.2f}x target)")
    print(f"\n=> simultaneity de-rating factor = {factor:.3f}\n")

    # sweep, so the choice of anchor is visible rather than buried
    print(f"{'factor':>8}{'metro GW':>11}{'total GW':>11}{'x nat peak':>12}")
    for f in (1.0, 0.9, 0.8, 0.7, 0.6, round(factor, 2), 0.5, 0.4):
        mt = m_ac * f + m_dc
        tt = (sum(ac.values()) * f + sum(dc.values())) / 1000
        mark = "  <= calibrated" if abs(f - round(factor, 2)) < 1e-9 else ""
        print(f"{f:8.2f}{mt:11.1f}{tt:11.1f}{tt/npeak:12.2f}{mark}")

    out_rows = []
    for r in rows:
        nr = dict(r)
        ac = float(r.get("_ac_mw", r[CAPCOL]))
        dc = float(r.get("_hvdc_mw", 0))
        nr[CAPCOL] = round(ac * factor + dc, 1)   # HVDC is not de-rated
        nr.pop("_ac_mw", None); nr.pop("_hvdc_mw", None)
        out_rows.append(nr)

    out = HERE / "outputs/transmission_v2_2021_ITL_derated.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    new = {corr(r["id"]): float(r[CAPCOL]) for r in out_rows}
    print(f"\n{'corridor':12}{'orig GW':>10}{'capped':>9}{'derated':>9}{'vs orig':>9}")
    for c in sorted(cur, key=lambda k: -cur[k]):
        a, b = sorted(c)
        print(f"{a}-{b:<8}{cur[c]/1000:10.1f}{cap[c]/1000:9.1f}{new[c]/1000:9.1f}"
              f"{(new[c]-cur[c])/cur[c]*100 if cur[c] else 0:8.0f}%")
    print(f"\n{'TOTAL':12}{sum(cur.values())/1000:10.1f}{sum(cap.values())/1000:9.1f}"
          f"{sum(new.values())/1000:9.1f}"
          f"{(sum(new.values())-sum(cur.values()))/sum(cur.values())*100:8.0f}%")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
