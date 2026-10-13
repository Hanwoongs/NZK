# Net Zero Korea — Power Sector Model (MACRO-Korea)

Provincial capacity expansion and dispatch model for South Korea's power
sector, built on MacroEnergy.jl.

Last updated **2026-10-12**. This file supersedes the per-case
`README1.md` and `README2_update.txt`, which contain several statements
that are no longer true (noted in §9).

---

## 1. Cases

Two cases are maintained. They share identical `assets/`; only the
scenario definition in `system/nodes_<year>.json` differs.

| folder | demand | domestic CO2 cap | delivered fuel prices | 2050 demand |
|---|---|---|---|---|
| `Ref` | BAU (`demand_ref.csv`) | off | BAU | 669.5 TWh |
| `NDC` | Net-Zero (`demand_NDC.csv`) | on, 2025 onward | 2°C | 742.3 TWh |

Demand, fuel prices and the CO2 budget all come from GCAM; see
`<case>/input.xlsx`. The CO2 cap trajectory is 207 / 92 / 48 / 36 / 27 /
20.7 Mt for 2025–2050.

Run with `sbatch run_NZK_della.slurm` (Della, Gurobi 13.0.2 +
Julia 1.12.1, 24 cores / 128 GB / 24 h).

---

## 2. Resolution

### Spatial — 17 provinces

| | | | | | |
|---|---|---|---|---|---|
| SEL Seoul | INC Incheon | GGI Gyeonggi | GWN Gangwon | CNA Chungnam | CNB Chungbuk |
| SJG Sejong | DJJ Daejeon | JNB Jeonbuk | JNA Jeonnam | KWJ Gwangju | GNB Gyeongbuk |
| GNA Gyeongnam | PUS Busan | TAE Daegu | USN Ulsan | JEJ Jeju | |

### Temporal

| | |
|---|---|
| Horizon | 2021 → 2050, **7 periods** at 5-year steps |
| Hours per modelled year | **8,760, chronological** (one subperiod, not representative days) |
| Timestep | 1 hour |
| Solution | Myopic; capacity carried forward between periods |
| Discount rate | 4.5% |

### Technology

17 assets per technology (one per province) for coal, coal CCS, gas CCGT,
gas CCS, nuclear, battery; 51 VRE assets (solar + onshore + offshore
wind); 8 hydro reservoir; 7 pumped hydro; 1 national CO2 injection;
32 transmission corridors.

Commodities declared: Electricity, NaturalGas, Coal, Uranium, CO2,
CO2Captured, Steam, Hydrogen. Only the electricity chain is active.

### Operational constraints

**Unit commitment is present and linearly relaxed** (not absent — see
§9). Commitment variables are continuous, which is why the solve is an LP
and shadow prices exist.

All five thermal technologies now carry the same constraint set,
harmonised 2026-10-12 (§7.1). Every constraint is stated explicitly in the
asset CSVs rather than relying on MacroEnergy's implicit defaults.

| | `uc` | MinUpTime | MinDownTime | MinFlow | Ramping | MustRun |
|---|---|---|---|---|---|---|
| Coal | ✓ | ✓ 6 h | ✓ 6 h | ✓ 0.40 | ✓ 25%/h | — |
| Coal CCS | ✓ | ✓ 4 h | ✓ 4 h | ✓ 0.50 | ✓ 100%/h | — |
| Gas CCGT | ✓ | ✓ 4 h | ✓ 2 h | ✓ 0.30 | ✓ 64%/h | — |
| Gas CCS | ✓ | ✓ 4 h | ✓ 4 h | ✓ 0.50 | ✓ 100%/h | — |
| Nuclear | ✓ | ✓ 36 h | ✓ 36 h | ✓ 0.40 | ✓ 25%/h | ✓ |
| Hydro | — | — | — | — | ✓ 8.3%/h | ✓ (+ min storage 30%) |

Startup costs are also applied: coal \$150/MW-start, gas CCGT \$69.34,
CCS \$97, nuclear \$0.

Per the MacroEnergy documentation, `BalanceConstraint`,
`CapacityConstraint` and `RampingLimitConstraint` are always active on a
ThermalPower asset; `uc: true` additionally activates `MinUpTime` and
`MinDownTime`; `MinFlowConstraint` is optional and applies **only when
declared**. All of them are declared here so the behaviour does not depend
on which defaults a given MacroEnergy version applies.

Storage: battery 2–10 h duration, 0.95 charge / 0.95 discharge
(90.25% round trip), no self-discharge. Pumped hydro 6–10 h, 88%.

Not modelled: planning reserve margin, operating reserve, inertia or
frequency constraints, minimum synchronous units.

---

## 3. Techno-economic inputs

### Capital and O&M costs — BNEF Korea, Mid scenario

Source: `20251205 BNEF Korea data .xlsx`, "South Korea" rows, **Mid**
scenario, converted from 2024\$ to **2021\$** with a deflator of **0.870**.
Verified: the ratio model ÷ BNEF-Mid is exactly 0.870 for every
technology in every period 2025–2050.

Capital cost, \$/kW (2021\$):

| | 2021 | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|---|
| Solar PV | 884 | 876 | 610 | 516 | 461 | 417 | **380** |
| Onshore wind | 1,988 | 1,969 | 1,605 | 1,505 | 1,468 | 1,440 | 1,408 |
| Offshore wind | 4,842 | 4,798 | 4,562 | 4,025 | 3,896 | 3,889 | 3,887 |
| Nuclear | 2,886 | 2,886 | 2,834 | 2,781 | 2,729 | 2,677 | 2,625 |
| Coal | 1,165 | 1,165 | 1,165 | 1,165 | 1,165 | 1,165 | 1,165 |
| Gas CCGT | 696 | 696 | 696 | 696 | 696 | 696 | 696 |

Two features of the BNEF projection drive most of the results: **solar
falls 57% while BNEF holds coal and gas flat from 2025**, and the steepest
single step is **2025→2030 (−30%)**. Solar crosses below coal on an LCOE
basis around 2030.

Note: 2021 values do **not** follow the 0.870 deflator (ratios 0.61–0.84)
and appear to come from a different source. This does not affect results
because 2021 is the calibrated base year with `can_expand = FALSE`.

Units are **\$/MW** throughout (and \$/MWh for storage energy), not ₩.

### Units and currency conventions

MacroEnergy is **energy-unit based throughout — MWh, never MMBtu**:

| field | unit |
|---|---|
| `investment_cost` | \$/MW (\$/MWh for storage energy) |
| `fixed_om_cost` | \$/MW-yr |
| `variable_om_cost` | \$/MWh |
| fuel node `price` | \$/MWh **of fuel** |
| `fuel_consumption` | MWh_fuel / MWh_elec (inverse of efficiency) |
| `emission_rate` | tCO2 / MWh_fuel |
| capacities, demand | MW |

Verified: implied efficiencies are 48.3% for gas CCGT and 32.6% for
nuclear, and emission rates are 0.3405 and 0.1810 tCO2/MWh_thermal for
coal and gas, both matching published values on a thermal-energy basis.
The realised fuel/electricity flow ratio in the solved results equals
`fuel_consumption` exactly.

All monetary values are **2021 US dollars**.

### GCAM fuel price conversion

GCAM reports delivered fuel prices in **1975\$/GJ** (`<case>/input.xlsx`).
The model nodes carry **2021\$/MWh**:

```
model $/MWh  =  GCAM 1975$/GJ  ×  3.6  ×  5.0400
                                  ↑        ↑
                              GJ→MWh    1975$ → 2021$
```

Verified across all 21 values (3 fuels × 7 periods): the implied factor is
5.0400 to four decimals in every case.

**5.04 is the US CPI-U ratio** (53.8 → 271.0). The GCAM community more
commonly uses the GDP implicit price deflator, which would give 4.31 and
fuel prices about 14% lower. CPI was retained because it is the more
conservative choice here: higher fuel prices work against fossil
generation, and switching to the GDP deflator would widen the gap between
solar and coal rather than narrow it.

Resulting 2050 prices: gas \$11.15/MMBtu, coal \$4.62, uranium \$1.53
(equivalent), against Korean import prices of roughly \$10–14, \$2–4 and
\$0.7–1.0 respectively.

### Renewable potential

Per-province `max_capacity` from the **신재생에너지 백서 technical
potential**: solar 252.9 GW, onshore wind 79.9 GW, offshore wind 91.0 GW
nationally.

Technical potential screens land use (forest, rivers, elevation) and
applies technology characteristics, but **excludes economics, permitting,
setback rules and social acceptance**. It is an upper bound on what is
physically buildable, not a deployment forecast — see §8.

### CO2 storage

`CO2StorageConstraint` on `co2_storage_offshore_KR` = **4,753,600 tCO2/yr**,
the same value in every period. Derived from a Korean offshore storage
potential assessment.

### CO2 injection cost (corrected 2026-09-20)

Previous values were roughly 1,000× too high. Corrected against Korean
and international literature:

| | before | after |
|---|---|---|
| `investment_cost` | 100,000 | **300** \$/t capacity |
| `fixed_om_cost` | — | **30** \$/t-yr |
| `variable_om_cost` | 50,000 | **27.5** \$/tCO2 |

The correction changed the outcome by almost nothing (see §8).

---

## 4. Transmission

**Current model input: 99.1 GW across 32 bidirectional corridors**, set in
`assets/assets_2021/transmission_v2_2021.csv`. Later periods inherit by
carry-forward, but **cost and loss parameters are set in every period's
file** and must be kept consistent.

### How the capacity was derived

| step | metro import | total | × national peak |
|---|---|---|---|
| 0. Sum of line thermal ratings | — | 418.4 GW | 4.6 |
| 1. Interface Transfer Limits (NREL) | 37.0 GW | 171.1 GW | 1.89 |
| 2. + injection caps | 24.2 GW | 109.5 GW | 1.21 |
| 3. + metro calibration to KPX | **13.8 GW** | **99.1 GW** | **1.10** |
| *published reality* | *12.0–13.8* | — | — |

**Step 1** — Brown et al. (NREL), *A general method for estimating zonal
transmission interface limits from nodal network data*, arXiv:2308.03612
(2023), re-implemented as a PTDF linear program and validated on the
paper's 5-bus case. Applied to the GIST public-data reconstruction of the
Korean grid (2,251 buses, 6,535 AC branches). Per corridor:
`min(n-1 A→B, n-1 B→A) + HVDC`, with HVDC added undiminished.

**Step 2** — the NREL formulation leaves bus injections uncapped, so it
measures the network's abstract capability rather than what the fleet can
deliver. Capped at installed generation (101.8 GW) and connected load
(77.1 GW) from the same GIST dataset.

**Step 3** — the 31 interface limits are each solved with the rest of the
network free to redispatch, so they are not simultaneously achievable,
while a transport model loads all of them at once. Korea also plans these
corridors to N-2 while the ITL uses a simplified N-1. Calibrated against
**KPX, 2024년도 전력계통 운영실적**: the metro (SEL+INC+GGI) transfer
limit ran 12,000 MW in January to **13,800 MW in August** and was exceeded
once in 2024 (11 June, 10:00). The August peak-month value is used. An AC
factor of **0.509** is applied to the three metro-boundary corridors only;
metro-internal corridors, all non-metro corridors and all HVDC are
unchanged.

Cross-check: the model's metro demand share is 40.8% against KPX's
published 41.1%, so the demand side was already consistent.

### Investment cost — distance-scaled

**5,200 \$/MW/km**, giving 87,120 \$/MW (17 km) to 907,573 \$/MW (175 km).
Calibrated to preserve the previous flat value of 443,638 \$/MW at the
mean 85.3 km corridor.

The flat 443,638 \$/MW had no documented source anywhere in the repo.
Reverse-engineering it against Korean construction costs: 345 kV
**underground** cable runs 15–30 billion ₩/km, which for a ~2 GW corridor
is 5,769–11,538 \$/MW/km — the model value sits at the low end of that
band. Overhead line (3–4 billion ₩/km) would imply 1,154–1,538 \$/MW/km.
Given Korea's siting constraints and the shift toward buried lines, the
underground-consistent figure is retained. **This remains an inferred
provenance, not a cited one.**

### Loss fraction — MacroEnergy default restored

`loss_fraction = max(0.001, 0.00003 × distance_km)`, reverse-engineered
from the MacroEnergy example file, where losses were already correctly
distance-scaled. Gives 0.0010–0.0052 (0.3% per 100 km).

This replaces a flat **0.03 on every corridor**, which had no source and
which — expressed per km — implied 17.9%/100 km on the shortest corridor
and 1.7%/100 km on the longest, i.e. loss *inversely* proportional to
distance.

---

## 5. 2021 base year

Existing capacity from EPSIS / KHNP / KEPCO plant-level data
(`province level_power (3).xlsx`). Corrections applied 2026-08-27:

- Gas CCGT: Sejong ↔ Gyeonggi values were swapped (848 / 11,689 MW)
- Nuclear: Daejeon ↔ Ulsan swapped (Saeul units are in Ulsan, 2,800 MW)
- Coal: Jeonnam 1,168.6 → 668.6 MW
- Solar and onshore wind re-allocated by province from the plant-level
  reference (national totals 18,200 and 1,560 MW)

Verified consistent and unchanged: pumped hydro (7 plants, 4,700 MW),
offshore wind (124.5 MW in JNB/JNA/JEJ).

### Provincial VRE capacity factors

ERA5 hourly, 2021, KST, per province, from `Post-processing files/
2021_Provincial_CF/`. 51 columns added to `system/availability.csv`.
Solar CF averages about 13–14%.

Gyeongbuk/Daegu is split into GNB and TAE with identical CF. Inland
provinces are assigned CF = 0 for offshore wind.

---

## 6. Siting restrictions

`can_expand = FALSE` for **every technology in Seoul (SEL)** and TRUE for
the other 16 provinces, reflecting land-use and siting constraints. This
is deliberate; do not "fix" it.

2021 is the calibration base year, so `can_expand = FALSE` there for all
provinces.

---

## 7. Changes made 2026-10-12

### 7.1 Unit commitment harmonised across all thermal technologies

Before this change the five thermal technologies were configured
inconsistently, in two ways that mattered:

- **`coalpowerCCS` had `uc = FALSE`** for 2035–2050 while every other
  thermal asset had `TRUE`. Coal CCS could therefore cycle freely with no
  startup cost and no minimum run time, which flattered its economics.
- **`MinFlowConstraint` was declared only for coal and gas CCGT.** It is
  an optional constraint in MacroEnergy, so nuclear (`min_flow_fraction`
  0.40) and both CCS technologies (0.50) carried the parameter but never
  had it enforced.

Applied to **52 files** (Ref and NDC × 7 periods × the affected
technologies): `uc` set to TRUE everywhere, and `MinUpTimeConstraint`,
`MinDownTimeConstraint`, `MinFlowConstraint` and `RampingLimitConstraint`
declared explicitly wherever the corresponding parameter was already
populated. No parameter values were changed — only which constraints are
switched on. Resulting configuration is in §2.

Checked before applying: nuclear carries `MustRunConstraint` and its
availability profile is constant at 0.85 with zero hourly variation, so
adding a 25%/h ramp limit cannot conflict with it.

Backups in `_backup_uc/{Ref,NDC}/assets_<year>/`.

Expected effect: small. Nuclear is already pinned by MustRun at a constant
availability, so its new MinFlow and ramp limits are unlikely to bind. CCS
does not currently deploy at all, so its constraints only matter if a
future input change makes it economic. The point of the change is that the
model is now internally consistent and the configuration no longer depends
on undeclared defaults.

### 7.2 Case settings cleaned

`settings/case_settings.json` carried a `Not_usingMyopicSettings` block
containing `StopAfterPeriod: 4` and a restart pointing at `results_009`.
The key prefix meant it was never read, but removing the prefix would have
silently truncated a run at period 4. Replaced with an explicit minimal
file: 7 period lengths, discount rate, Myopic, and `Restart.enabled:
false`. `StopAfterPeriod` is omitted so the default (unlimited) applies
and all 7 periods run.

Backups in `_backup_settings/`.

### 7.3 File hygiene

- **Stale demand files removed.** Each case folder carried a copy of the
  *other* case's demand file, and those copies were outdated (2050 at
  618.3 / 629.4 TWh, flat after 2035, versus the live 669.5 / 742.3).
  Each case now keeps only the file it actually references. Backups in
  `_removed_stale_demand/`. Also removed: `demand_backup.csv`,
  `demand_fulldecimal.csv`, `demand_downsized.csv` (unreferenced).
  `demand.csv` was kept — the demand pipeline scripts use it.
- **Stale transmission file renamed** to
  `transmission_v2_2021_OLD_sum_of_ratings_418GW.csv`. It previously
  carried the same filename as the model input, making an accidental
  2.4× over-capacity copy easy.
- Transmission backups in `_backup_transmission_171GW/`.

### The free-fuel bug (historical, resolved)

Runs before 2026-09-19 silently priced **all fuel at zero**. The fuel
price node schema changed from `{"id": ..., "price": ...}` to
`{"id": ..., "supply": {"segment1": {"price": ...}}}`; older node files
used the old key, which the newer code did not read. No error or warning
was emitted — the logs of an affected run and a correct run are
byte-identical apart from timestamps.

Affected and **invalid**: any result produced on 2026-09-11 or 2026-09-15
(`Ref_results`, `NDC_results`, `NDC_case1_results`). Diagnostic: in
`costs_by_type.csv`, `Node{Coal} / Node{NaturalGas} / Node{Uranium}`
`Supply` = 0.

This is why an older Ref run showed solar frozen at 18.2 GW and all demand
growth met by gas: with free fuel, existing thermal beats new solar.

---

### 7.4 Coal efficiency corrected to Korean values (2026-10-13)

`transforms--fuel_consumption` for coal was 3.825 MWh_fuel/MWh_e, i.e.
**26.1% net efficiency** and an emission factor of 1.3024 tCO2/MWh. Both
are far from Korea's actual fleet. The value did not come from
MacroEnergy: a full search of the package's test and documentation assets
confirms there is **no coal example** — `Coal` appears only in the
commodity list, and `coal_power.json` is mentioned in the docs but never
shipped. Gas, gas CCS and nuclear do match the MacroEnergy examples to
several decimals and were left alone.

Korean reference points:

| | efficiency | tCO2/MWh |
|---|---|---|
| reported Korean coal emission factor, 991 g/kWh | 34.4% | 0.991 |
| **applied (fleet average)** | **38.0%** | **0.896** |
| 1,000 MW USC design | 41.4–44.1% | 0.77–0.82 |

38% is used as a fleet average: Korea runs a mix of 500 MW subcritical and
1,000 MW ultra-supercritical units, so neither the reported fleet emission
factor nor the USC design value alone is representative.

| | before | after |
|---|---|---|
| coal `fuel_consumption` | 3.8250 | **2.6316** |
| coal emission factor | 1.3024 | **0.8961** tCO2/MWh |
| coal CCS `fuel_consumption` | 4.8000 | **3.3024** |
| coal CCS emission factor | 0.1114 | **0.0766** |

Coal CCS was scaled by the same ratio so its energy penalty relative to
unabated coal (1.255×) is preserved. `emission_rate` (0.3405 tCO2/MWh of
fuel) is the carbon content of the fuel, matches published values, and was
**not** changed.

Applied to 26 files (both cases, all 7 periods). Backups in
`_backup_coaleff/`.

Expected effect: coal LCOE in 2050 falls from about \$80 to \$61/MWh,
narrowing the gap to solar (\$38) from \$43 to \$24. In the Ref case coal
should hold on longer and less solar should be built; in NDC the lower
emission factor makes the CO2 cap easier to meet with less coal
retirement.

---

### 7.5 Solar build-rate limit (2026-10-13)

The model previously added solar faster than Korea has ever built it:
up to 9.3 GW/yr nationally in Ref and **26.5 GW/yr in NDC (2025–30)**,
against a Korean record of 4.1 GW in 2020 and an 11th Basic Plan implied
rate of 4.8 GW/yr to 2030. Nothing in the model represented permitting,
grid-connection queues, or supply-chain limits.

`MaxNewCapacityConstraint` is now enabled on all 17 provincial solar
assets with `max_new_capacity = 7,500 MW` per 5-year period, i.e.
**1.5 GW/yr per province**. That is roughly 37% of Korea's national
historical maximum concentrated in a single province, so it is a generous
rather than a binding-everywhere limit; 12 of 17 provinces are unaffected.

This version of MacroEnergy implements `MaxNewCapacityConstraint`
**per asset**, not as a grouped or system-wide limit (the grouped version
is a later upstream PR), so a national cap cannot be imposed directly.
The per-province limit cuts the concentration — Gangwon was adding
25.3 GW in a single period — and the resulting national total has to be
checked after each run. If it still exceeds about 25 GW per period, lower
the per-province value or upgrade MacroEnergy.

Wind is left unconstrained; onshore wind stops at 4.1 GW in Ref on its own.

Applied to 14 files (both cases, all 7 periods). Backups in
`_backup_buildrate/`.

**Tightened to 6,000 MW per province per period on 2026-10-13** after the
first run with the limit in place; see §7.6.4 for the measurement that
prompted it.

| reference | GW/yr |
|---|---|
| Korea national record (2020) | 4.1 |
| 11th Basic Plan implied, 2024–30 | 4.8 |
| per-province limit, first version | 1.5 |
| **per-province limit, current** | **1.2** |

---

## 7.6 Changes made 2026-10-13 (after the first full run)

The run of 2026-10-13 (Ref `results_004`, NDC `results_003`) was the first
to complete with §7.1–7.5 all in place. It confirmed those fixes and
exposed four further problems, fixed below. Backups in
`_backup_20261013_fix4/`.

### What the run confirmed

| fix | evidence from the run |
|---|---|
| 99.1 GW transmission (§4) | `existing_capacity` 2021 = 99.07 GW |
| coal efficiency (§7.4) | heat rate measured from `flows.csv` = 2.6317, i.e. 38.0% |
| solar build rate (§7.5) | 7,500 MW cap binding in 8 Ref and 20 NDC province-periods |
| fuel costs in objective (§7.3) | `Node{Coal} Supply` = $14.1B in Ref 2050 |

The transmission network **expanded for the first time**. Under the old
171 GW network new capacity was exactly 0 GW in all 7 periods of every
scenario; under 99.1 GW the model adds 3.14 GW immediately in 2021 and
reaches 105.6 GW (Ref) / 103.9 GW (NDC) by 2050. Electricity non-served
demand is effectively zero in both cases (under 25 GWh against
550–740 TWh of load).

### 7.6.1 Transmission variable O&M was being paid out, not charged

`variable_om_cost = 1 $/MWh` was set on every corridor, but a
`TransmissionLink` is a `BidirectionalEdge` whose flow variable is
**signed**. MacroEnergy charges `variable_om_cost × flow`, so whenever
power moves against the corridor's declared `start_vertex → end_vertex`
direction the term is negative and the model is *paid* to transmit.

Measured in the run:

| | transmission VariableOM |
|---|---|
| Ref 2050 | −$653 M |
| NDC 2021 | −$2,132 M |
| NDC 2050 | −$669 M |

Against a NDC 2021 total system cost of $121 B that is a −1.8% distortion,
and it biases dispatch toward reverse-direction flow. The sign is
consistent with the flow data: summed signed transmission flow is
−486 to −625 TWh, because the corridor directions in the CSV were assigned
from the province-code ordering rather than from the physical
coast-to-metro flow direction.

**Fix: `variable_om_cost = 0` on all 32 corridors in all 7 periods of both
cases (448 rows).** Zero is the right value here regardless of the sign
bug, because the corridors carry no documented per-MWh O&M figure; the
$443,638/MW base and the $100/MW-yr `fixed_om_cost` are also undocumented
(§4). Losses, which are the real per-MWh cost of transmission, are already
represented by `loss_fraction`.

Do not simply flip the sign or take an absolute value in the input file —
that is not expressible in the CSV. If a per-MWh transmission cost is
wanted later, either confirm that the MacroEnergy version in use charges
`|flow|`, or split each corridor into two unidirectional edges.

### 7.6.2 New coal was allowed, and the efficiency fix made it economic

`coalpower_<year>.csv` had `can_expand = TRUE` in 16 of 17 provinces for
2025–2050, at `investment_cost = 1,164,761 $/MW`. This had never bound,
because at the old 26.1% efficiency coal was not economic. Correcting the
efficiency to 38.0% (§7.4) cut coal's fuel cost per MWh by 31% and the Ref
case promptly **built 1.92 GW of new coal in 2025**, holding 37.8 GW of
coal at 88% capacity factor and 291 TWh through 2050.

That is inconsistent with Korean policy: no new coal permit has been
issued since 2017, and neither the 10th nor the 11th Basic Plan contains
any new coal unit. The model should not have the option.

**Fix: `can_expand = FALSE` on all 16 expandable coal assets in
assets_2025 through assets_2050, both cases (192 rows).** 2021 was already
FALSE and is untouched, so the 35.8 GW existing fleet and its age-based
retirement are unaffected. `coalpowerCCS` is deliberately left expandable:
it is a retrofit/abatement technology, not a new unabated coal unit, and
it never deploys anyway.

### 7.6.3 (not applied) Nuclear has no build-rate or siting limit

Recorded here because it was considered and deferred, not fixed. Nuclear
carries no `max_capacity` and no `MaxNewCapacityConstraint`, and
`can_expand = TRUE` in 16 of 17 provinces. In Ref this does not bind —
nuclear stays at 23.3 GW for all 7 periods, so it is uneconomic at a zero
carbon price. In NDC it builds 38 GW, including **14.9 GW in the single
2025–2030 period**, which is faster than Korea has ever built nuclear
(Shin-Hanul 3 and 4 are roughly a decade per pair). A limit of about
2–3 GW per period is the obvious next step; it is in §10.

### 7.6.4 Solar build rate tightened to 6,000 MW per province per period

With the 7,500 MW limit the national new-build total was still above
target:

| | new solar, 2025–30 | GW/yr |
|---|---|---|
| Ref | 32.5 GW | 6.5 |
| NDC | 64.3 GW | 12.9 |
| target (§7.5) | 25 GW | 5.0 |

The limit was binding in 3 Ref provinces and 7 NDC provinces in that
period, so lowering it moves the national total directly.

**Fix: `max_new_capacity = 6,000` on all 17 `utility_pv` assets in all 7
periods of both cases (238 rows), i.e. 1.2 GW/yr per province.** Wind is
untouched and still has `MaxNewCapacityConstraint = FALSE`. The
per-province `max_capacity` potential values are unchanged.

This remains a per-asset limit, not a national one, for the reason given in
§7.5. Ref should land near 5.6 GW/yr; NDC will stay above target because
its CO2 cap forces the build, and that is a defensible result rather than
an artifact.

### 7.6.5 The stale `system/demand.csv` removed from both cases

`Ref/system/demand.csv` and `NDC/system/demand.csv` were byte-identical and
**neither was read by the model**: all 14 `nodes_<year>.json` files point at
`system/demand_ref.csv` and `system/demand_NDC.csv` respectively. The file
was also internally broken — its `_40`, `_45` and `_50` electricity columns
are byte-identical copies of `_35`, so anything that did read it would see
Ref demand plateau at 649 TWh after 2035. It had already caused one
misdiagnosis of the Ref results.

It could not simply be deleted: `Post-processing files/Demand/build_macro_demand.py`
uses it as a **header template**, reproducing its exact column order and
carrying over the `Demand_heat*` and `Demand_Zero` placeholder columns.

**Fix:** moved to
`Post-processing files/Demand/demand_schema_template.csv` in both cases and
`TEMPLATE` in `build_macro_demand.py` repointed at it, so `system/` now
contains only files the model actually loads. The script's docstring records
why, and additionally records that the script writes only the
2021/`_25`/`_30`/`_35` columns — the `_40`/`_45`/`_50` columns in
`demand_ref.csv` and `demand_NDC.csv` were produced outside it and are not
regenerated by rerunning it.

Verified demand after the move, from the files the model actually reads:

| year | Ref, TWh | NDC, TWh |
|---|---|---|
| 2021 | 553.4 | 553.4 |
| 2030 | 628.4 | 600.4 |
| 2040 | 650.6 | 678.3 |
| 2050 | 669.5 | 742.3 |

2021 is identical across the two cases, as it must be, and no period is a
duplicate of another.

---

## 8. Known issues and open questions

Ordered by how much they affect whether results are defensible.

**Solar builds to the technical-potential cap, not to an economic
optimum.** In Ref 2050, 15 of 17 provinces sit at their `max_capacity` to
the decimal (239.0 of 252.9 GW). The two that do not are network-limited
(Jeju, which can only export 900 MW by HVDC, and Gyeongbuk). The binding
constraint is the resource cap. Since technical potential excludes
permitting, setbacks and acceptance — and Korean reporting suggests actual
deployment reaches roughly 10% of potential — a sensitivity at 30–50% of
technical potential is needed before this result is presented as an
economic finding.

**No firm-capacity or reserve requirement.** Electricity non-served demand
is exactly zero in every run, which means the system is only being judged
against the single weather year it was given. A planning reserve margin,
or a stress-year check on the solved mix, is missing.

**CCS never deploys, for two independent reasons.** (a) The CO2 storage
limit of 4.75 Mt/yr is flat in every period, capping CCS at under 2% of
2050 generation even at zero cost — Korea's own CCUS roadmap assumes
growth. (b) Even within that cap it does not pencil: gas CCS costs about
\$246/MWh once residual emissions are priced at the model's own shadow
price, against a system average electricity price of \$89/MWh, because
capture is set at 90%. Raising capture to 95–99% is the highest-value
test. The injection-cost correction (§3) changed almost nothing;
injection is only a few percent of total CCS cost.

**CO2 shadow price is implausibly high.** Measured in the 2026-10-13 NDC
run, with the cap binding exactly in every period from 2025 on:

| year | cap, MtCO2 | shadow price, \$/tCO2 |
|---|---|---|
| 2025 | 207.0 | non-binding dual |
| 2030 | 92.0 | **5,566** |
| 2035 | 48.0 | 4,731 |
| 2040 | 36.0 | 4,602 |
| 2045 | 27.0 | 4,211 |
| 2050 | 20.7 | 3,622 |

That is 40 to 60 times the EU ETS. It signals missing abatement options
rather than genuinely expensive abatement: no long-duration storage
(batteries cap at 10 h), no hydrogen, no demand flexibility, no biomass or
BECCS, and CCS effectively unavailable. Note that the solar build-rate
limit (§7.5, §7.6.4) is itself one of the binding constraints producing
this number, so the price is partly a consequence of a deliberate modelling
choice and must be reported alongside it, never on its own.

**Nuclear in BAU is a knife-edge result.** It never expands because it
costs about \$89/MWh against coal at \$82, and BAU prices no carbon. The
crossover sits at roughly \$5/tCO2 — below current K-ETS prices. Reporting
"no new nuclear under BAU" needs a sensitivity. Separately, nuclear capex
(\$2,625/kW) is several times below Lazard's published range; a Korean cost
advantage is real but a gap this wide needs a citation.

**~~Transmission has never expanded.~~** Resolved 2026-10-13. Under the
171 GW network new capacity was exactly 0 GW in every period of every
scenario. Under the 99.1 GW network the model adds 3.14 GW in 2021 and
reaches 105.6 GW (Ref) / 103.9 GW (NDC) by 2050, so the network now binds.
See §7.6.

**Curtailment is large in NDC and unexamined.** 53.2 TWh in 2050, about
17% of combined solar and wind output (Ref: 7.0 TWh). Whether this is a
genuine integration result or an artifact of the fixed 4-hour battery
duration and absent long-duration storage has not been tested.

**~~Operational constraints are inconsistent across technologies.~~**
Resolved 2026-10-12 — see §7.1. All five thermal technologies now carry
the same explicitly-declared constraint set.

**Heat demand is defined with no supply.** 17 heat nodes carry demand but
no Steam-producing asset exists, so roughly **76 TWh per year is
non-served** in every scenario, identically. It is a constant in the
objective and does not distort power-sector conclusions, but it inflates
reported total system cost and makes `non_served_demand.csv` unreadable.
Must be resolved before the heat module lands.

**~~Coal heat rate implies 26% efficiency.~~** Resolved 2026-10-13 — see §7.4.

**Pumped hydro capital cost is \$30/kW**, against roughly \$1,500–2,500/kW
in reality — 50 to 80 times too low — and `can_expand` is TRUE. No pumped
hydro is currently added, but nothing stops it if conditions shift.

**Hydro fixed O&M is \$1/MW-yr**, effectively zero against a realistic
\$15,000–40,000. `can_expand` is FALSE so it does not affect build
decisions, only reported cost.

**Hydro reservoir duration is 475 hours.** `HydroRes` carries 1,471.8 GWh
of storage energy against only 3.1 GW of turbine capacity, fixed in every
period. Korea's conventional hydro is roughly 1.8 GW with far less stored
energy. The asset generates only 0.6 TWh/yr so it is not distorting
results today, but the energy figure should be traced or the asset
rebuilt before any seasonal-storage analysis.

**Battery power-component cost is \$36/kW**, low against a typical
\$100–200/kW. The energy component (\$48.7/kWh) dominates, so the effect is
limited.

**Still a transport model.** Each corridor is a capacitated edge with no
DC power flow, impedance or N-1 security in the model itself. The ITL was
derived under loop-flow physics and then used in a formulation that
discards it.

**Single weather year**, repeated for every period. No inter-annual
variability, cold snap or wind drought.

**2025 model capacity sits about 11% below observed**, explained by CHP
and industrial self-generation being outside the model boundary. State
this wherever the calibration chart appears.

**Bus count discrepancy.** Slides say 2,217 buses; the loader reports
2,251 from the GIST data. Reconcile before publication.

---

## 9. Corrections to the previous README

Statements in `README1.md` that are **no longer or were never** true:

| previous | actual |
|---|---|
| "Modeling periods: 2025, 2030, 2035" | 7 periods to 2050 |
| "Representative periods — 14 representative days (336 hours)" | **8,760 chronological hours**, 1 subperiod. Contradicted the line above it |
| "No Unit commitment" | **Clustered, linearized unit commitment** |
| "ERA5 … 5km × 5km planned" | slides say 3 km; reconcile |
| "28 corridor pairs (56 directional links)", "`OneWayTransmissionLink`" | **32 bidirectional `TransmissionLink`** |
| "investment cost (₩/kW)" | **\$/MW** |
| "Jeju–Jeonnam loss fraction 0.015" | now follows the distance rule (§4) |
| "Nuclear total 24.5 GW" | 23.2 GW in the model |
| "`demand_NDC.csv` is not usable as-is" | resolved; it is province-level and is what NDC uses |
| "nodes point to `system/demand.csv`" | resolved; `Ref`→`demand_ref.csv`, `NDC`→`demand_NDC.csv` |
| "Nuclear `can_expand` uncapped, no `max_capacity`" | still true — see §8 |
| "Transmission does not expand even when saturated" | still true — see §8 |
| (not previously documented) `Not_usingMyopicSettings` block | removed — see §7.2 |

---

## 10. Backlog

Carried from `README2_update.txt` and extended.

**Model scope**
1. Heat demand and CHP (structure staged in `tmp/`)
2. BECCS electricity (structure staged in `tmp/`)
3. Hydrogen
4. Long-duration storage
5. Demand flexibility

**Input quality**
6. Nuclear build-rate limit, about 2–3 GW per period, and `max_capacity` by
   candidate site — currently both absent, and NDC builds 14.9 GW in the
   2025–30 period alone (§7.6.3). Highest-priority remaining input fix.
7. VRE potential sensitivity at 30–50% of technical potential (note: the 252.9 GW cap already appears to be a market-potential figure, below the white paper's 369 GW national market potential)
8. 3 km ERA5 capacity factors
9. Transmission investment cost from a citable Korean source
10. CCS capture rate 95–99%; CO2 storage limit on a growth trajectory

**Model structure**
11. Planning reserve margin / capacity adequacy
12. ~~Enable the operational constraints that are currently parameter-only~~ — done 2026-10-12 (§7.1)
13. Perfect-foresight benchmark against the myopic solve
14. Re-derive ITLs at N-2, ideally over stressed system states

**Validation**
15. Compare demand against the 11th Basic Plan
16. ~~Re-run Ref and NDC with the 99 GW network; check whether transmission
    finally expands and whether unserved energy appears~~ — done 2026-10-13.
    Transmission expands; electricity unserved energy stays at zero (§7.6).
17. Confirm national solar new-build lands near 5 GW/yr under the 6,000 MW
    per-province limit (§7.6.4)
18. Confirm transmission VariableOM is no longer negative in
    `costs_by_type.csv` (§7.6.1)
19. Confirm no new coal appears in Ref 2025 (§7.6.2)

---

## 11. Sources

- BNEF, *South Korea key cost metrics*, 5 Dec 2025 (`20251205 BNEF Korea data .xlsx`) — capital and O&M costs, Mid scenario
- Brown, Barrows, Wright, Brinkman, Dalvi, Zhang, Mai (NREL), *A general method for estimating zonal transmission interface limits from nodal network data*, arXiv:2308.03612 (2023) — interface transfer limits
- KPX, 2024년도 전력계통 운영실적 (2025.11) — metro transfer limit, demand shares
- GIST public-data reconstruction of the Korean grid (~2024 network) — nodal topology, line ratings, generator and load siting
- 신재생에너지 백서 — provincial technical potential for solar and wind
- EPSIS / KHNP / KEPCO plant-level statistics (`province level_power (3).xlsx`) — 2021 existing capacity
- ERA5 reanalysis, 2021, KST — hourly provincial capacity factors
- GCAM (`<case>/input.xlsx`) — electricity demand, delivered fuel prices, power-sector CO2 budget
- Lazard, *Levelized Cost of Energy+*, Version 19.0 (July 2026) — LCOE cross-check only, not a model input
- Korea JoongAng Daily, *Korea seeks faster power grid expansion by burying transmission lines under roads* — 345 kV overhead and underground construction costs
