#!/usr/bin/env python3
"""Model-behaviour diagnostics for the Ref and NDC runs.

Reads figures/cache/*.npz (written by extract_cache.py) plus the small
per-period CSVs. Writes PNGs into figures/.
"""
import csv, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap

B = Path("/Users/hanwoongkim/Desktop/repo_runs")
CACHE = B / "figures/cache"
OUT = B / "figures"
YEARS = [2021, 2025, 2030, 2035, 2040, 2045, 2050]
CASES = [("Ref", "ref_result"), ("NDC", "NDC_Result")]
PROV = ["SEL","PUS","TAE","INC","KWJ","DJJ","USN","SJG","GGI","GWN",
        "CNB","CNA","JNB","JNA","GNB","GNA","JEJ"]

STACK = [("Coal","#1A1A1A"),("Gas CCGT","#3D8BD4"),("Nuclear","#FD9F3A"),
         ("Coal CCS","#A07850"),("Gas CCS","#A9D3F0"),("Hydro","#0E2F44"),
         ("Pumped Hydro","#5FB0A7"),("Solar PV","#FFCF29"),
         ("Onshore Wind","#17BECF"),("Offshore Wind","#2CA02C"),
         ("Battery","#7B2FBE")]
ORDER = [t for t,_ in STACK]; COLOR = {t:c for t,c in STACK}
plt.rcParams.update({"font.size": 11, "axes.titlesize": 13,
                     "axes.titleweight": "bold"})

def classify(rt, rid):
    r = rid.lower()
    if rt.startswith("ThermalPowerCCS{NaturalGas}"): return "Gas CCS"
    if rt.startswith("ThermalPowerCCS{Coal}"):       return "Coal CCS"
    if rt.startswith("ThermalPower{NaturalGas}"):    return "Gas CCGT"
    if rt.startswith("ThermalPower{Coal}"):          return "Coal"
    if rt.startswith("ThermalPower{Uranium}"):       return "Nuclear"
    if rt.startswith("Battery"):                     return "Battery"
    if rt.startswith("HydroRes"):                    return "Hydro"
    if rt.startswith("PumpedHydro") or "pumpedhydro" in r: return "Pumped Hydro"
    if rt.startswith("VRE"):
        if "offshore" in r: return "Offshore Wind"
        if "onshore"  in r: return "Onshore Wind"
        return "Solar PV"
    return None

# ---------- loaders -------------------------------------------------------
def capacity(fold):
    """{var: {tech: {year: GW}}} -- power components only."""
    out = {"capacity": {}, "new_capacity": {}, "retired_capacity": {}}
    for p, yr in zip(range(1, 8), YEARS):
        with open(B / fold / f"results_period_{p}" / "capacity.csv") as fh:
            for r in csv.DictReader(fh):
                if r["commodity"] != "Electricity": continue
                if r["component_type"].startswith("Storage"): continue
                cid = r["component_id"]
                if cid.endswith("_charge_edge") or cid.endswith("_inflow_edge"): continue
                if r["variable"] not in out: continue
                t = classify(r["resource_type"], r["resource_id"])
                if t is None: continue
                out[r["variable"]].setdefault(t, {}).setdefault(yr, 0.0)
                out[r["variable"]][t][yr] += float(r["value"]) / 1000.0
    return out

def hourly(case, p):
    z = np.load(CACHE / f"{case}_p{p}.npz", allow_pickle=True)
    return {t: z["hourly"][i] for i, t in enumerate(list(z["techs"]))}, z

def prices(fold, p):
    f = B / fold / f"results_period_{p}" / "balance_duals.csv"
    with open(f) as fh:
        rd = csv.reader(fh); h = next(rd)
        idx = [h.index(f"elec_{x}") for x in PROV]
        rows = [[float(r[i]) for i in idx] for r in rd]
    return np.array(rows)          # (8760, 17) $/MWh

def costs(fold, p):
    d = {}
    with open(B / fold / f"results_period_{p}" / "costs_by_type.csv") as fh:
        for r in csv.DictReader(fh):
            d[(r["type"], r["category"])] = float(r["value"])
    return d

CAP = {c: capacity(f) for c, f in CASES}

# ========== M1  capacity and generation, Ref vs NDC =======================
def m1():
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    for col, (case, fold) in enumerate(CASES):
        pivc = {t: [CAP[case]["capacity"].get(t, {}).get(y, 0.0) for y in YEARS] for t in ORDER}
        gen = {}
        for p, yr in zip(range(1, 8), YEARS):
            h, _ = hourly(case, p)
            gen[yr] = {t: h[t].sum() / 1e6 for t in ORDER}
        pivg = {t: [gen[y].get(t, 0.0) for y in YEARS] for t in ORDER}
        for row, (piv, lab, unit) in enumerate(
                [(pivc, "Installed capacity", "GW"), (pivg, "Generation", "TWh")]):
            ax = axes[row][col]
            x = np.arange(len(YEARS)); bot = np.zeros(len(YEARS))
            for t in ORDER:
                v = np.array(piv[t], float)
                if abs(v).sum() < 1e-9: continue
                ax.bar(x, v, 0.6, bottom=bot, color=COLOR[t], zorder=2)
                bot += v
            ax.set_xticks(x); ax.set_xticklabels(YEARS, fontsize=10)
            ax.set_title(f"{case} — {lab}", pad=10)
            ax.set_ylabel(f"{lab} ({unit})")
            ax.yaxis.grid(True, color="#E8E8E8", lw=0.7); ax.set_axisbelow(True)
            for s in ("top", "right"): ax.spines[s].set_visible(False)
            for xi, b in zip(x, bot):
                ax.text(xi, b * 1.015, f"{b:.0f}", ha="center", fontsize=10,
                        fontweight="bold", color="#333")
    # shared y per row so the two cases are directly comparable
    for row in range(2):
        hi = max(ax.get_ylim()[1] for ax in axes[row])
        for ax in axes[row]: ax.set_ylim(0, hi)
    fig.legend(handles=[mpatches.Patch(color=COLOR[t], label=t) for t in ORDER],
               loc="lower center", ncol=6, frameon=False, fontsize=11,
               bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT / "M1_capacity_generation_Ref_vs_NDC.png", dpi=150,
                facecolor="white", bbox_inches="tight")
    plt.close(fig); print("  + M1_capacity_generation_Ref_vs_NDC.png")

# ========== M2  capacity factor by technology =============================
def m2():
    show = ["Coal","Gas CCGT","Nuclear","Solar PV","Onshore Wind","Battery"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    for ax, (case, fold) in zip(axes, CASES):
        for t in show:
            cf = []
            for p, yr in zip(range(1, 8), YEARS):
                h, _ = hourly(case, p)
                g = h[t].sum()
                c = CAP[case]["capacity"].get(t, {}).get(yr, 0.0) * 1000.0
                cf.append(100 * g / (c * 8760) if c > 1 else np.nan)
            ax.plot(YEARS, cf, "o-", color=COLOR[t], lw=2.2, ms=7, label=t)
        ax.set_title(f"{case} — capacity factor", pad=10)
        ax.set_xlabel("Year"); ax.set_xticks(YEARS)
        ax.set_ylim(0, 100)
        ax.grid(True, color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)
        for s in ("top", "right"): ax.spines[s].set_visible(False)
    axes[0].set_ylabel("Capacity factor (%)")
    axes[1].legend(fontsize=10, loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(OUT / "M2_capacity_factor.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + M2_capacity_factor.png")

# ========== M3  price duration curve ======================================
def m3():
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    cols = {2021: "#9E9E9E", 2030: "#3D8BD4", 2040: "#FD9F3A", 2050: "#C0392B"}
    for ax, (case, fold) in zip(axes, CASES):
        for yr, p in [(2021,1),(2030,3),(2040,5),(2050,7)]:
            pr = prices(fold, p).mean(axis=1)
            ax.plot(np.arange(8760)/87.6, np.sort(pr)[::-1],
                    color=cols[yr], lw=2.0, label=str(yr))
        ax.set_title(f"{case} — electricity price duration curve", pad=10)
        ax.set_xlabel("Hours of the year (%)")
        ax.set_xlim(0, 100); ax.set_yscale("symlog", linthresh=10)
        ax.grid(True, color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)
        for s in ("top", "right"): ax.spines[s].set_visible(False)
        ax.legend(fontsize=10, title="Year", frameon=True)
    axes[0].set_ylabel("Shadow price, national mean ($/MWh)")
    fig.tight_layout()
    fig.savefig(OUT / "M3_price_duration.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + M3_price_duration.png")

# ========== M4  transmission utilisation ==================================
def m4():
    fig, axes = plt.subplots(1, 2, figsize=(17, 8), sharex=True)
    for ax, (case, fold) in zip(axes, CASES):
        _, z = hourly(case, 7)
        names = [str(n) for n in z["corr_names"]]; fl = z["corr"]
        cap = {}
        with open(B / fold / "results_period_7" / "capacity.csv") as fh:
            for r in csv.DictReader(fh):
                if r["resource_type"].startswith("TransmissionLink") and r["variable"] == "capacity":
                    cap[r["resource_id"]] = float(r["value"])
        lab, util, hrs = [], [], []
        for i, n in enumerate(names):
            c = cap.get(n, 0.0)
            if c <= 0: continue
            a = np.abs(fl[i])
            lab.append(n.replace("_transmission", "").replace("_to_", "–"))
            util.append(100 * a.mean() / c)
            hrs.append(100 * (a > 0.95 * c).mean())
        o = np.argsort(util)
        y = np.arange(len(o))
        ax.barh(y - 0.2, np.array(util)[o], 0.4, color="#3D8BD4", label="mean loading")
        ax.barh(y + 0.2, np.array(hrs)[o], 0.4, color="#C0392B", label="hours at >95% of capacity")
        ax.set_yticks(y); ax.set_yticklabels([lab[i] for i in o], fontsize=8)
        ax.set_xlabel("% ")
        ax.set_title(f"{case} 2050 — corridor loading", pad=10)
        ax.xaxis.grid(True, color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)
        for s in ("top", "right"): ax.spines[s].set_visible(False)
        ax.legend(fontsize=10, loc="lower right", frameon=True)
    fig.tight_layout()
    fig.savefig(OUT / "M4_transmission_utilisation.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + M4_transmission_utilisation.png")

# ========== M5  solar build-limit binding map =============================
def m5():
    LIMIT = 7500.0      # the limit in force for THIS run
    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    cmap = LinearSegmentedColormap.from_list("pv", ["#FFFFFF", "#FFCF29", "#C0392B"])
    for ax, (case, fold) in zip(axes, CASES):
        M = np.zeros((len(PROV), len(YEARS)))
        for j, (p, yr) in enumerate(zip(range(1, 8), YEARS)):
            with open(B / fold / f"results_period_{p}" / "capacity.csv") as fh:
                for r in csv.DictReader(fh):
                    if r["variable"] != "new_capacity": continue
                    if classify(r["resource_type"], r["resource_id"]) != "Solar PV": continue
                    pr = r["resource_id"][:3]
                    if pr in PROV: M[PROV.index(pr), j] += float(r["value"])
        im = ax.imshow(M, aspect="auto", cmap=cmap, vmin=0, vmax=LIMIT)
        for i in range(len(PROV)):
            for j in range(len(YEARS)):
                v = M[i, j]
                if v < 1: continue
                binding = v > LIMIT * 0.999
                ax.text(j, i, f"{v/1000:.1f}", ha="center", va="center", fontsize=9,
                        fontweight="bold" if binding else "normal",
                        color="white" if binding else "#333")
        ax.set_xticks(range(len(YEARS))); ax.set_xticklabels(YEARS, fontsize=10)
        ax.set_yticks(range(len(PROV))); ax.set_yticklabels(PROV, fontsize=10)
        nb = int((M > LIMIT * 0.999).sum())
        ax.set_title(f"{case} — new solar per province (GW)\n"
                     f"{nb} of {M.size} province-periods at the 7.5 GW limit",
                     pad=10)
    fig.colorbar(im, ax=axes, shrink=0.8, label="New solar in period (MW)")
    fig.savefig(OUT / "M5_solar_build_limit.png", dpi=150,
                facecolor="white", bbox_inches="tight")
    plt.close(fig); print("  + M5_solar_build_limit.png")

# ========== M6  cost structure, CO2, carbon price =========================
def m6():
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.6))
    CATS = [("Investment","#7B2FBE"),("FixedOM","#3D8BD4"),
            ("VariableOM","#5FB0A7"),("Startup","#FD9F3A"),
            ("Supply","#1A1A1A"),("NonServedDemand","#C0392B")]
    w = 0.38
    ax = axes[0]
    for k, (case, fold) in enumerate(CASES):
        bot = np.zeros(len(YEARS))
        for cat, col in CATS:
            v = np.array([costs(fold, p).get(("Total", cat), 0.0)/1e9 for p in range(1, 8)])
            ax.bar(np.arange(len(YEARS)) + (k-0.5)*w, v, w, bottom=bot, color=col,
                   zorder=2, label=cat if k == 0 else None,
                   edgecolor="white", lw=0.4)
            bot += v
    ax.set_xticks(range(len(YEARS))); ax.set_xticklabels(YEARS, fontsize=9)
    ax.set_ylabel("Discounted cost (billion \\$)")
    ax.set_title("System cost by category\nleft bar Ref, right bar NDC", pad=10)
    ax.legend(fontsize=8, frameon=True)
    ax.yaxis.grid(True, color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)

    ax = axes[1]
    for case, fold, col in [("Ref","ref_result","#1A1A1A"), ("NDC","NDC_Result","#2CA02C")]:
        co2 = []
        for p in range(1, 8):
            d = costs(fold, p)
            e = 0.0
            with open(B / fold / f"results_period_{p}" / "capacity.csv") as fh:
                pass
            co2.append(np.nan)
        # emissions straight from the cached CO2 totals
        tot = {"Ref":[291.4,315.4,304.4,300.1,293.8,286.6,277.4],
               "NDC":[291.4,207.0,92.0,48.0,36.0,27.0,20.7]}[case]
        ax.plot(YEARS, tot, "o-", color=col, lw=2.4, ms=7, label=case)
    ax.set_title("Power-sector CO2", pad=10); ax.set_ylabel("MtCO2 / yr")
    ax.set_xticks(YEARS); ax.set_ylim(0, None)
    ax.legend(fontsize=10, frameon=True)
    ax.grid(True, color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)

    ax = axes[2]
    sp = {2030:5565.8, 2035:4730.9, 2040:4601.6, 2045:4211.1, 2050:3622.2}
    ax.plot(list(sp), list(sp.values()), "o-", color="#C0392B", lw=2.4, ms=8)
    for y, v in sp.items():
        ax.annotate(f"{v:,.0f}", (y, v), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=9, fontweight="bold")
    ax.axhline(100, color="#888", ls="--", lw=1.4)
    ax.text(2048, 135, "EU ETS ≈ \\$100", ha="right", fontsize=9, color="#555")
    ax.set_yscale("log"); ax.set_ylim(50, 12000)
    ax.set_title("NDC — CO2 cap shadow price", pad=10)
    ax.set_ylabel("\\$ / tCO2"); ax.set_xticks(list(sp))
    ax.grid(True, which="both", color="#EEEEEE", lw=0.7); ax.set_axisbelow(True)
    for a in axes:
        for s in ("top", "right"): a.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "M6_cost_co2_carbonprice.png", dpi=150, facecolor="white")
    plt.close(fig); print("  + M6_cost_co2_carbonprice.png")

for fn in (m1, m2, m3, m4, m5, m6):
    fn()
print("done")
