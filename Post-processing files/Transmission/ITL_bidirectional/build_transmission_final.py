#!/usr/bin/env python3
"""
Final transmission file: injection-capped ITLs, with a metro-boundary
correction calibrated to KPX's published 수도권 융통한계, plus
distance-scaled investment cost and losses.

What is changed, and what is not
--------------------------------
  * corridors CROSSING the metro boundary (exactly one endpoint in
    SEL/INC/GGI): AC capacity scaled by a factor solved so the metro
    import limit matches KPX
  * corridors INSIDE the metro (both endpoints in SEL/INC/GGI): unchanged
  * all non-metro corridors: unchanged
  * HVDC: never de-rated anywhere; converter-scheduled DC flow is not
    subject to AC loop flow

Calibration anchor
------------------
KPX, 2024년도 전력계통 운영실적: the metro (수도권) 융통전력 한계량
ranges from 12,000 MW in January to 13,800 MW in August, and was exceeded
once in 2024 (11 June, 10:00). The August peak-month figure is used here,
since a capacity-expansion model should be sized to the stressed case.

Why a correction is needed at all: the 31 ITLs are each solved with the
rest of the network free to redispatch to maximise flow across that one
interface, so they are not simultaneously achievable. A transport model
treats them as independent and loads all of them at once. Korea also
plans these corridors to N-2 while the ITL LP uses a simplified N-1.

Output: outputs/transmission_v2_2021_FINAL.csv
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPPED = HERE / "outputs/transmission_v2_2021_ITL_capped.csv"
CURRENT = HERE.parent.parent.parent / "assets/assets_2021/transmission_v2_2021.csv"
DEMAND = HERE.parent.parent.parent / "system/demand_ref.csv"
OUT = HERE / "outputs/transmission_v2_2021_FINAL.csv"

CAPCOL = "edges--transmission_edge--existing_capacity"
METRO = {"SEL", "INC", "GGI"}
PROV = ["SEL", "PUS", "TAE", "INC", "KWJ", "DJJ", "USN", "SJG", "GGI",
        "GWN", "CNB", "CNA", "JNB", "JNA", "GNB", "GNA", "JEJ"]

METRO_LIMIT_MW = 13_800.0     # KPX 2024, August (peak month)


def read(p):
    with open(p, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def corr(i):
    return frozenset(i.replace("_transmission", "").split("_to_"))


def crosses_metro(c):
    return len({*c} & METRO) == 1


def main():
    rows = read(CAPPED)
    cur = {corr(r["id"]): float(r[CAPCOL]) for r in read(CURRENT)}
    ac = {corr(r["id"]): float(r["_ac_mw"]) for r in rows}
    dc = {corr(r["id"]): float(r["_hvdc_mw"]) for r in rows}

    m_ac = sum(v for c, v in ac.items() if crosses_metro(c))
    m_dc = sum(v for c, v in dc.items() if crosses_metro(c))
    factor = max(0.0, (METRO_LIMIT_MW - m_dc) / m_ac)

    print(f"metro boundary, capped ITL : {(m_ac+m_dc)/1000:6.1f} GW "
          f"(AC {m_ac/1000:.1f} + HVDC {m_dc/1000:.1f})")
    print(f"KPX limit, Aug 2024        : {METRO_LIMIT_MW/1000:6.1f} GW")
    print(f"=> AC factor on metro-crossing corridors only = {factor:.3f}\n")

    out_rows, changed = [], []
    for r in rows:
        c = corr(r["id"])
        nr = dict(r)
        if crosses_metro(c):
            nr[CAPCOL] = round(ac[c] * factor + dc[c], 1)
            changed.append(c)
        else:
            nr[CAPCOL] = round(ac[c] + dc[c], 1)
        nr.pop("_ac_mw", None)
        nr.pop("_hvdc_mw", None)
        out_rows.append(nr)

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    new = {corr(r["id"]): float(r[CAPCOL]) for r in out_rows}
    print("CHANGED (metro boundary):")
    for c in sorted(changed, key=lambda k: -new[k]):
        a, b = sorted(c)
        print(f"   {a}-{b:<6} orig {cur[c]/1000:5.1f}  capped {(ac[c]+dc[c])/1000:5.1f}"
              f"  final {new[c]/1000:5.1f} GW")

    print("\nUNCHANGED from the capped ITL (metro-internal + all others):")
    for c in sorted((k for k in new if k not in changed), key=lambda k: -new[k])[:6]:
        a, b = sorted(c)
        print(f"   {a}-{b:<6} orig {cur[c]/1000:5.1f}  final {new[c]/1000:5.1f} GW")
    print(f"   ... and {len(new)-len(changed)-6} more")

    d = read(DEMAND)
    npeak = max(sum(float(r[f"Demand_MW_{p}"]) for p in PROV) for r in d) / 1000
    tot_cur, tot_new = sum(cur.values()) / 1000, sum(new.values()) / 1000
    m_new = sum(v for c, v in new.items() if crosses_metro(c)) / 1000
    m_cur = sum(v for c, v in cur.items() if crosses_metro(c)) / 1000
    print(f"\n{'':22}{'current':>10}{'final':>10}")
    print(f"{'metro boundary':22}{m_cur:10.1f}{m_new:10.1f}  GW")
    print(f"{'total network':22}{tot_cur:10.1f}{tot_new:10.1f}  GW")
    print(f"{'x national peak':22}{tot_cur/npeak:10.2f}{tot_new/npeak:10.2f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
