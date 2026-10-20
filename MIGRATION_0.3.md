# Migration to MacroEnergy release-0.3

Created 2026-10-19 as a git worktree of `NZK_Della_repo`, on a new branch
`NZK_release03` based on `upstream/release-0.3`.

```
~/Desktop/NZK_Della_repo    branch NZK_Della       unchanged, still works
~/Desktop/NZK_MACRO_v03     branch NZK_release03   this folder
```

Both share one `.git`. Nothing in the old folder was modified.

## Where we came from

The old repo is a fork, `joonmoon6409/MacroEnergy-ESAG.jl`, not the official
`macroenergy/MacroEnergy.jl`. Its `Project.toml` says `version = "0.1.0"`, but
that is just a string the fork never bumped. The real code vintage is upstream
PR #244, which is **445 commits behind release-0.3**.

| | version |
|---|---|
| old repo, declared | 0.1.0 (meaningless) |
| old repo, actual | upstream PR #244 |
| upstream release-0.2 | 0.2.5 |
| **this folder** | **0.3.0-rc1** |

`release-0.3` is a release *candidate*, not a final release.

## What was carried over

**Case data** — every NZK and ExampleSystems folder, plus `0718_techno_params`,
`TDR_script`, `test.jl`, `test_system_output.json`.

`results_*` directories were **excluded**: 1.3 GB of stale run output in
`NZK_power provincial_0908_BNEF` alone, all regenerable. The folder went from
1.4 GB to 178 MB, and the whole copy is 357 MB.

**Fork source** — 11 custom asset files that exist only in the fork:

```
be_hefa  beccsammonia  beccsatj  beccsbiomethane  beccscharcoal
beccsdiesel  beccsethanol  biomassharvest  biomasstransformation
fischertropsch  fuelsenduse_generalized
```

and three commodities they need, which 0.3 does not declare: `Charcoal`,
`Biomethane`, `Pollution`. Both were added to `src/MacroEnergy.jl`, marked
`# ESAG fork`. No upstream file was otherwise modified — the fork's only change
to shared code was `include` lines, so there was nothing to merge by hand.

The NZK power model does not use any of these 11. It uses only core types:
`ThermalPower`, `ThermalPowerCCS`, `VRE`, `Battery`, `HydroRes`,
`TransmissionLink`, `CO2Injection`.

## Verified

- `Pkg.instantiate()` resolves — 215 dependencies precompiled
- `using MacroEnergy` loads, reports 0.3.0-rc1
- all 7 core asset types and all 11 fork asset types are defined
- **`load_case` on the current `repo_runs/Ref` succeeds, all 7 periods**

That last one is the important result: the live NZK inputs load unchanged
under 0.3. No input migration was needed to get that far.

## Julia version

**0.3 will not build on Julia 1.9.4.** `MacroEnergyTimeReduction 0.0.2`
requires newer. Built and tested here on **1.10.5** (`julia +release`).
The cluster runs `julia/1.12.1`, which is newer still, so it should be fine —
but it has not been tested there.

The old `NZK_Della` branch still builds on 1.9.4.

## What 0.3 brings that we wanted

**Grouped `MaxNewCapacityConstraint` exists.** From
`src/model/constraints/max_new_capacity.jl`:

> Typed payload for a **system-wide or location-level** `MaxNewCapacityConstraint`.
> `groups` contains `GroupConfig` entries whose `value` is an upper bound on
> **the sum of newly built capacity**.

with `add_model_constraint!` methods for both `::System` and `::Location`.

This is the single thing most blocking us: on 0.1 the constraint is per-asset,
so a national solar build-rate limit cannot be expressed, and the per-province
workaround relocates build rather than limiting it (7,500 → 6,000 MW moved the
national peak only 6.5 → 6.0 GW/yr, and Ref 2050 solar went *up*, 139 → 142 GW).

## Not yet done

- Run the case end to end, not just load it. Loading proves the schema parses;
  it does not prove the model builds or that results match.
- Compare a full Ref solve against the 0.1 result, so any difference can be
  attributed to the version rather than to the base-year fixes now in flight.
- Rewrite the solar build-rate limit to use the grouped constraint.
- Test on the cluster under `julia/1.12.1`.
- Decide whether to keep the 11 fork assets at all. They compile, but nothing
  in the NZK power model uses them.

## Reproduce

```bash
cd ~/Desktop/NZK_MACRO_v03
julia +release --project=. -e 'using Pkg; Pkg.instantiate()'
julia +release --project=. -e 'using MacroEnergy; println(pkgversion(MacroEnergy))'
```
