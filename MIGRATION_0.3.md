# repo_runs on MacroEnergy release-0.3

Created 2026-10-19. This folder is **the `repo_runs` cases running on
MacroEnergy 0.3.0-rc1** instead of the 0.1-era fork they were built against.

```
~/Desktop/repo_runs          the working copy, still on the 0.1 fork — untouched
~/Desktop/NZK_Della_repo     the 0.1 fork package, branch NZK_Della — untouched
~/Desktop/NZK_MACRO_v03      this folder, branch NZK_release03
```

It is a git worktree of `NZK_Della_repo`, so all three share one `.git` and
nothing in the other two was modified.

## What is here

**The package** — upstream `macroenergy/MacroEnergy.jl`, branch `release-0.3`,
version **0.3.0-rc1**.

**The cases** — everything from `repo_runs`:

```
Ref/  NDC/                        the two run cases
Post-processing files/            transmission, demand, provincial CF, BNEF
figures/                          diagnostic charts and their scripts
20251205 BNEF Korea data .xlsx
NZK_MODEL_README.md               repo_runs/README.md, renamed so it does not
                                  collide with the package's own README.md
```

**Excluded:** `Ref_re/` and `NDC_Re/`, 5 GB each of results from the 0.1 run,
and the two October `_backup_*` folders of pre-edit asset CSVs. Both still
exist in `repo_runs`, and the input changes the backups covered are written up
with before and after values in `Post-processing files/BNEF/README.md`. This
folder is 462 MB.

**Also carried over** from the fork: 11 custom asset files
(`be_hefa`, `beccsammonia`, `beccsatj`, `beccsbiomethane`, `beccscharcoal`,
`beccsdiesel`, `beccsethanol`, `biomassharvest`, `biomasstransformation`,
`fischertropsch`, `fuelsenduse_generalized`) and the three commodities they
need — `Charcoal`, `Biomethane`, `Pollution` — added to `src/MacroEnergy.jl`
and marked `# ESAG fork`.

Ref and NDC do not use any of them; they use only core types (`ThermalPower`,
`ThermalPowerCCS`, `VRE`, `Battery`, `HydroRes`, `TransmissionLink`,
`CO2Injection`). They are kept because BECCS is on the model backlog. They
compile and load. Their Julia type names are `BECCSATJ` and `HEFA`, not
`BECCSAtj` / `BEHefa`.

## Where the old package stood

`NZK_Della_repo` is a fork, `joonmoon6409/MacroEnergy-ESAG.jl`, not the
official repo. Its `Project.toml` says `version = "0.1.0"`, but that is a
string the fork never bumped. The real code vintage is upstream PR #244 —
**445 commits behind release-0.3**.

| | version |
|---|---|
| the fork, declared | 0.1.0 (meaningless) |
| the fork, actual | upstream PR #244 |
| upstream release-0.2 | 0.2.5 |
| **here** | **0.3.0-rc1** |

`release-0.3` is a release *candidate*, not a final release.

## Julia

**1.12.1, matching the cluster** (`module load julia/1.12.1`). Installed with
`juliaup add 1.12.1`. Run everything here as `julia +1.12.1` — the local
default is still 1.9.4.

0.3 **will not build on 1.9.4**; `MacroEnergyTimeReduction 0.0.2` requires
newer. The old fork still builds on 1.9.4, so both keep working.

## Verified

- `Pkg.instantiate()` resolves on 1.12.1 — 242 dependencies precompiled
- `using MacroEnergy` loads, reports 0.3.0-rc1
- all 7 core and all 11 fork asset types are defined
- **`load_case("Ref")` and `load_case("NDC")` both succeed, 7 periods each**

The current inputs load unchanged. No input migration was needed.

## Load time, measured

Same machine, same `Ref` inputs, same function:

| | `load_case` |
|---|---|
| 0.1 fork, Julia 1.9.4 | **369.1 s** |
| 0.3, Julia 1.12.1 | **18.8 s** |

**19.6× faster.** This matches the changelog entry: *"Cached repeated reads of
shared CSV inputs within each case or system load, avoiding repeated full-file
parsing when assets select different columns from the same file."* Our case is
exactly that shape — 51 VRE assets each reading different columns out of one
8,760 × 59 `availability.csv`, 17 demand columns out of one demand file.

Where the 2 h 30 m Ref run on the cluster actually went:

| stage | time | share | does 0.3 help |
|---|---|---|---|
| loading | 16 m 54 s | 11% | **yes, measured** |
| model generation | ~29 m | 19% | claimed, not measured |
| scaling + solve + write | ~94 m | 62% | barely — this is Gurobi |

Optimistically that is 2 h 30 m → about 2 h. Real, but not transformative:
**the solve dominates and 0.3 cannot change it.** The thing that would is TDR
(new in 0.3), which replaces 8,760 hours with weighted representative periods —
but that changes the model, so results would no longer be comparable to the
chronological runs.

## What 0.3 gives us that we needed

**Grouped `MaxNewCapacityConstraint`.** From the changelog:

> system-wide and per-location capacity constraints for selected groups of
> assets ... `MaxNewCapacityConstraint` bounds newly built capacity. Limits are
> configured via a `constraints` block in `system_data.json` (whole system) or
> per location in `locations.json`, using **asset-type and tag selectors**.

and for VRE, `technology: "Solar"` is normalised into a `:solar` tag.

This removes the workaround we are stuck with on 0.1, where the constraint is
per-asset so a national solar build limit cannot be written. The per-province
cap relocates build rather than limiting it — tightening 7,500 → 6,000 MW moved
the national peak only 6.5 → 6.0 GW/yr, and Ref 2050 solar went *up*,
139 → 142 GW.

Also worth noting:

- `capacity_summary.csv` — multi-period capacity in one file
- `capex.csv` — per-component capital cost
- `StartYear` in `case_settings.json` — label periods by calendar year
- **Fixed:** `StorageChargeLimitConstraint` was declared at the wrong level in
  a `Battery`'s charge edge and was *silently dropped*. It now binds. This may
  change our battery results.
- **Fixed:** myopic runs with `ReturnModels = false` now actually free each
  period's model — a memory fix, relevant given our 192 GB runs.

## The run scripts

Both cases carry their full run set, unchanged from `repo_runs`:

```
run_v1_BNEF.jl              the actual run script
run_NZK_della.slurm         the existing one, points at the 0.1 cluster path
run_NZK_della_v03.slurm     added here, points at a new 0.3 cluster path
run_HiGHS.jl  run_with_env.jl
```

alongside `assets/`, `system/`, `settings/`, `user_additions/`,
`system_data.json` and `input.xlsx`.

**One change was needed.** `run_case` returns something different in 0.3:

| | returns |
|---|---|
| 0.1 | `case.systems, solution` |
| 0.3 | `case, solution` |

The script bound this as `(system, model)`, which on 0.3 would silently put a
`Case` into a variable named `system`. It would not have errored — the script
never uses the returned values — but it would have been wrong to read. Both
scripts now bind `(case, solution)`.

Every keyword the script passes (`lazy_load`, `optimizer`,
`optimizer_attributes`) is still accepted by 0.3.

## Running on the cluster

`Ref/run_NZK_della_v03.slurm` and `NDC/run_NZK_della_v03.slurm` are copies of
the existing scripts with the job name suffixed `_v03` and

```
REPO="/scratch/gpfs/JENKINS/hk6264/MacroEnergy_NZK_v03"
```

so the 0.3 package lands in a new directory and the existing
`MacroEnergy_NZK` is left alone. Upload this whole folder there. The original
`run_NZK_della.slurm` files are untouched.

## Not yet done

- **Run a case end to end.** Loading proves the schema parses. It does not
  prove the model builds, solves, or returns the same answer.
- Compare a full Ref solve against the 0.1 result. Do this before the
  base-year fixes land, or the two changes cannot be told apart.
- Rewrite the solar build-rate limit using the grouped constraint.
- Check whether `StorageChargeLimitConstraint` now binding changes battery
  results.
- Test on the cluster. The Julia version matches, but Gurobi there is
  `gurobi/13.0.0` and has not been tried.

## Reproduce

```bash
cd ~/Desktop/NZK_MACRO_v03
julia +1.12.1 --project=. -e 'using Pkg; Pkg.instantiate()'
julia +1.12.1 --project=. -e 'using MacroEnergy; MacroEnergy.load_case("Ref")'
```
