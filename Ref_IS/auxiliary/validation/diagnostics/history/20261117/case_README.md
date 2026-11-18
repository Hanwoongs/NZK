# Ref_IS: adding iron and steel to NZK

Updated November 17, 2026.

We have added six steel production routes and three retrofit options to the Della_1019 Ref case. The main connections are in place, including electricity, hydrogen, raw materials, steel demand, and CO₂. The next step is to replace the test inputs with Korean data.

**We ran a local TDR version through all seven Myopic periods, and every period reported `OPTIMAL`.** The full-resolution Ref_IS case also loads successfully, but we have not solved it. The industrial parameters are still placeholders, so the results should not yet be used as a Korea steel assessment.

## What we added

We started from the existing Ref case and kept its power-system inputs. Ref_IS uses the same 17 regions and seven periods: 2021, 2025, 2030, 2035, 2040, 2045, and 2050. The case in this folder keeps all 8,760 hours per period and the existing Monolithic/Myopic settings.

All six routes can be built once they become available:

| Steel route | First available year | Starting capacity per region in 2021 | Can also be retrofitted from |
| --- | --- | --- | --- |
| BF–BOF | 2021 | 0.5 t/h | — |
| BF–BOF–CCS | 2030 | Zero | BF–BOF |
| NG–DRI–EAF | 2021 | 0.25 t/h | — |
| NG–DRI–EAF–CCS | 2030 | Zero | NG–DRI–EAF |
| H₂–DRI–EAF | 2021 | Zero | NG–DRI–EAF |
| Scrap–EAF | 2021 | 0.25 t/h | — |

These starting capacities and dates are test assumptions. In particular, the NG–DRI–EAF starting capacity does not represent confirmed Korean capacity. We also allow the H₂ route from 2021 for this template. Both assumptions need review during parameterization.

The retrofit connections are:

```text
BF–BOF     → BF–BOF–CCS
NG–DRI–EAF → NG–DRI–EAF–CCS
NG–DRI–EAF → H₂–DRI–EAF
```

New builds and retrofit destinations are separate asset instances. A retrofit uses capacity from its source route. The two NG–DRI–EAF retrofit options share that available source capacity. Myopic runs carry solved capacities into the next period, so we only enter the starting capacities in 2021.

## How the steel sector connects to the rest of the model

- **Electricity:** steel and electrolysis use the existing `elec_<REGION>` nodes. We adapted the non-CCS BF–BOF asset so that it consumes electricity. The two custom definitions, `BFBOFSteel` and `BFBOFSteel_CCS`, are in `user_additions/assets/`.
- **DRI–EAF:** the NG and H₂ routes have no scrap input edge, following the agreed scope.
- **Hydrogen:** we added an electrolyzer and an `h2_<REGION>` node in each region. This completes the connection for the H₂ steel route; its efficiency and costs still need Korean inputs.
- **Raw materials:** iron ore and scrap come from national fixed-price supply nodes. Coal and natural gas use the existing Ref supply nodes.
- **Steel demand:** each region has a `crudesteel_<REGION>` node. Annual net supply must meet or exceed demand through `AggregatedDemandConstraint`. We do not impose a fixed hourly steel demand profile.
- **CCS:** steel CCS becomes available from 2030 and connects to the existing `co2_captured_KR` network. Residual emissions go to `co2_sink_KR`.
- **Operation:** we enabled minimum-flow and ramping constraints. Minimum flow is currently 0.0, and both hourly ramp fractions are 1.0. These are permissive placeholders.

Scrap has a national allowance of 85,000 t/year, divided by 8,760 and used as an hourly supply cap. This limits how much scrap can be used in each hour. A flexible annual scrap limit remains future work.

We kept the original Ref assets, node records, electricity demand, and CO₂ budgets. Ref_IS adds the industrial records, enables `Retrofitting=true`, and adds the required commodity and time-data entries. Other Ref settings remain unchanged, including period lengths and the 4.5% discount rate. The rc1 default for `WriteFullTimeseries` is `false`.

This handover covers steel and the connections it needs. Heat-sector integration and power-system adequacy are outside the work completed here.

## What still needs data

The values to update are collected in [auxiliary/template/config.json](auxiliary/template/config.json). They are marked `SYNTHETIC_PLACEHOLDER_NOT_KOREA_CALIBRATION`.

| Item | What is there now | What we need next |
| --- | --- | --- |
| Steel demand | 10,000 t/year per region in every period | Demand by region and period. |
| Starting capacity | The route capacities shown above, repeated across regions | Actual capacities, ages, and retirement assumptions. |
| Scrap | 85,000 t/year nationally, converted to an hourly cap | An agreed allowance and, later, a decision on a flexible annual limit. |
| Material prices | Iron ore: 100 per t; scrap: 300 per t | Korean prices and an agreed currency year. |
| Process inputs and emissions | Test material, energy, and CO₂ coefficients | Route-specific coefficients and capture quantities. |
| Costs and lifetimes | Test investment costs, fixed costs, and lifetimes | Agreed costs, lifetime, and capital recovery assumptions. |
| Hydrogen | Electrolysis efficiency of 0.7 and test costs | The hydrogen supply boundary, efficiency, costs, and heating-value basis. |
| Availability | Common settings across regions; steel CCS starts in 2030 | The regions and years in which each option should be available. |

Two system boundaries also need attention. Steel and electrolysis add electricity demand, while the original Ref demand is still present. We will need to remove any overlapping industrial load. We also need to agree on how industrial emissions enter future CO₂ budgets.

For units, steel capacity is in t/h. Iron ore and scrap coefficients are t/t steel; energy inputs are MWh/t steel. Investment cost is currency/(t/h), and fixed cost is currency/(t/h)/year. `emission_rate` and `capture_rate` are t CO₂/t steel, not percentages. Electrolyzer capacity is MW of hydrogen output.

## Getting started

Use Julia **1.13.1**, which is the version we tested. Python **3.11 or later** is needed only for regeneration and structural checks. The Python scripts do not need extra libraries.

From the NZK repository root, run:

```text
julia --startup-file=no Ref_IS/auxiliary/setup.jl
julia --startup-file=no Ref_IS/auxiliary/check_load.jl
```

Setup prepares the source and installs the recorded Julia dependencies. It may need internet access the first time. The second command loads all seven periods and checks the assets and connections. It does not create an optimizer or solve the model. Use a fresh Julia process for each command.

If the dependencies are already cached, `setup.jl --offline` uses them without downloading. `setup.jl --source-only` only prepares the source and environment files; it does not install dependencies.

When we are ready for a full-resolution solve, the command is:

```text
julia --startup-file=no Ref_IS/run.jl
```

This starts an optimization and needs a usable Gurobi license. The settings are `Method=2`, `BarConvTol=1e-3`, and `Crossover=0`, matching the local TDR trial. The final semicolon suppresses display of the returned case and solution. We have not yet tested the memory use or completion of this full-resolution solve.

## Why the source is included as a ZIP

We kept a fixed copy of standard MacroEnergy rc1 in [auxiliary/source/MacroEnergy-0.3.0-rc1.zip](auxiliary/source/MacroEnergy-0.3.0-rc1.zip), so everyone can start from the same source. It contains the runtime files and license, without the ESAG additions. It is not a full upstream repository archive with documentation and tests.

The ZIP stays unmodified. Setup checks its hashes, extracts it into `auxiliary/.runtime/MacroEnergy_rc1/`, and applies the separate [Storage output fix](auxiliary/source/storage_retrofit_output.patch) to that local copy:

```julia
retrofitted_capacity(g::AbstractStorage) = 0.0;
```

Without this accessor, capacity output can fail in a Myopic run with `Retrofitting=true` when storage is present. We tested the fix with `Storage` and `LongDurationStorage`, and used it in the successful TDR run. It changes an output accessor, not the constraint library. We have not tested PF.

Setup also creates an isolated Julia environment under `auxiliary/.runtime/`. The run scripts select it automatically. The repository's original `src/` and `run_env/` remain unchanged. Git ignores the extracted source and local environment; the ZIP, patch, and dependency list stay with the case.

Repeated setup checks the existing files. If it finds unexpected source or environment changes, it stops and preserves them. The source hashes and provenance details are in [auxiliary/source/source_manifest.toml](auxiliary/source/source_manifest.toml).

## Where to make changes

The top level keeps the usual model files and the run entry point. Setup, source, parameters, and validation records are grouped under `auxiliary/`.

```text
Ref_IS/
  assets/, system/, settings/   model inputs
  user_additions/assets/       custom BF–BOF definitions
  system_data.json             case definition
  run.jl                       start the full-resolution solve
  README.md                    this handover
  auxiliary/
    setup.jl                   prepare the local runtime
    check_load.jl              check the case without solving
    runtime.jl                 shared source and environment checks
    template/                  parameters, generator, and validator
    source/                    rc1 ZIP, Storage patch, and source notes
    environment/               recorded Julia dependency files
    validation/                check results and provenance
    template_manifest.json     generated-input and source hashes
    .runtime/                  generated locally; ignored by Git
```

For permanent parameter changes, edit `auxiliary/template/config.json`. Then run:

```text
python -B Ref_IS/auxiliary/template/build_template.py
python -B Ref_IS/auxiliary/template/build_template.py --check
python -B Ref_IS/auxiliary/template/validate_template.py
julia --startup-file=no Ref_IS/auxiliary/check_load.jl
```

The generator reads the sibling `Ref/` baseline and the prepared rc1 source. It updates the model inputs and custom assets. It leaves this README, the setup scripts, the ZIP, and the dependency files alone.

The generator will stop if it would overwrite a manually edited generated file. Keeping permanent changes in the configuration makes regeneration easier. More detailed regional or time variation may require extending the generator. It normalizes text line endings so Windows and Linux checkouts can reproduce the same inputs; this does not change model values.

## What we have tested

### The local TDR run

We used **24 representative 48-hour periods per model period**, or 1,152 representative hours. The 48-hour duration retained the existing 36-hour nuclear minimum up/down constraints. The time weights represent a full year.

All seven Myopic periods reported `OPTIMAL`, with an overall run status of `OK`. The recorded elapsed time was 1,286.261 seconds, including setup and output. That is the result from our local test, not a runtime estimate for another computer or the full-resolution case.

We also checked the steel results:

- All 782 matched capacity carry-over comparisons agreed in the exported values.
- All three retrofit links had positive additions. The shared source limits held, and source/target mismatches were below 1.1e-16 t/h.
- Steel CCS became available from 2030 as intended.
- All 119 region-period annual steel-demand lower bounds were met.
- The largest steel capacity accounting residual was 8.63e-5 t/h under the selected solver settings. We have not tested tighter tolerances.

This gives us evidence that the steel routes and retrofit connections can run with the current test inputs. Korean parameter calibration and comparison with a full-resolution solve are still ahead of us. The TDR case and its results are not included in this folder.

### The full-resolution template and setup

The case in this clone passed setup, regeneration, structural validation, and loading of all seven periods. We confirmed that it uses the extracted rc1 source with the Storage fix. No optimizer was created during these checks.

We also compared all 139 model files with the earlier clean delivery. The only byte differences were line-ending normalization; model values and structure were unchanged. The original Ref and NDC files remain unchanged.

Earlier small synthetic tests covered routes, new builds, flow equations, retrofits, electrolysis, ramping, and aggregate demand. We reran MACRO Diagnostics on this clone. Both cases had 979 warnings and zero errors, with no added warning/error findings from steel integration. See [the Ref and Ref_IS reports](auxiliary/validation/diagnostics/README.md). Retrofit diagnostics were unavailable in all seven periods, so that part of the tool's coverage remains incomplete.

Inherited messages about optional locations, Myopic defaults, and default time weights may still appear. We have not suppressed them. Full-resolution optimization, PF, and a TDR/full-resolution comparison have not been tested.

The detailed records are available in the [load check](auxiliary/validation/load_check.json), [static checks](auxiliary/validation/static_integration_checks.json), and [setup checks](auxiliary/validation/setup_checks.json). The next modeling task is to replace the placeholders and settle the electricity-demand and CO₂-accounting boundaries.
