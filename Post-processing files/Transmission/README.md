# Inter-province transmission capacity — how the numbers are built

Last updated 2026-10-12. Current model input: **99.1 GW** across 32
corridors, installed in `Ref/assets/assets_2021/transmission_v2_2021.csv`
and `NDC/assets/assets_2021/transmission_v2_2021.csv`.

Later periods inherit this by myopic carry-forward, so the 2021 file is
the only place the network is set.

---

## The chain

| step | metro import | total network | × national peak |
|---|---|---|---|
| 0. Sum of line thermal ratings | — | 418.4 GW | 4.6 |
| 1. Interface Transfer Limits (NREL) | 37.0 GW | 171.1 GW | 1.89 |
| 2. + injection caps | 24.2 GW | 109.5 GW | 1.21 |
| 3. + metro calibration to KPX | **13.8 GW** | **99.1 GW** | **1.10** |
| *published reality (KPX 2024)* | *12.0–13.8* | — | — |

National peak demand in the model is 90.3 GW; metro (SEL+INC+GGI) peak is
36.9 GW, which is 40.8% of national against KPX's published 41.1%, so the
demand side was already consistent and only the network needed fixing.

---

## Step 0 — Sum of thermal ratings (superseded)

Add up the rating of every line crossing a province boundary.
**418.4 GW.** Wrong because it ignores Kirchhoff loop flow, applies no
N-1 security de-rating, and treats interfaces as symmetric. The worst
artifact was Gyeongnam–Ulsan at 71 GW, created by the Kori/Shin-Kori
765 kV switchyard sitting on a three-province boundary.

Kept for reference as `transmission_v2_2021_OLD_sum_of_ratings_418GW.csv`.

## Step 1 — Interface Transfer Limits

Method: Brown et al. (NREL), *A general method for estimating zonal
transmission interface limits from nodal network data*, arXiv:2308.03612.
Re-implemented as a PTDF linear program in `compute_itl.py`, validated
against the paper's 5-bus test case.

For each interface and direction, maximise flow across the boundary
subject to DC power flow, thermal limits on every line in the network,
and sign-constrained bus injections. `n-1` drops the highest-flow
crossing line and re-solves.

Model value per corridor: `min(n-1 A→B, n-1 B→A) + HVDC`, since a
`TransmissionLink` carries one capacity valid both ways. HVDC is added
undiminished because converter-scheduled DC flow is not subject to AC
loop flow.

**Result 171.1 GW.** Output: `transmission_v2_2021_ITL_bidir.csv`.
This was the model input until 2026-10-12.

## Step 2 — Cap the injections (`compute_itl_capped.py`)

The NREL formulation lets any generator bus inject and any load bus
withdraw without limit: it measures the *network's* capability, not what
the fleet can deliver. The original package README flags this.

Changes versus `compute_itl.py`:

- per-bus caps built from the GIST data, `gen_cap[b] = Σ p_max_mw` over
  in-service generators and `load_cap[b] = Σ p_mw` over in-service loads
  (101.8 GW generation, 77.1 GW load)
- radial reduction folds a collapsed bus's **capacity** into its
  neighbour, not just its role
- bus bounds use those caps instead of ±10⁷ MW

Still passes the 5-bus validation. **Result 171.1 → 109.5 GW**, metro
import 37.0 → 24.2 GW. Largest movers: Seoul–Gyeonggi 11.6 → 3.6,
Gangwon–Chungbuk 5.0 → 1.4, Chungbuk–Gyeonggi 17.5 → 9.8 GW.

Runtime about 7 minutes. Output: `outputs/province_ITL_capped.csv`.

## Step 3 — Metro calibration (`build_transmission_final.py`)

Even capped, the model let the capital region import 24.2 GW against a
metro peak demand of 36.9 GW. KPX publishes the actual limit.

**Anchor — KPX, 2024년도 전력계통 운영실적:**

- 41.1% of national demand is in the metro
- 30.3% of supply capability is generated there
- 11.1% is imported from outside (융통전력)
- the metro transfer limit ran 12,000 MW in January to **13,800 MW in
  August**, and was exceeded once in 2024 (11 June, 10:00)

The August peak-month figure is used, since a capacity-expansion model
should be sized to the stressed case.

**Why a correction is needed at all.** The 31 interface limits are each
solved with the rest of the network free to redispatch to maximise flow
across that one interface, so they are not simultaneously achievable. A
transport model treats them as independent constraints and will load all
of them at once. Korea also plans these corridors to N-2 while the ITL LP
uses a simplified N-1.

**What is changed:** only corridors *crossing* the metro boundary, and
only their AC component. AC factor **0.509**.

| corridor | ratings | ITL | capped | final |
|---|---|---|---|---|
| Chungbuk–Gyeonggi | — | 17.5 | 9.8 | **5.0** |
| Chungnam–Gyeonggi | — | 9.9 | 9.2 | **6.1** |
| Gangwon–Gyeonggi | — | 9.6 | 5.2 | **2.7** |

**What is not changed:** corridors *inside* the metro (Seoul–Gyeonggi,
Incheon–Gyeonggi, Seoul–Incheon), every non-metro corridor, and all HVDC
(Jeju–Jeonnam 900 MW, Bukdangjin–Godeok 3,000 MW).

An earlier attempt applied the factor to all 32 corridors and produced
38.9 GW. That was wrong: the metro is only 22% of the network, so
correcting it nationally over-cut the other 78%. Do not repeat it.

## Distance-scaled cost and losses

The template carried one flat value for every corridor, \$443,638/MW and
3% loss, whether the line is 27 km or 162 km. The `distance` column
existed and was unused.

Rescaled so the **mean corridor is unchanged**, needing no new cost data:

- **5,200 \$/MW/km**
- **0.0352 %/km**

Seoul–Incheon (27 km) is now \$140k/MW; Gangwon–Gyeongbuk (162 km) is
\$842k/MW.

Note: the \$443,638/MW base is itself undocumented. It traces back to the
MacroEnergy example file, which carried \$12,060/MW and distance-scaled
losses. Both were changed at some point with no record. Replacing it with
a Korean build-cost figure is open work.

## Variable O&M set to zero (2026-10-13)

Every corridor carried `variable_om_cost = 1 $/MWh`. A `TransmissionLink`
is a `BidirectionalEdge` whose flow variable is **signed**, and MacroEnergy
charges `variable_om_cost × flow`, so flow against the declared
`start_vertex → end_vertex` direction produced a **negative** cost. The
model was being paid to transmit.

Measured in the 2026-10-13 run:

| | transmission VariableOM |
|---|---|
| Ref 2050 | −\$653 M |
| NDC 2021 | −\$2,132 M |
| NDC 2050 | −\$669 M |

The sign follows from the data: summed signed transmission flow is −486 to
−625 TWh, because corridor directions in the CSV were assigned from
province-code ordering, not from the physical coast-to-metro flow
direction. Against NDC 2021's \$121 B total system cost this was a −1.8%
distortion and a standing incentive for reverse-direction flow.

**`variable_om_cost = 0` is now set on all 32 corridors in all 7 periods of
both cases.** Zero is defensible independently of the sign bug: no Korean
per-MWh transmission O&M figure was ever cited for this model, and the real
per-MWh cost of transmission is already carried by `loss_fraction`. The
\$100/MW-yr `fixed_om_cost` is left in place but is equally undocumented.

Do not try to fix this by flipping the sign in the CSV — the per-corridor
direction of net flow is an output, not an input. If a per-MWh cost is
wanted later, either confirm the MacroEnergy version in use charges
`|flow|`, or split each corridor into two unidirectional edges.

---

## Files

```
transmission_v2_2021_FINAL_99GW.csv              ← current model input
transmission_v2_2021_ITL_bidir.csv               step 1 (171 GW)
transmission_v2_2021_ITL_oneway.csv              step 1, directional variant
transmission_v2_2021_OLD_sum_of_ratings_418GW.csv  step 0, superseded
province_ITL.csv                                 raw ITLs, uncapped

compute_itl.py                                   step 1 solver
build_transmission_ITL.py                        step 1 → model CSV

ITL_bidirectional/
  compute_itl_capped.py                          step 2 solver
  build_transmission_capped.py                   step 2 + distance scaling
  build_transmission_derated.py                  flat de-rating (superseded)
  build_transmission_final.py                    step 3 → FINAL
  outputs/
    province_ITL_capped.csv
    transmission_v2_2021_ITL_capped.csv          109.5 GW
    transmission_v2_2021_ITL_derated.csv         38.9 GW (superseded)
    transmission_v2_2021_FINAL.csv               99.1 GW
    itl_capped_run.log
```

## Reproducing

```bash
cd ITL_bidirectional
python3 compute_itl_capped.py --validate     # 5-bus check
python3 compute_itl_capped.py                # ~7 min
python3 build_transmission_capped.py         # + distance scaling
python3 build_transmission_final.py          # + KPX metro calibration
```

Then copy `outputs/transmission_v2_2021_FINAL.csv` over
`<case>/assets/assets_2021/transmission_v2_2021.csv`, **preserving the
model file's row order** (the builder writes corridors in a different
order; the install script reorders them).

---

## Open issues

**~~Transmission never expanded under the 171 GW network.~~** Resolved
2026-10-13. Under 171 GW new capacity was exactly 0 GW in every period of
every scenario. Under 99.1 GW the model adds 3.14 GW immediately in 2021
and keeps building:

| | 2021 | 2050 total | periods with new build |
|---|---|---|---|
| Ref | 99.1 → 102.2 | **105.6 GW** | 2021, 2035, 2040, 2045, 2050 |
| NDC | 99.1 → 102.2 | **103.9 GW** | 2021, 2035, 2040, 2045, 2050 |

Electricity non-served demand stayed at effectively zero (under 25 GWh
against 550–740 TWh of load), so the tighter network binds on cost without
making the system infeasible.

**Still a transport model.** Each corridor is a capacitated edge with no
DC power flow, no impedance, and no N-1 security in the model itself. The
ITL was derived with loop flow, then used in a formulation that discards
it.

**Corridors cannot retire or be reconfigured.** `can_retire = FALSE` and
the 2021 topology is permanent.

**N-1 versus N-2.** Korea plans these corridors to N-2; the ITL LP drops
only the single highest-flow crossing line. Recomputing at N-2, and
ideally over a few stressed system states rather than one interface at a
time, is the methodologically clean next step.

**The 2,217 vs 2,251 bus discrepancy.** Slides say 2,217; the loader
reports 2,251 buses from the GIST data. Reconcile before publication.

---

## References

- Brown, Barrows, Wright, Brinkman, Dalvi, Zhang, Mai (NREL),
  arXiv:2308.03612 (2023)
- KPX, 2024년도 전력계통 운영실적 (2025.11)
- GIST public-data reconstruction of the Korean grid (~2024 network)
