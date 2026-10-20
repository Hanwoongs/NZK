# BNEF Korea cost metrics in three unit systems

Source: `20251205 BNEF Korea data .xlsx`, sheet `Sheet1`, region South Korea,
scenarios Low / Mid / High, years 2018–2050.

The model uses the **Mid** scenario. These files put the same numbers side by
side in BNEF, MACRO and GCAM units so the MACRO–GCAM harmonisation can be
checked without going back to the workbook.

---

## Currency chain

| step | factor | note |
|---|---|---|
| BNEF 2024\$ → MACRO 2021\$ | **× 0.870** | the deflator already used for the model's capex |
| MACRO 2021\$ → GCAM 1975\$ | **÷ 5.0400** | US CPI ratio; the same factor used in reverse for the GCAM fuel-price conversion |
| BNEF 2024\$ → GCAM 1975\$ | **× 0.172619** | the two combined |

Verified against the model: PV Mid 2050 capex, 436.7 × 0.870 = 380.0 \$/kW,
and `VRE_50.csv` carries 380,073 \$/MW.

## Unit chain

| metric | BNEF | MACRO | GCAM |
|---|---|---|---|
| Capex | \$/kW | \$/MW | \$/kW |
| Fixed O&M | \$/MW/yr | \$/MW-yr | \$/kW/yr |
| Variable O&M | \$/MWh | \$/MWh | \$/GJ |
| LCOE | \$/MWh | \$/MWh | \$/GJ |
| Short-run marginal cost | \$/MWh | \$/MWh | \$/GJ |

**GCAM caveat.** 1975\$/kW and 1975\$/kW/yr follow GCAM's electricity capital
and fixed-O&M convention. The variable terms are given in 1975\$/GJ because
GCAM's energy unit is EJ. If the GCAM input you are populating expects
1975\$/MWh instead, multiply the `gcam_value` column by 3.6.

---

## Files

```
outputs/
  BNEF_Korea_costs_BNEF_GCAM_MACRO.xlsx   the workbook — 5 sheets:
                                          README, BNEF original, For GCAM,
                                          For MACRO, Model input
  bnef_korea_three_units_long.csv         2,229 rows — every metric, technology,
                                          scenario and year 2018–2050
  bnef_korea_three_units_model_years.csv    471 rows — the same, restricted to
                                          the 7 model periods
  bnef_korea_mid_macro_wide.csv              23 rows — Mid only, MACRO units,
                                          one row per metric × technology
  model_vs_bnef_mid.csv                      77 rows — what is actually in the
                                          asset CSVs against BNEF Low/Mid/High
  nuclear_from_macro.csv                     21 rows — nuclear, which BNEF does
                                          not cover, taken from the asset files
  ccs_japan_proxy.csv                       108 rows — coal CCS and gas CCS,
                                          Japan used as the proxy for Korea
  gcam_current_costs.csv                  2,596 rows — every OCC, O&M, FCR and
                                          capacity factor in the GCAM XML, with
                                          the line number of each
  macro_to_gcam_mapping.csv                 132 rows — GCAM current against the
                                          Korean value, per technology and year
  gcam_edit_log.csv                         303 rows — every value written into
                                          the XML: line, year, old, new
```

Long-format columns: `metric, technology_bnef, technology_model, scenario,
year, bnef_value, bnef_unit, macro_value, macro_unit, gcam_value, gcam_unit`.

Technology names are mapped to the model's: `PV fixed-axis` → `Solar PV`,
`CCGT` → `Gas CCGT`, `Wind onshore` → `Onshore wind`, `OCGT` → `Gas CT`.

Reproduce with:

```bash
python3 build_bnef_harmonised.py    # the three CSVs
python3 extract_gcam.py             # read the GCAM XML
python3 build_mapping.py            # nuclear + the MACRO->GCAM mapping
python3 build_ccs.py                # coal CCS and gas CCS, Japan proxy
python3 build_excel.py              # the workbook
python3 compare_model_vs_bnef.py    # the audit against the asset files
python3 apply_to_gcam.py            # write the Korean costs into the GCAM XML
```

---

## What the audit found

**Capex matches BNEF Mid exactly from 2025 on.** Every technology, every
period, within 0.1%, except 2030 where solar and onshore wind are 0.9–1.0%
high. The 0.870 deflator is confirmed.

**2021 capex does not follow the deflator** and is 27–30% below BNEF Mid. This
is already recorded in the main README: the 2021 column appears to come from a
different source. It does not affect results, since 2021 is the calibrated base
year with `can_expand = FALSE`.

**Fixed O&M used a different deflator — 0.910, not 0.870.** Backing it out of
the asset files gives 0.9100 to 0.9103 for solar and onshore wind in every
period from 2025 on, against 0.8700 for capex. Example: solar 2050, BNEF Mid is
16,899 \$/MW-yr in 2024\$, and the model carries 15,384, a ratio of 0.9103.
This is a 4.6% overstatement of fixed O&M relative to the capex convention.
It is not a year offset — that was tested and ruled out.

**~~Coal and gas O&M are flat and are not BNEF Mid at all.~~** Fixed
2026-10-19. The model carried single values repeated across all seven periods,
sitting between BNEF Mid and High, with no recorded source:

| | was, all periods | now, BNEF Mid × 0.870 |
|---|---|---|
| Coal fixed O&M | 15,816 \$/MW-yr | 15,122 → 14,114 → 13,708 |
| Coal variable O&M | 1.55 \$/MWh | 1.444 → 1.309 |
| Gas CCGT fixed O&M | 15,274 \$/MW-yr | 14,603 → 14,993 → 14,561 |
| Gas CCGT variable O&M | 1.82 \$/MWh | 1.713 → 1.553 |

Applied to `coalpower_*.csv` and `NaturalGasPower_*.csv`, all 7 periods, both
cases — 28 files, 952 cells. 2021 takes the BNEF Mid 2021 value rather than
being held at the 2025 level, so the base year moves slightly too. Coal and gas
O&M now vary over time, which they did not before.

The audit count fell from 35 rows more than 1.5% off Mid to 11, and the
remaining 11 are all the VRE fixed-O&M deflator issue above.

**Still open.** Fixed O&M for solar and wind uses 0.910 while everything else
uses 0.870. Until that is reconciled, the harmonisation statement should read
**"BNEF Mid, 2024\$ deflated to 2021\$ at 0.870, except VRE fixed O&M at
0.910"** rather than simply "BNEF Mid".

---

## Nuclear

BNEF's Korea sheet has no nuclear, so the model's values come from elsewhere
and the original source is **not recorded**. They are carried here as the Mid
case and flagged with an asterisk on every sheet.

| | 2021 | 2050 | unit |
|---|---|---|---|
| Capex | 2,885,794 | 2,624,715 | 2021\$ \$/MW |
| Fixed O&M | 199,087 | 199,087 | 2021\$ \$/MW-yr |
| Variable O&M | 10.34 | 10.34 | 2021\$ \$/MWh |

Capex declines linearly from 2025, about \$52,216/MW per period. O&M is flat.
Other parameters: lifetime 50 years, WACC 0.10, `fuel_consumption` 3.0644
(32.6% efficiency).

The capital cost is the number to watch. At **\$2,625/kW in 2050** it is well
below Lazard's published range and about 38% of what GCAM carries globally.
A Korean cost advantage in nuclear construction is real and documented, but a
gap this wide needs a citation before publication.

---

## CCS — Japan as the proxy

BNEF does carry CCS costs, but on a different sheet (`Sheet3`) and **only for
China, Japan and the United States**. There is no South Korea row.

**Japan is adopted as the proxy**, for three reasons:

1. The spread across the three is enormous — coal CCS capex in 2025 is
   \$879/kW in China against \$5,646 in the United States, a factor of 6.4.
   An arithmetic mean of three numbers that far apart is dominated by the US
   and is not a meaningful central value.
2. Japan's EPC cost structure is the closest of the three to Korea's.
3. The model's existing CCS fixed O&M already matches **Japan Mid 2030 to
   within 0.12%** for both technologies — 53,714 against 53,649 for coal CCS,
   17,597 against 17,576 for gas CCS. Adopting Japan therefore makes the
   inputs internally consistent rather than introducing a new source.

**2021 is omitted.** Japan's CCS series starts in 2022, and that first year is
a first-of-a-kind cost — \$10,100/kW for coal CCS against \$2,697 the year
after. Carrying it back would put a fourfold spike at the front of the series.
The model has no CCS asset in 2021 either: `assets_2021` contains neither
`coalpowerCCS` nor `NaturalGasPowerCCS`.

Japan Mid, in MACRO units:

| | 2025 | 2030–2050 | unit |
|---|---|---|---|
| Coal CCS capex | 1,943,179 | 1,341,309 | 2021\$ \$/MW |
| Coal CCS fixed O&M | 52,507 | 46,675 | \$/MW-yr |
| Coal CCS variable O&M | 18.69 | 18.38–18.40 | \$/MWh |
| Gas CCS capex | 1,566,062 | 1,080,999 | \$/MW |
| Gas CCS fixed O&M | 17,202 | 15,291 | \$/MW-yr |
| Gas CCS variable O&M | 8.39 | 8.05–8.22 | \$/MWh |

**Against what the model carries now:**

| | model | Japan Mid | |
|---|---|---|---|
| Coal CCS capex 2035+ | 2,028,809 | 1,341,309 | −34% |
| Gas CCS capex 2035+ | 1,208,525 | 1,080,999 | −11% |
| Coal CCS fixed O&M | 53,714 | 46,675 | −13% |
| Gas CCS fixed O&M | 17,597 | 15,291 | −13% |
| Coal CCS variable O&M | 19.14 | 18.38 | −4% |
| Gas CCS variable O&M | 8.58 | 8.05 | −6% |

The model's current numbers do not follow any single rule — fixed O&M tracks
Japan Mid 2030 almost exactly, coal CCS capex is close to a three-country mean,
and the rest matches nothing. None of them appear to have had the 0.870
deflator applied, so they may be 2024\$ sitting in a 2021\$ field, which would
overstate CCS cost by about 15%.

**Applied to both MACRO and GCAM on 2026-10-19.** See the sections below.

### Applied to MACRO

`coalpowerCCS_*.csv` and `NaturalGasPowerCCS_*.csv`, both cases, 2025–2050 —
**24 files, 1,224 cells**. `assets_2021` has no CCS files, so the base year is
untouched.

| | was | now, Japan Mid |
|---|---|---|
| Coal CCS capex 2025 | 2,509,255 | 1,943,179 |
| Coal CCS capex 2030+ | 2,028,809 | 1,341,309 |
| Coal CCS fixed O&M | 53,714 flat | 52,507 → 46,675 |
| Coal CCS variable O&M | 19.135 flat | 18.69 → 18.38 |
| Gas CCS capex 2025 | 1,718,028 | 1,566,062 |
| Gas CCS capex 2030+ | 1,208,525 | 1,080,999 |
| Gas CCS fixed O&M | 17,597 flat | 17,202 → 15,291 |
| Gas CCS variable O&M | 8.58 flat | 8.39 → 8.05 |

Verified: 17 rows per file all carrying one value, CRLF preserved, Ref and NDC
assets still byte-identical.

---

## Mapping to GCAM

`macro_to_gcam_mapping.csv` and the **GCAM mapping** sheet line up each model
technology with its GCAM counterpart, give the current GCAM value against the
Korean one, and carry the **line number in the XML** where each value sits.

| MACRO | GCAM subsector | GCAM technology |
|---|---|---|
| Coal | coal | `coal (conv pul)` |
| Gas CCGT | gas | `gas (CC)` |
| Solar PV | solar | `PV` |
| Onshore wind | wind | `wind` |
| Offshore wind | wind | `wind_offshore` |
| Nuclear | nuclear | `Gen_III` |

Korea's new build is the APR-1400, a Gen III+ design, so `Gen_III` is the right
target. `Gen_II_LWR` is left alone; if the existing OPR-1000 fleet should carry
Korean costs too, that is a second decision.

**Where to edit.** Only the `electricity` sector inside
`<global-technology-database>`. The cooling variants under `elec_<fuel>`
(`once through`, `seawater`, `recirculating`, `dry cooling`) carry the
*incremental cooling-system* cost — their OCC is about 10 — not the plant cost.
Editing those would be wrong.

**2050, 1975\$:**

| technology | parameter | GCAM | Korea | change | XML line |
|---|---|---|---|---|---|
| Coal | OCC | 491.00 | 231.03 | −52.9% | 257060 |
| Coal | OM-fixed | 17.66 | 2.72 | −84.6% | 257064 |
| Gas CCGT | OCC | 201.00 | 137.97 | −31.4% | 259055 |
| Solar PV | OCC | 148.00 | 75.39 | −49.1% | 249814 |
| Onshore wind | OCC | 185.00 | 279.20 | **+50.9%** | 248213 |
| Offshore wind | OCC | 401.00 | 763.97 | **+90.5%** | 248792 |
| Nuclear | OCC | 1,358.00 | 520.78 | −61.7% | 263050 |
| Nuclear | OM-fixed | 38.50 | 39.50 | +2.6% | 263054 |

Most Korean costs are below GCAM's global defaults, but **wind is far above**:
onshore +51% and offshore +91%. That is the real Korean picture — wind is
roughly twice the cost of solar here — and it is why the model builds almost
no wind.

**Capacity factors have to move with the costs**, or the implied LCOE will be
wrong. The mapping rows for these are shaded:

| technology | GCAM | Korea |
|---|---|---|
| Solar PV | 0.20 | **0.134** |
| Onshore wind | 0.37 | **0.238** |
| Coal | 0.85 | 0.65 |
| Nuclear | 0.90 | 0.85 |

GCAM's solar capacity factor is 50% above Korea's, so leaving it at 0.20 while
lowering the capital cost would make Korean solar look much cheaper than it is.

**One caution.** `<global-technology-database>` is global: editing it changes
all 32 GCAM regions. To change Korea only, override inside the Korea region
block instead.

Also note the discontinuity already in the GCAM file — several technologies
jump at 2040, e.g. coal OCC 407.73 → 525.00 and coal OM-fixed 4.92 → 17.66.
The pre-2040 and post-2040 values come from different vintages. Whatever is
written in should be consistent across all periods.

---

## Applied to GCAM, 2026-10-19

```
exe/electricity_water_cost_updated.xml       original, untouched
exe/electricity_water_cost_updated_KR.xml    the edited copy  <- point GCAM here
outputs/gcam_edit_log.csv                    line, year, old value, new value
```

**399 values written, 349 lines actually changed.** The other 50 were already
equal — the OM-var of solar and both wind technologies is zero in both sources.

| technology | OCC | OM-fixed | OM-var |
|---|---|---|---|
| Coal, Gas CCGT, Solar PV, Onshore wind, Nuclear | 17 each | 17 each | 17 each |
| Offshore wind, Coal CCS, Gas CCS | 16 each | 16 each | 16 each |

Offshore wind and both CCS technologies have no 2021 value, so their 2021
period keeps the GCAM number.

**This leaves a step at 2021 for the two CCS technologies**, because GCAM's own
2021 figures are far from the Japanese ones:

| | GCAM 2021 | Korea 2025 | |
|---|---|---|---|
| Coal CCS OCC | 1,198.33 | 385.55 | 3.1× down |
| Gas CCS OCC | 882.42 | 310.73 | 2.8× down |
| Coal CCS OM-var | 0.005 | 1.030 | 200× up |

The OM-var step looks dramatic but GCAM's own file is already discontinuous
there — its CCS OM-var is about 0.01 through 2035 and then jumps to 3.66 at
2040. Our values are flat at about 1.01 across 2025–2050, which is *more*
consistent than what was there. CCS deployment in 2021 was zero in any case,
so the 2021 figure is effectively inert. Left as is deliberately; backfilling
2021 with the 2025 value is a one-line change if it turns out to matter.

**Years.** 2021 through 2050 take the Korean value. **2055 through 2100 are
held flat at the 2050 Korean value** — BNEF stops at 2050 and extrapolating it
to 2100 would be inventing data. Note this means the cost decline stops at
2050, which is a visible assumption if GCAM is run past then. Years before 2021
(1975 to 2015) are untouched.

**Verified after writing:**

- line count identical, 263,646 both files
- both files parse as valid XML
- all 349 changed lines fall inside `<global-technology-database>`
- only `capital-overnight`, `OM-fixed` and `OM-var` tags changed —
  133 + 133 + 83
- `capacity-factor` changed: **0**. `fixed-charge-rate` changed: **0**
- cooling variants changed: **0**

**Not done, by decision:**

- **Capacity factors.** GCAM keeps 0.20 for solar against Korea's 0.134, and
  0.37 for onshore wind against 0.238. Since GCAM annualises capital as
  `OCC × FCR / (CF × 8760)`, leaving CF high while lowering OCC makes Korean
  solar and wind look cheaper than they are. This has to be revisited before
  the numbers are used.
- `Gen_II_LWR` — only `Gen_III` carries Korean costs. The existing OPR-1000
  fleet still sits on GCAM's global number.
**Scope.** `<global-technology-database>` is global, so these costs now apply
to **all 32 GCAM regions**, not only South Korea. That is acceptable for a
Korea-focused study but would contaminate any multi-region result. Region-level
override was investigated and is possible, but GCAM expresses it as
`minicam-non-energy-input` / `input-cost` in 1975\$/GJ — a single annualised
number — rather than as `capital-overnight`. None of the 381 XML files in this
distribution put `capital-overnight` inside a region block.

---

## Sources

- BNEF, *South Korea key cost metrics*, 5 December 2025
- US CPI, 1975 and 2021 annual averages, for the GCAM currency base
