#!/usr/bin/env python3
"""
Recreate the 6 summary charts for a MacroEnergy myopic result set.

Charts (written into the results folder):
  capacity_by_technology_2021_2035.png
  capacity_decision_by_period.png
  generation_by_technology_2021_2035.png
  curtailment_rate_by_technology_2021_2035.png
  dispatch_annual_avg_hourofday_2035.png
  dispatch_representative_days_2035.png

Usage:  python3 make_ref_charts.py [results_dir]     (default: ref)
"""
import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

BASE = Path(__file__).resolve().parent
RES = BASE / (sys.argv[1] if len(sys.argv) > 1 else "ref")
PERIOD_YEAR = {1: 2021, 2: 2025, 3: 2030, 4: 2035}
LAST_PERIOD = 4

# tech stack: bottom -> top
STACK = [
    ("Coal",          "#1A1A1A"),
    ("Gas CCGT",      "#3D8BD4"),
    ("Nuclear",       "#FD9F3A"),
    ("Coal CCS",      "#A07850"),
    ("Gas CCS",       "#A9D3F0"),
    ("Hydro",         "#0E2F44"),
    ("Pumped Hydro",  "#5FB0A7"),
    ("Solar PV",      "#FFCF29"),
    ("Onshore Wind",  "#17BECF"),
    ("Offshore Wind", "#2CA02C"),
    ("Battery",       "#7B2FBE"),
]
ORDER  = [t for t, _ in STACK]
COLOR  = {t: c for t, c in STACK}


def classify(resource_type: str, resource_id: str):
    rid = str(resource_id).lower()
    rt = resource_type
    if rt.startswith("ThermalPowerCCS{NaturalGas}"): return "Gas CCS"
    if rt.startswith("ThermalPowerCCS{Coal}"):       return "Coal CCS"
    if rt.startswith("ThermalPower{NaturalGas}"):    return "Gas CCGT"
    if rt.startswith("ThermalPower{Coal}"):          return "Coal"
    if rt.startswith("ThermalPower{Uranium}"):       return "Nuclear"
    if rt.startswith("Battery"):                     return "Battery"
    if rt.startswith("HydroRes"):                    return "Hydro"
    if rt.startswith("PumpedHydro") or "pumpedhydro" in rid: return "Pumped Hydro"
    if rt.startswith("VRE"):
        if "offshore" in rid or "offwind" in rid: return "Offshore Wind"
        if "onshore" in rid or "onwind" in rid:   return "Onshore Wind"
        return "Solar PV"
    return None


def legend_handles():
    return [mpatches.Patch(color=COLOR[t], label=t) for t in reversed(ORDER)]


def stacked_bar(ax, pivot, xlabels, width=0.55, lab_min=1.0, fs=9):
    x = np.arange(len(xlabels))
    bottom = np.zeros(len(xlabels))
    for t in ORDER:
        if t not in pivot:
            continue
        v = np.array(pivot[t], float)
        ax.bar(x, v, width, bottom=bottom, color=COLOR[t], zorder=2)
        for xi, (vi, bi) in enumerate(zip(v, bottom)):
            if vi >= lab_min:
                ax.text(xi, bi + vi / 2, f"{vi:.1f}", ha="center", va="center",
                        fontsize=fs, fontweight="bold",
                        color="white" if t in ("Coal", "Gas CCGT", "Coal CCS",
                                                "Offshore Wind", "Battery", "Hydro") else "#222")
        bottom += v
    ax.set_xticks(x); ax.set_xticklabels(xlabels)
    ax.yaxis.grid(True, color="#E4E4E4", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# ---------------------------------------------------------------- capacity.csv
def load_capacity():
    """returns dict[var] -> dict[tech] -> {year: GW}  and per-period new/retired."""
    out = {"capacity": {}, "new_capacity": {}, "retired_capacity": {}}
    for p, yr in PERIOD_YEAR.items():
        f = RES / f"results_period_{p}" / "capacity.csv"
        if not f.exists():
            continue
        with open(f) as fh:
            for r in csv.DictReader(fh):
                if r["commodity"] != "Electricity":
                    continue
                # keep the power rating (Edge), drop storage energy (MWh)
                if r["component_type"].startswith("Storage"):
                    continue
                # storage / hydro resources expose TWO power edges per unit
                # (discharge + charge/inflow); the power rating is the
                # discharge edge only -> skip the other to avoid double count.
                cid = r["component_id"]
                if cid.endswith("_charge_edge") or cid.endswith("_inflow_edge"):
                    continue
                var = r["variable"]
                if var not in out:
                    continue
                tech = classify(r["resource_type"], r["resource_id"])
                if tech is None:
                    continue
                try:
                    gw = float(r["value"]) / 1000.0
                except ValueError:
                    continue
                out[var].setdefault(tech, {}).setdefault(yr, 0.0)
                out[var][tech][yr] += gw
    return out


# ---------------------------------------------------------------- flows.csv (stream)
def scan_flows(period, want_hourly=False):
    """
    Sum electricity delivered to the grid by tech.
    returns (annual_TWh: dict[tech]->TWh, hourly: dict[tech]->np.array[8760] or None)
    Grid-delivery = flow on an edge whose node_out starts 'elec_' and node_in does not
    (i.e. injection into an electricity node), minus battery/pumped charging.
    """
    f = RES / f"results_period_{period}" / "flows.csv"
    annual = {}
    hourly = {t: np.zeros(8760) for t in ORDER} if want_hourly else None
    with open(f) as fh:
        rd = csv.reader(fh)
        h = next(rd)
        i_ni, i_no = h.index("node_in"), h.index("node_out")
        i_rt, i_rid = h.index("resource_type"), h.index("resource_id")
        i_var, i_t, i_v = h.index("variable"), h.index("time"), h.index("value")
        for row in rd:
            if row[i_var] != "flow":
                continue
            no, ni = row[i_no], row[i_ni]
            rt = row[i_rt]
            if rt.startswith("TransmissionLink") or rt.startswith("OneWayTransmissionLink"):
                continue
            tech = classify(rt, row[i_rid])
            if tech is None:
                continue
            try:
                val = float(row[i_v])
            except ValueError:
                continue
            # net grid contribution: flow value is already signed (discharge +,
            # charge -), so just take `value` for any edge touching one elec node.
            out_grid = no.startswith("elec_")
            in_grid = ni.startswith("elec_")
            if out_grid == in_grid:      # both or neither -> internal, skip
                continue
            net = val
            annual[tech] = annual.get(tech, 0.0) + net
            if want_hourly:
                ti = int(row[i_t]) - 1
                if 0 <= ti < 8760:
                    hourly[tech][ti] += net
    annual = {k: v / 1e6 for k, v in annual.items()}   # MWh -> TWh
    return annual, hourly


# ---------------------------------------------------------------- curtailment.csv
def load_curtailment(period):
    """curtailed MWh by VRE tech for one period."""
    f = RES / f"results_period_{period}" / "curtailment.csv"
    cur = {}
    with open(f) as fh:
        rd = csv.reader(fh)
        h = next(rd)
        i_rt, i_rid = h.index("resource_type"), h.index("resource_id")
        i_v = h.index("value")
        for row in rd:
            tech = classify(row[i_rt], row[i_rid])
            if tech not in ("Solar PV", "Onshore Wind", "Offshore Wind"):
                continue
            try:
                cur[tech] = cur.get(tech, 0.0) + float(row[i_v])
            except ValueError:
                pass
    return cur


# ====================================================================== main
def main():
    print(f"[dir] {RES}")
    years = list(PERIOD_YEAR.values())
    ylab = [str(y) for y in years]

    cap = load_capacity()

    # ---- 1. capacity by technology ----
    piv = {t: [cap["capacity"].get(t, {}).get(y, 0.0) for y in years] for t in ORDER}
    fig, ax = plt.subplots(figsize=(8, 7))
    stacked_bar(ax, piv, ylab, lab_min=1.0, fs=10)
    ax.set_xlabel("Year"); ax.set_ylabel("Installed capacity (GW)")
    ax.set_title("Installed Capacity by Technology", fontweight="bold", pad=12)
    ax.legend(handles=legend_handles(), fontsize=8, loc="upper left", frameon=True)
    fig.tight_layout()
    fig.savefig(RES / "capacity_by_technology_2021_2035.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + capacity_by_technology_2021_2035.png")

    # ---- 3. capacity decisions (new / retired) by period ----
    fig, ax = plt.subplots(figsize=(9, 6))
    x = np.arange(len(years)); w = 0.38
    newp = {t: [cap["new_capacity"].get(t, {}).get(y, 0.0) for y in years] for t in ORDER}
    retp = {t: [cap["retired_capacity"].get(t, {}).get(y, 0.0) for y in years] for t in ORDER}
    b_new = np.zeros(len(years)); b_ret = np.zeros(len(years))
    for t in ORDER:
        vn = np.array(newp[t], float); vr = -np.array(retp[t], float)
        ax.bar(x - w/2, vn, w, bottom=b_new, color=COLOR[t], zorder=2)
        ax.bar(x + w/2, vr, w, bottom=b_ret, color=COLOR[t], zorder=2, alpha=0.85)
        b_new += vn; b_ret += vr
    ax.axhline(0, color="#888", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(ylab)
    ax.set_ylabel("Capacity change (GW)   ▲ new   ▼ retired")
    ax.set_title("Capacity Decisions by Period", fontweight="bold", pad=12)
    ax.yaxis.grid(True, color="#E4E4E4", lw=0.7); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.legend(handles=legend_handles(), fontsize=8, loc="upper left", frameon=True)
    fig.tight_layout()
    fig.savefig(RES / "capacity_decision_by_period.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + capacity_decision_by_period.png")

    # ---- 2. generation by technology (needs all periods' flows) ----
    gen_by_year = {}
    hourly_last = None
    for p, yr in PERIOD_YEAR.items():
        want_h = (p == LAST_PERIOD)
        print(f"  scanning flows period {p} ...", flush=True)
        ann, hr = scan_flows(p, want_hourly=want_h)
        gen_by_year[yr] = ann
        if want_h:
            hourly_last = hr
    piv = {t: [gen_by_year.get(y, {}).get(t, 0.0) for y in years] for t in ORDER}
    fig, ax = plt.subplots(figsize=(8, 7))
    stacked_bar(ax, piv, ylab, lab_min=5.0, fs=10)
    ax.set_xlabel("Year"); ax.set_ylabel("Annual generation (TWh)")
    ax.set_title("Electricity Generation by Technology", fontweight="bold", pad=12)
    ax.legend(handles=legend_handles(), fontsize=8, loc="upper left", frameon=True)
    fig.tight_layout()
    fig.savefig(RES / "generation_by_technology_2021_2035.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + generation_by_technology_2021_2035.png")

    # ---- 4. curtailment rate by technology ----
    rate = {t: [] for t in ("Solar PV", "Onshore Wind", "Offshore Wind")}
    for p, yr in PERIOD_YEAR.items():
        cur = load_curtailment(p)
        gen = gen_by_year.get(yr, {})
        for t in rate:
            c = cur.get(t, 0.0) / 1e6            # TWh curtailed
            g = gen.get(t, 0.0)                  # TWh delivered
            rate[t].append(100 * c / (c + g) if (c + g) > 0 else 0.0)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    x = np.arange(len(years)); w = 0.25
    for i, t in enumerate(("Solar PV", "Onshore Wind", "Offshore Wind")):
        ax.bar(x + (i - 1) * w, rate[t], w, color=COLOR[t], label=t, zorder=2)
        for xi, rv in zip(x + (i - 1) * w, rate[t]):
            if rv > 0.3:
                ax.text(xi, rv + 0.3, f"{rv:.1f}%", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(ylab)
    ax.set_ylabel("Curtailment rate (%)")
    ax.set_title("VRE Curtailment Rate by Technology", fontweight="bold", pad=12)
    ax.yaxis.grid(True, color="#E4E4E4", lw=0.7); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.legend(fontsize=9, frameon=True)
    fig.tight_layout()
    fig.savefig(RES / "curtailment_rate_by_technology_2021_2035.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + curtailment_rate_by_technology_2021_2035.png")

    # ---- 5. average dispatch by hour of day (last period) ----
    hod = {t: hourly_last[t].reshape(365, 24).mean(axis=0) for t in ORDER}
    fig, ax = plt.subplots(figsize=(10, 6))
    # close the daily cycle: append hour 0 as hour 24 so the stack wraps smoothly
    hrs = np.arange(25)
    pos = np.zeros(25); neg = np.zeros(25)
    for t in ORDER:
        vd = hod[t] / 1000.0                      # GW, 24 values
        v = np.concatenate([vd, vd[:1]])          # 25 values, cyclic
        up = np.clip(v, 0, None); dn = np.clip(v, None, 0)
        ax.fill_between(hrs, pos, pos + up, color=COLOR[t], linewidth=0)
        ax.fill_between(hrs, neg, neg + dn, color=COLOR[t], linewidth=0, alpha=0.85)
        # thin separator between bands for readability
        ax.plot(hrs, pos + up, color="white", lw=0.5, alpha=0.6)
        pos += up; neg += dn
    ax.set_xlabel("Hour of day"); ax.set_ylabel("Average dispatch (GW)")
    ax.set_title(f"Average Dispatch by Hour of Day — {PERIOD_YEAR[LAST_PERIOD]}",
                 fontweight="bold", pad=12)
    ax.set_xlim(0, 24); ax.set_xticks(np.arange(0, 25, 3))
    ax.axhline(0, color="#888", lw=0.8)
    ax.legend(handles=legend_handles(), fontsize=8, loc="upper left", ncol=2, frameon=True)
    ax.grid(True, color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(RES / "dispatch_annual_avg_hourofday_2035.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + dispatch_annual_avg_hourofday_2035.png")

    # ---- 6. dispatch over representative weeks (last period) ----
    # show 4 one-week windows (mid-Jan, mid-Apr, mid-Jul, mid-Oct)
    windows = {"Winter (Jan)": 24*14, "Spring (Apr)": 24*104,
               "Summer (Jul)": 24*195, "Autumn (Oct)": 24*287}
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), sharey=True)
    for ax, (lab, start) in zip(axes.flat, windows.items()):
        sl = slice(start, start + 24*7)
        hh = np.arange(24*7) / 24.0
        pos = np.zeros(24*7); neg = np.zeros(24*7)
        for t in ORDER:
            v = hourly_last[t][sl] / 1000.0
            up = np.clip(v, 0, None); dn = np.clip(v, None, 0)
            ax.fill_between(hh, pos, pos + up, color=COLOR[t], linewidth=0)
            ax.fill_between(hh, neg, neg + dn, color=COLOR[t], linewidth=0, alpha=0.85)
            pos += up; neg += dn
        ax.set_title(lab, fontsize=11, fontweight="bold")
        ax.set_xlim(0, 7); ax.axhline(0, color="#888", lw=0.8)
        ax.set_xlabel("Day"); ax.grid(True, color="#EEEEEE", lw=0.6); ax.set_axisbelow(True)
    axes[0][0].set_ylabel("Dispatch (GW)"); axes[1][0].set_ylabel("Dispatch (GW)")
    fig.suptitle(f"Dispatch — Representative Weeks, {PERIOD_YEAR[LAST_PERIOD]}",
                 fontsize=14, fontweight="bold")
    fig.legend(handles=legend_handles(), fontsize=9, loc="lower center",
               ncol=6, frameon=True, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(RES / "dispatch_representative_days_2035.png", dpi=150,
                facecolor="white", bbox_inches="tight")
    plt.close(fig); print("  + dispatch_representative_days_2035.png")

    print("done.")


if __name__ == "__main__":
    main()
