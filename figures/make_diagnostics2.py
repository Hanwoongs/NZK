#!/usr/bin/env python3
"""Revisions to M2/M3/M4 plus M7, the transmission-saturation diagnostic."""
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

B = Path("/Users/hanwoongkim/Desktop/repo_runs")
CACHE = B / "figures/cache"; OUT = B / "figures"
YEARS = [2021, 2025, 2030, 2035, 2040, 2045, 2050]
CASES = [("Ref", "ref_result"), ("NDC", "NDC_Result")]
PROV = ["SEL","PUS","TAE","INC","KWJ","DJJ","USN","SJG","GGI","GWN",
        "CNB","CNA","JNB","JNA","GNB","GNA","JEJ"]
COLOR = {"Coal":"#1A1A1A","Gas CCGT":"#3D8BD4","Nuclear":"#FD9F3A",
         "Solar PV":"#FFCF29","Onshore Wind":"#17BECF","Battery":"#7B2FBE"}
plt.rcParams.update({"font.size": 11, "axes.titlesize": 13, "axes.titleweight":"bold"})

def classify(rt, rid):
    r = rid.lower()
    if rt.startswith("ThermalPowerCCS{NaturalGas}"): return "Gas CCS"
    if rt.startswith("ThermalPowerCCS{Coal}"):       return "Coal CCS"
    if rt.startswith("ThermalPower{NaturalGas}"):    return "Gas CCGT"
    if rt.startswith("ThermalPower{Coal}"):          return "Coal"
    if rt.startswith("ThermalPower{Uranium}"):       return "Nuclear"
    if rt.startswith("Battery"):                     return "Battery"
    if rt.startswith("HydroRes"):                    return "Hydro"
    if rt.startswith("VRE"):
        if "offshore" in r: return "Offshore Wind"
        if "onshore"  in r: return "Onshore Wind"
        return "Solar PV"
    return None

def hourly(case, p):
    z = np.load(CACHE / f"{case}_p{p}.npz", allow_pickle=True)
    return {t: z["hourly"][i] for i, t in enumerate(list(z["techs"]))}, z

def capGW(fold, p, tech):
    s = 0.0
    with open(B / fold / f"results_period_{p}" / "capacity.csv") as fh:
        for r in csv.DictReader(fh):
            if r["commodity"] != "Electricity" or r["variable"] != "capacity": continue
            if r["component_type"].startswith("Storage"): continue
            cid = r["component_id"]
            if cid.endswith("_charge_edge") or cid.endswith("_inflow_edge"): continue
            if classify(r["resource_type"], r["resource_id"]) == tech:
                s += float(r["value"])
    return s / 1000.0

def tcap(fold, p):
    d = {}
    with open(B / fold / f"results_period_{p}" / "capacity.csv") as fh:
        for r in csv.DictReader(fh):
            if r["resource_type"].startswith("TransmissionLink") and r["variable"] == "capacity":
                d[r["resource_id"]] = float(r["value"])
    return d

# ---- M2 revised: drop Battery (net CF is ~0 by construction) -------------
def m2():
    show = ["Coal","Gas CCGT","Nuclear","Solar PV","Onshore Wind"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    for ax, (case, fold) in zip(axes, CASES):
        for t in show:
            cf = []
            for p, yr in zip(range(1, 8), YEARS):
                h, _ = hourly(case, p)
                c = capGW(fold, p, t) * 1000.0
                cf.append(100 * h[t].sum() / (c * 8760) if c > 1 else np.nan)
            ax.plot(YEARS, cf, "o-", color=COLOR[t], lw=2.4, ms=7, label=t)
            ax.annotate(f"{cf[-1]:.0f}%", (YEARS[-1], cf[-1]), fontsize=10,
                        fontweight="bold", color=COLOR[t],
                        textcoords="offset points", xytext=(8, 0), va="center")
        ax.set_title(f"{case} — capacity factor", pad=10)
        ax.set_xlabel("Year"); ax.set_xticks(YEARS); ax.set_ylim(0, 105)
        ax.set_xlim(2019, 2054)
        ax.grid(True, color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)
        for s in ("top","right"): ax.spines[s].set_visible(False)
    axes[0].set_ylabel("Capacity factor (%)")
    axes[0].legend(fontsize=10, loc="center left", frameon=True)
    fig.text(0.5, -0.02, "Battery omitted: its net flow is charge minus discharge, "
             "so a net capacity factor is near zero by construction.",
             ha="center", fontsize=9.5, color="#555")
    fig.tight_layout()
    fig.savefig(OUT / "M2_capacity_factor.png", dpi=150, facecolor="white",
                bbox_inches="tight")
    plt.close(fig); print("  + M2_capacity_factor.png (revised)")

# ---- M3 revised: log axis without the wasted negative half ---------------
def m3():
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    cols = {2021:"#9E9E9E", 2030:"#3D8BD4", 2040:"#FD9F3A", 2050:"#C0392B"}
    for ax, (case, fold) in zip(axes, CASES):
        for yr, p in [(2021,1),(2030,3),(2040,5),(2050,7)]:
            with open(B / fold / f"results_period_{p}" / "balance_duals.csv") as fh:
                rd = csv.reader(fh); h = next(rd)
                idx = [h.index(f"elec_{x}") for x in PROV]
                pr = np.array([np.mean([float(r[i]) for i in idx]) for r in rd])
            s = np.sort(np.clip(pr, 0.2, None))[::-1]
            ax.plot(np.arange(8760)/87.6, s, color=cols[yr], lw=2.2, label=str(yr))
            if yr == 2050:
                below = 100*(pr < 5).mean()
                ax.annotate(f"{below:.0f}% of hours\nbelow \\$5/MWh",
                            (min(99, 100-below/2), 1.0), fontsize=10, ha="center",
                            color="#C0392B", fontweight="bold")
        ax.set_yscale("log"); ax.set_ylim(0.2, 2000); ax.set_xlim(0, 100)
        ax.set_title(f"{case} — electricity price duration curve", pad=10)
        ax.set_xlabel("Percentage of the 8,760 hours")
        ax.grid(True, which="both", color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)
        for s_ in ("top","right"): ax.spines[s_].set_visible(False)
        ax.legend(fontsize=10, title="Year", frameon=True, loc="lower left")
    axes[0].set_ylabel("Shadow price, 17-province mean (\\$/MWh)")
    fig.tight_layout()
    fig.savefig(OUT / "M3_price_duration.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + M3_price_duration.png (revised)")

# ---- M4 revised: loading duration curves, saturation made visible --------
def m4():
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), sharey=True)
    for ax, (case, fold) in zip(axes, CASES):
        _, z = hourly(case, 7)
        names = [str(n) for n in z["corr_names"]]; fl = z["corr"]
        cap = tcap(fold, 7)
        npin = 0
        for i, n in enumerate(names):
            c = cap.get(n, 0.0)
            if c <= 0: continue
            u = np.sort(100 * np.abs(fl[i]) / c)[::-1]
            pin = (np.abs(fl[i]) > 0.999*c).mean()
            if pin > 0.5: npin += 1
            ax.plot(np.arange(8760)/87.6, u,
                    color="#C0392B" if pin > 0.5 else "#8FA8BC",
                    lw=1.6 if pin > 0.5 else 0.9,
                    alpha=0.95 if pin > 0.5 else 0.6, zorder=3 if pin > 0.5 else 2)
        ax.axhline(100, color="#222", ls="--", lw=1.2, zorder=4)
        ax.set_title(f"{case} 2050 — corridor loading duration\n"
                     f"{npin} of 32 corridors sit at their limit for more than half the year",
                     pad=10)
        ax.set_xlabel("Percentage of the 8,760 hours")
        ax.set_xlim(0, 100); ax.set_ylim(0, 110)
        ax.grid(True, color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)
        for s in ("top","right"): ax.spines[s].set_visible(False)
    axes[0].set_ylabel("Corridor loading, |flow| / capacity (%)")
    axes[0].plot([], [], color="#C0392B", lw=2, label="saturated > 50% of hours")
    axes[0].plot([], [], color="#8FA8BC", lw=1.2, label="other corridors")
    axes[0].legend(fontsize=10, loc="lower left", frameon=True)
    fig.text(0.5, -0.03,
             "Flat lines at 100% are not a dispatch result. `variable_om_cost = 1 $/MWh` on a signed "
             "BidirectionalEdge pays the model to transmit\nin the negative direction, so corridors are "
             "held hard against their limit all year. Corrected to 0 for the next run.",
             ha="center", fontsize=10, color="#C0392B")
    fig.tight_layout()
    fig.savefig(OUT / "M4_transmission_saturation.png", dpi=150,
                facecolor="white", bbox_inches="tight")
    plt.close(fig); print("  + M4_transmission_saturation.png (revised)")

# ---- M7 the smoking gun: one corridor, one January week ------------------
def m7():
    fig, axes = plt.subplots(2, 1, figsize=(15, 8.5), sharex=True)
    _, z = hourly("Ref", 7)
    names = [str(n) for n in z["corr_names"]]; cap = tcap("ref_result", 7)
    pick = ["CNB_to_DJJ_transmission", "CNB_to_GNB_transmission",
            "SEL_to_INC_transmission", "GNB_to_USN_transmission"]
    sl = slice(24*14, 24*21); hh = np.arange(24*7)/24.0
    for ax, grp, title in [
        (axes[0], pick[:3], "Saturated corridors — flow pinned at the capacity limit"),
        (axes[1], pick[3:], "A corridor that dispatches normally, for comparison")]:
        for n in grp:
            i = names.index(n); c = cap[n]
            lab = n.replace("_transmission","").replace("_to_","–")
            l, = ax.plot(hh, z["corr"][i][sl]/1000, lw=2.0, label=f"{lab}  (cap {c/1000:.1f} GW)")
            ax.axhline(-c/1000, color=l.get_color(), ls=":", lw=1.1, alpha=0.7)
            ax.axhline( c/1000, color=l.get_color(), ls=":", lw=1.1, alpha=0.7)
        ax.set_title(title, pad=8, fontsize=12)
        ax.set_ylabel("Flow (GW)")
        ax.grid(True, color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)
        ax.axhline(0, color="#888", lw=0.8)
        ax.legend(fontsize=10, ncol=3, frameon=True, loc="upper right")
        for s in ("top","right"): ax.spines[s].set_visible(False)
    axes[1].set_xlabel("Day of a January week, 2050 (dotted lines are ± corridor capacity)")
    axes[1].set_xlim(0, 7)
    fig.suptitle("Ref 2050 — why the transmission results from this run cannot be used",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "M7_corridor_trace.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + M7_corridor_trace.png")

for fn in (m2, m3, m4, m7): fn()
import os
old = OUT / "M4_transmission_utilisation.png"
if old.exists(): os.remove(old); print("  - removed superseded M4_transmission_utilisation.png")
print("done")
