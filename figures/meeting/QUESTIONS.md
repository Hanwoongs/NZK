# MACRO-Korea — technical questions

Provincial power-sector model, 17 provinces, 8,760 chronological hours,
2021–2050 in 7 myopic periods, linear-relaxed unit commitment, Gurobi barrier.

**Before anything else:** the results below are from the run of 13 October and
predate three staged base-year fixes (coal availability 0.65, nuclear
availability 0.85 → 0.78, 2021 gas retirement blocked). The 2021 generation mix
is known to be wrong — coal 300 TWh against 198 observed, gas 58 against 167 —
and the cause is identified: coal and gas carried no availability field, so both
defaulted to 1.0 and coal ran at a 95% capacity factor.

---

## Q1 · `MaxNewCapacityConstraint` is per-asset, so we cannot cap a national build rate

In this version the constraint applies per asset.

- **What we need:** a national limit of about 5 GW/yr, against a Korean record
  of 4.1 GW in 2020 and an 11th Basic Plan rate of roughly 4.8 GW/yr.
- **What we can express:** 6,000 MW per province per 5-year period, i.e.
  1.2 GW/yr each — or 20.4 GW/yr if all 17 provinces bind at once.

The per-province cap therefore has almost no grip on the national total.
Tightening it relocates the build rather than limiting it:

| per-province cap | national peak, Ref | national peak, NDC | Ref 2050 solar |
|---|---|---|---|
| 7,500 MW per 5-yr period | 6.5 GW/yr | 12.9 GW/yr | 139.4 GW |
| 6,000 MW per 5-yr period | 6.0 GW/yr | 10.6 GW/yr | **141.7 GW** |

Lowering the cap *raised* 2050 solar. Only 14 of 119 province-periods bind in
Ref and 28 of 119 in NDC, so a province that hits the cap simply hands the build
to a neighbour that still has headroom.

**Questions**
1. Is a grouped or system-wide `MaxNewCapacityConstraint` available upstream,
   and can we pull it into the version we are running?
2. If not, is `user_additions` the right place to write a custom constraint over
   a set of assets, and is there a pattern you would recommend?

This is our highest priority. Solar dominates every scenario result and the only
control we have over it does not function.

---

## Q2 · `MinFlowConstraint` on all five thermal technologies exhausted memory

| | rows |
|---|---|
| MinFlow on coal and gas CCGT only | 13.60 M |
| MinFlow on all five thermal technologies | 14.05 M |
| added by three technologies | ≈ 450,000 |

Two jobs were killed at 128 GB. We removed it from nuclear, coal CCS and gas CCS
(38 files) and raised memory to 192 GB.

**Questions**
1. Is that row growth expected for three technologies × 17 provinces × 8,760
   hours, or does it suggest we have the formulation wrong?
2. Is there a cheaper way to express a minimum stable output under relaxed UC?
3. The `min_flow_fraction` values are still present in the CSVs for those three
   technologies while the constraint is not declared. Can we rely on them being
   completely inert, or should we strip them to avoid ambiguity?

---

## Q3 · Nuclear is completely rigid, and the carbon price absorbs it

Nuclear carries `MustRunConstraint` plus a flat 0.85 availability. Its capacity
factor is **exactly 85% in all seven periods, in both scenarios** — zero hourly
variation. In NDC 2050 that is 468 TWh of completely inflexible output.

The NDC carbon shadow price:

| year | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| \$/tCO₂ | **10,515** | 5,576 | 4,771 | 4,756 | 4,244 | 3,588 |

Tens of times any real carbon price. VRE curtailment reaches 51 TWh in NDC 2050.
Our reading is that this is not expensive abatement but *absent* abatement: no
long-duration storage, no hydrogen, no demand response, no BECCS, and CCS capped
by a flat 4.75 Mt/yr CO₂ storage limit. With nuclear unable to move, the cap can
only be met by curtailing solar.

**Questions**
1. What is the idiomatic way to represent near-baseload nuclear in MACRO? Should
   we drop `MustRunConstraint` and use a low `min_flow_fraction` instead?
2. Does a shadow price at this magnitude indicate a formulation problem we should
   look for, or is it simply what a tight cap with few options produces?
3. The 2025 value of \$10,515 is the outlier. Anything specific to check there?

---

## Q4 · Transmission: signed bidirectional edges, and a transport formulation

We derived 32 inter-province limits from nodal data using the NREL ITL method
(Brown et al., arXiv:2308.03612) — a PTDF linear program with loop flow and n-1.
Those limits are then used in a transport model with no impedance, no DC power
flow and no security constraint.

We also hit a sign problem. `variable_om_cost = 1 $/MWh` on a `BidirectionalEdge`
whose flow variable is signed meant the model was *paid* to transmit in the
negative direction:

| | before | after setting it to 0 |
|---|---|---|
| NDC 2021 transmission VariableOM | −\$2,132 M | 0 |
| corridors pinned >95% of hours | 9 of 32 | **0 of 32** |
| total \|flow\| | 645 TWh | 345 TWh |

Resolved, but the formulation question stands.

**Questions**
1. Does MACRO offer a DC power flow or any impedance-aware transmission
   representation, or is the transport model the intended abstraction?
2. To charge a genuine per-MWh cost, should each corridor be split into two
   unidirectional edges? Is there a version that charges on `|flow|`?
3. Is `can_retire = FALSE` with a fixed topology the normal setup, or do people
   model corridor reconfiguration?

---

## Q5 · Myopic versus perfect foresight

We run myopic. NDC builds **14.9 GW of nuclear in the single 2025–2030 period**,
which is far faster than Korea has ever built nuclear. There is no build-rate
limit on nuclear, so this is partly a missing constraint, but we also suspect
myopic short-sightedness.

Current performance: 17–19 minutes per period; 2.5 h (Ref) and 4.6 h (NDC)
end to end on 24 cores and 192 GB.

**Questions**
1. Is perfect foresight tractable at 8,760 hours × 7 periods at this problem
   size, and roughly what does it cost?
2. Would you expect the nuclear build path to smooth materially under perfect
   foresight, or is the missing build-rate limit the whole story?

---

## Q6 · Staging a sector that does not exist yet

17 Steam nodes carry demand, but no asset produces Steam. The result is
**76,212 GWh non-served in every period of every scenario, identically**. It does
not distort the power solution, but it inflates reported system cost and makes
`non_served_demand.csv` hard to read.

**Question** — what is the recommended way to stage a sector that is defined but
not yet built? Remove the nodes until the sector lands, keep them with a zero
penalty, or something else?

Heat is our next sector, due November 2026, so this affects how we wire it in.

---

## Shorter items

**`HydroRes` duration is 475 hours.** 1,471.8 GWh of storage against 3.1 GW of
turbine capacity, fixed in every period, generating only 0.6 TWh against an
observed 6.7 TWh for Korean hydro. This looks inherited from the MacroEnergy
example data — can you confirm the provenance?

**Battery settles at 5.6–5.7 h duration** given a 2–10 h range, in both
scenarios. Plausible, but we would like a sanity check.

**Solver settings.** Barrier with `Method=2`, `Crossover=0`, `BarConvTol=1e-3`,
`Threads=22`, `BarHomogeneous=1`, over 8,760 hours in a single subperiod. Any
advice on these, or on `scaling.jl` behaviour at this size?

---

## What we are asking for, in priority order

1. **Grouped `MaxNewCapacityConstraint`** — unblocks every build-rate limit we need
2. **The right construct for near-baseload nuclear** — drives both the carbon
   price and the curtailment result
3. A cheaper `MinFlow` formulation, or confirmation that the row cost is simply real
4. Transmission: DC flow, or guidance on splitting edges
5. Whether perfect foresight is tractable here
6. How to stage an unbuilt sector — needed before heat, next month

Items 1 and 3 decide whether our solar and carbon-price results are defensible.
