#!/usr/bin/env python3
"""Read the GCAM electricity_water cost XML and pull out the plant-level
capital and O&M numbers, with the line number of every value so the file can
be edited directly.

Only the `electricity` sector is read. The cooling variants under
`elec_<fuel>` carry the incremental cooling-system cost (OCC about 10), not
the plant cost, and are ignored.

Output: outputs/gcam_current_costs.csv
"""
import csv, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
XML = Path("/Users/hanwoongkim/Desktop/1. Net-Zero_Korea/Bucket/0."
           "/gcam-v8.2-Mac-Release-Package/exe/electricity_water_cost_updated.xml")
OUT = HERE / "outputs"; OUT.mkdir(exist_ok=True)

TAGS = {"capital-overnight": ("OCC", "1975$/kW"),
        "OM-fixed":          ("OM-fixed", "1975$/kW/yr"),
        "OM-var":            ("OM-var", "1975$/GJ"),
        "fixed-charge-rate": ("FCR", "fraction"),
        "capacity-factor":   ("capacity-factor", "fraction")}


def main():
    lines = XML.read_text().split("\n")
    g = next(i for i, l in enumerate(lines) if "<global-technology-database>" in l)

    rows = []
    loc = None; tech = None; kind = None; yr = None
    for i in range(g, len(lines)):
        l = lines[i]
        m = re.search(r'<location-info\s+sector-name="([^"]*)"\s+subsector-name="([^"]*)"', l)
        if m:
            loc = (m.group(1), m.group(2)); continue
        m = re.search(r'<(intermittent-technology|pass-through-technology|technology)\s+name="([^"]*)"', l)
        if m:
            kind, tech = m.group(1), m.group(2); yr = None; continue
        if loc is None or loc[0] != "electricity":
            continue
        m = re.search(r'<period year="(\d+)"', l)
        if m:
            yr = int(m.group(1)); continue
        if yr is None:
            continue
        for tag, (name, unit) in TAGS.items():
            m = re.search(rf"<{tag}>([\d.eE+-]+)</{tag}>", l)
            if m:
                rows.append({"sector": loc[0], "subsector": loc[1],
                             "technology": tech, "kind": kind,
                             "parameter": name, "unit": unit,
                             "year": yr, "value": float(m.group(1)),
                             "xml_line": i + 1})

    f = OUT / "gcam_current_costs.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    techs = sorted({r["technology"] for r in rows})
    yrs = sorted({r["year"] for r in rows})
    print(f"  + {f.name}  ({len(rows)} values, {len(techs)} technologies, "
          f"years {yrs[0]}-{yrs[-1]})")
    print(f"    technologies: {', '.join(techs)}")


if __name__ == "__main__":
    main()
