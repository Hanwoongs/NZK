#!/usr/bin/env python3
"""Four figures for the MACRO technical discussion. Each one carries one question."""
import csv, collections
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

B = Path("/Users/hanwoongkim/Desktop/repo_runs")
CACHE = B / "figures/cache_re"; OUT = B / "figures/meeting"
YEARS = [2021, 2025, 2030, 2035, 2040, 2045, 2050]
CASES = [("Ref", "Ref_re"), ("NDC", "NDC_Re")]
PROV = ["SEL","PUS","TAE","INC","KWJ","DJJ","USN","SJG","GGI","GWN",
        "CNB","CNA","JNB","JNA","GNB","GNA","JEJ"]
INK, MUTE, ACC, WARN = "#1C2A3A", "#6B7A8C", "#C0392B", "#D98C1F"
plt.rcParams.update({"font.size": 12, "axes.titlesize": 14, "axes.titleweight": "bold",
                     "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": MUTE, "ytick.color": MUTE})

def hourly(case, p):
    z = np.load(CACHE / f"{case}_p{p}.npz", allow_pickle=True)
    return {t: z["hourly"][i] for i, t in enumerate(list(z["techs"]))}, z

def cap_of(fold, p, rt, var="capacity"):
    s = 0.0
    for r in csv.DictReader(open(B / fold / f"results_period_{p}" / "capacity.csv")):
        if r["resource_type"] == rt and r["variable"] == var:
            s += float(r["value"])
    return s

def frame(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(MUTE)
    ax.grid(True, color="#E9ECEF", lw=0.8); ax.set_axisbelow(True)

# ============ F1  base-year calibration gap =============================
def f1():
    obs = {"Coal": 198, "Gas": 167, "Nuclear": 158, "Solar+Wind": 28, "Hydro": 6.7}
    h, _ = hourly("Ref", 1)
    mod = {"Coal": h["Coal"].sum()/1e6, "Gas": h["Gas CCGT"].sum()/1e6,
           "Nuclear": h["Nuclear"].sum()/1e6,
           "Solar+Wind": (h["Solar PV"]+h["Onshore Wind"]+h["Offshore Wind"]).sum()/1e6,
           "Hydro": h["Hydro"].sum()/1e6}
    k = list(obs); x = np.arange(len(k)); w = 0.38
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.bar(x-w/2, [mod[t] for t in k], w, color=ACC, label="Model 2021", zorder=3)
    ax.bar(x+w/2, [obs[t] for t in k], w, color=MUTE, label="Observed 2021", zorder=3)
    for xi, t in zip(x, k):
        ax.text(xi-w/2, mod[t]+6, f"{mod[t]:.0f}", ha="center", fontsize=11, fontweight="bold", color=ACC)
        ax.text(xi+w/2, obs[t]+6, f"{obs[t]:.0f}", ha="center", fontsize=11, color=MUTE)
    ax.annotate("", xy=(0.14, 232), xytext=(1.14, 232),
                arrowprops=dict(arrowstyle="<->", color=WARN, lw=2.2))
    ax.text(1.30, 232, "coal and gas\nare inverted", ha="left", va="center",
            fontsize=12.5, fontweight="bold", color=WARN)
    ax.set_xticks(x); ax.set_xticklabels(k); ax.set_ylabel("Generation (TWh)")
    ax.set_ylim(0, 300)
    ax.set_title("Base year is not yet calibrated — and this run predates the fix", pad=12)
    ax.legend(frameon=False, fontsize=12, loc="upper right"); frame(ax)
    fig.text(0.5, -0.04,
        "Cause: coal and gas carried no availability field, so both defaulted to 1.0 and coal ran at a 95% capacity factor.\n"
        "Fixes staged but NOT in this run: coal availability 0.65 · nuclear 0.85 → 0.78 · 2021 gas retirement blocked.",
        ha="center", fontsize=11, color=MUTE)
    fig.tight_layout(); fig.savefig(OUT/"F1_base_year.png", dpi=160, facecolor="white", bbox_inches="tight")
    plt.close(fig); print("  + F1_base_year.png")

# ============ F2  solar build limit — Q1 ================================
def f2():
    LIM = 6000.0
    fig, axes = plt.subplots(1, 2, figsize=(17.5, 6.6))
    cmap = LinearSegmentedColormap.from_list("pv", ["#FFFFFF", "#F6D55C", ACC])
    for ax, (case, fold) in zip(axes, CASES):
        M = np.zeros((17, 7))
        for j, p in enumerate(range(1, 8)):
            for r in csv.DictReader(open(B/fold/f"results_period_{p}"/"capacity.csv")):
                if r["variable"] != "new_capacity" or r["resource_type"] != "VRE": continue
                if "utility_pv" not in r["resource_id"]: continue
                M[PROV.index(r["resource_id"][:3]), j] += float(r["value"])
        im = ax.imshow(M, aspect="auto", cmap=cmap, vmin=0, vmax=LIM)
        for i in range(17):
            for j in range(7):
                v = M[i, j]
                if v < 1: continue
                b = v > LIM*0.999
                ax.text(j, i, f"{v/1000:.1f}", ha="center", va="center", fontsize=9.5,
                        fontweight="bold" if b else "normal", color="white" if b else INK)
        nb = int((M > LIM*0.999).sum())
        peak = M.sum(0).max()/5000
        ax.set_xticks(range(7)); ax.set_xticklabels(YEARS, fontsize=10)
        ax.set_yticks(range(17)); ax.set_yticklabels(PROV, fontsize=9.5)
        ax.set_title(f"{case}:  {nb} of 119 province-periods at the cap\n"
                     f"national build peaks at {peak:.1f} GW/yr   (target 5)", pad=10)
    fig.colorbar(im, ax=axes, shrink=0.75, label="New solar per province, per 5-year period (MW)")
    fig.suptitle("Q1  A per-province cap cannot control the national build rate",
                 fontsize=17, fontweight="bold", y=1.03)
    fig.text(0.5, -0.022,
        "What we need:  national solar build ≤ 5 GW/yr          "
        "What we can express:  6,000 MW per province per 5-year period  =  1.2 GW/yr each,  20.4 GW/yr if all 17 bind",
        ha="center", fontsize=12, fontweight="bold", color=INK)
    fig.text(0.5, -0.072,
        "Tightening it relocates the build instead of limiting the total: 7,500 → 6,000 MW moved the national peak only "
        "6.5 → 6.0 GW/yr (Ref) and 12.9 → 10.6 (NDC),\n"
        "and Ref 2050 solar rose 139 → 142 GW. Red cells are at the cap; the provinces beside them still have headroom to absorb it.",
        ha="center", fontsize=11, color=MUTE)
    fig.savefig(OUT/"F2_solar_cap.png", dpi=160, facecolor="white", bbox_inches="tight")
    plt.close(fig); print("  + F2_solar_cap.png")

# ============ F3  nuclear rigidity -> CO2 price — Q3 ====================
def f3():
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.4))
    # (a) capacity factors
    ax = axes[0]
    for case, fold, ls in [("Ref","Ref_re","--"), ("NDC","NDC_Re","-")]:
        cf = []
        for p in range(1, 8):
            h, _ = hourly(case, p)
            c = cap_of(fold, p, "ThermalPower{Uranium}")
            cf.append(100*h["Nuclear"].sum()/(c*8760))
        ax.plot(YEARS, cf, ls, color=WARN, lw=2.6, ms=8, marker="o", label=f"Nuclear, {case}")
    for case, fold, ls in [("Ref","Ref_re","--"), ("NDC","NDC_Re","-")]:
        cf = []
        for p in range(1, 8):
            h, _ = hourly(case, p)
            c = cap_of(fold, p, "ThermalPower{Coal}")
            cf.append(100*h["Coal"].sum()/(c*8760))
        ax.plot(YEARS, cf, ls, color=INK, lw=2.0, ms=6, marker="s", label=f"Coal, {case}")
    ax.annotate("exactly 85% in all\nseven periods", (2037, 85), xytext=(2030, 62),
                fontsize=11, fontweight="bold", color=WARN,
                arrowprops=dict(arrowstyle="->", color=WARN, lw=1.6))
    ax.set_ylim(0, 105); ax.set_xticks(YEARS); ax.set_ylabel("Capacity factor (%)")
    ax.set_title("Nuclear cannot move", pad=10)
    ax.legend(fontsize=10, frameon=False, loc="lower left"); frame(ax)
    ax.tick_params(axis="x", labelsize=9)
    # (b) CO2 shadow price
    ax = axes[1]
    sp = {}
    for p, y in zip(range(2, 8), YEARS[1:]):
        f = B/"NDC_Re"/f"results_period_{p}"/"co2_cap_duals.csv"
        if f.exists():
            rows = list(csv.DictReader(open(f)))
            if rows: sp[y] = float(rows[0]["CO2_Shadow_Price"])
    ax.plot(list(sp), list(sp.values()), "o-", color=ACC, lw=2.6, ms=9)
    for y, v in sp.items():
        ax.annotate(f"{v:,.0f}", (y, v), textcoords="offset points", xytext=(0, 13),
                    ha="center", fontsize=10.5, fontweight="bold", color=ACC)
    ax.axhline(100, color=MUTE, ls="--", lw=1.5)
    ax.text(2049, 125, "EU ETS ≈ $100", ha="right", fontsize=10.5, color=MUTE)
    ax.set_yscale("log"); ax.set_ylim(60, 30000); ax.set_xticks(list(sp))
    ax.set_ylabel("$ / tCO₂"); ax.set_title("NDC carbon shadow price", pad=10)
    frame(ax); ax.tick_params(axis="x", labelsize=9)
    # (c) curtailment
    ax = axes[2]
    for case, fold, col in [("Ref","Ref_re",MUTE), ("NDC","NDC_Re",ACC)]:
        cur = []
        for p in range(1, 8):
            s = 0.0
            with open(B/fold/f"results_period_{p}"/"curtailment.csv") as fh:
                rd = csv.reader(fh); next(rd)
                for row in rd:
                    try: s += float(row[-1])
                    except ValueError: pass
            cur.append(s/1e6)
        ax.plot(YEARS, cur, "o-", color=col, lw=2.6, ms=8, label=case)
    ax.set_ylabel("VRE curtailment (TWh)"); ax.set_xticks(YEARS)
    ax.set_title("Curtailment has nowhere to go", pad=10)
    ax.legend(fontsize=11, frameon=False); frame(ax); ax.tick_params(axis="x", labelsize=9)
    fig.suptitle("Q3  Nuclear is pinned by MustRun + flat 0.85 availability, and the carbon price absorbs it",
                 fontsize=16, fontweight="bold", y=1.03)
    fig.text(0.5, -0.05,
        "Nuclear is 468 TWh of completely inflexible output in NDC 2050. With no long-duration storage, hydrogen, demand response or BECCS,\n"
        "and CCS capped by 4.75 Mt/yr of CO₂ storage, the cap can only be met by curtailing solar — so the dual rises to tens of times any real carbon price.",
        ha="center", fontsize=11, color=MUTE)
    fig.tight_layout(); fig.savefig(OUT/"F3_nuclear_co2.png", dpi=160, facecolor="white", bbox_inches="tight")
    plt.close(fig); print("  + F3_nuclear_co2.png")

# ============ F4  transmission formulation — Q4 =========================
def f4():
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8))
    ax = axes[0]
    for case, fold, col in [("Ref","Ref_re",MUTE), ("NDC","NDC_Re",ACC)]:
        _, z = hourly(case, 7)
        names = [str(n) for n in z["corr_names"]]
        cap = {r["resource_id"]: float(r["value"])
               for r in csv.DictReader(open(B/fold/"results_period_7"/"capacity.csv"))
               if r["resource_type"].startswith("TransmissionLink") and r["variable"]=="capacity"}
        for i, n in enumerate(names):
            c = cap.get(n, 0)
            if c <= 0: continue
            ax.plot(np.arange(8760)/87.6, np.sort(100*np.abs(z["corr"][i])/c)[::-1],
                    color=col, lw=0.9, alpha=0.5)
        ax.plot([], [], color=col, lw=2, label=case)
    ax.axhline(100, color=INK, ls="--", lw=1.3)
    ax.set_xlim(0, 100); ax.set_ylim(0, 108)
    ax.set_xlabel("Percentage of the 8,760 hours"); ax.set_ylabel("|flow| / capacity (%)")
    ax.set_title("2050 corridor loading — healthy after the fix", pad=10)
    ax.legend(fontsize=11, frameon=False); frame(ax)
    ax = axes[1]; ax.axis("off")
    ax.text(0.0, 0.97, "What the signed BidirectionalEdge did", fontsize=13.5,
            fontweight="bold", color=INK, va="top")
    rows = [("variable_om_cost", "1 $/MWh on every corridor"),
            ("flow variable", "signed, so reverse flow earned revenue"),
            ("NDC 2021 transmission VOM", "−$2,132 M  (−1.8% of system cost)"),
            ("corridors pinned >95% of hours", "9 of 32   →   0 of 32 after setting it to 0"),
            ("total |flow|", "645 TWh  →  345 TWh")]
    for i, (a, b) in enumerate(rows):
        y = 0.80 - i*0.115
        ax.text(0.0, y, a, fontsize=11.5, color=MUTE)
        ax.text(0.52, y, b, fontsize=11.5, fontweight="bold", color=INK)
    ax.text(0.0, 0.17,
        "Resolved by setting variable_om_cost = 0, but the formulation question stands:\n"
        "the ITLs were derived under loop-flow physics, then used in a transport model\n"
        "that discards impedance, DC power flow and N-1 entirely.",
        fontsize=11.5, color=ACC, va="top")
    fig.suptitle("Q4  Transmission is a transport model with signed bidirectional edges",
                 fontsize=16, fontweight="bold", y=1.02)
    fig.tight_layout(); fig.savefig(OUT/"F4_transmission.png", dpi=160, facecolor="white", bbox_inches="tight")
    plt.close(fig); print("  + F4_transmission.png")

for fn in (f1, f2, f3, f4): fn()
print("done")
