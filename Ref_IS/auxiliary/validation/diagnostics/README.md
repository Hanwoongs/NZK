# Ref and Ref_IS diagnostic reports

Updated November 18, 2026. The latest targeted scan passed with a MacroDiagnostics 0.1.2 repair candidate and the project's standard MacroEnergy 0.3.0-rc1 source.

The repair has now passed the relevant regression tests and is installed in both local v0.1.2 maintenance copies. Both source trees exactly match the version tested in the latest NZK scan, so no repeat scan is needed. See [the final acceptance record](tool_acceptance_20261118.json). This is a local source repair, not a new official release; the full default test suite was not rerun.

## Latest reports: November 18

| Report | Ref baseline | Ref_IS with steel |
| --- | --- | --- |
| Topology | [Ref](runs/20261118_steel_parser_candidate_02/Ref_topology-diagnostics.html) | [Ref_IS](runs/20261118_steel_parser_candidate_02/Ref_IS_topology-diagnostics.html) |
| Nodes | [Ref](runs/20261118_steel_parser_candidate_02/Ref_nodes-diagnostics.html) | [Ref_IS](runs/20261118_steel_parser_candidate_02/Ref_IS_nodes-diagnostics.html) |
| Assets | [Ref](runs/20261118_steel_parser_candidate_02/Ref_assets-diagnostics.html) | [Ref_IS](runs/20261118_steel_parser_candidate_02/Ref_IS_assets-diagnostics.html) |

The filenames include the case name. Each detailed English HTML report opens directly in a browser. Paths in the reports identify the computer used for this scan.

| Case | Errors | Warnings |
| --- | ---: | ---: |
| Ref | 0 | 979 |
| Ref_IS | 0 | 979 |

These totals include all three modules and all periods. They are message counts, not counts of unique underlying issues. The warning/error comparison found no added or removed findings between Ref and Ref_IS. It compares severity, code, source, and full message, including repeated occurrences. Only case-root paths are normalized.

The public assessment APIs report the following coverage for the added steel and electrolyzer records:

| Coverage | Check scopes |
| --- | ---: |
| Complete | 35,275 |
| Not applicable | 164,254 |
| Blocked | 0 |
| Partial | 0 |
| Not evaluated | 0 |

The completed scopes have no findings. No added inventory record lacks assessments, and every Asset check maps to a record. “Not applicable” means that the tool confirmed the scope and found no applicable branch. These counts describe the records exposed by this scan; they do not establish coverage outside that inventory.

## What the repair restored

The candidate supports ordinary `process_data(...)` calls in the three native steel factories. The earlier 1,768 blocked and 442 partial P01–P05 scopes are resolved.

All 646 base steel asset × period records now have a confirmed Transformation. This includes the 442 native-steel records whose Transformation was missing from the earlier diagnostic inventory. We checked the `CrudeSteel` time axis, input-field sources, `BalanceConstraint`, and the expected balance count. All 3,723 process-coefficient magnitudes and their input sources match the actual steel inputs. A balance term's sign depends on its side of the equation.

The public API counts and the saved HTML coverage records agree. The 423 protected files, including both cases' inputs, runtime source, and earlier reports, remained unchanged. No model was solved.

Retrofit coverage remains incomplete. `RETROFIT_SETTING_UNCONFIRMED` appears seven times. The diagnostic inventory does not separately include the generated retrofit assets, so zero blocked checks here must not be presented as complete retrofit validation. The earlier synthetic tests and successful seven-period Myopic TDR run provide separate execution evidence.

## Records and reproducibility

- [Comparison](runs/20261118_steel_parser_candidate_02/diagnostics_comparison.json) and [acceptance review](runs/20261118_steel_parser_candidate_02/acceptance_review.json).
- Scan summaries: [Ref](runs/20261118_steel_parser_candidate_02/Ref_scan_summary.json) and [Ref_IS](runs/20261118_steel_parser_candidate_02/Ref_IS_scan_summary.json).
- [Steel component evidence](runs/20261118_steel_parser_candidate_02/Ref_IS_steel_components.json) records the restored transformations and parameter sources.
- [Diagnostic source hashes](runs/20261118_steel_parser_candidate_02/diagnostic_source_sha256.json) identify all 177 source files used for this scan.
- [Run manifest](runs/20261118_steel_parser_candidate_02/run_manifest.json) identifies the executed collector and coverage helper. Their copies are in the same directory.

The scan used Julia 1.11.3 and an unchanged snapshot of the repair candidate. MacroEnergy came from `Ref_IS/auxiliary/.runtime/MacroEnergy_rc1`, including the separate Storage output fix. The model run environment uses Julia 1.13.1.

To rerun from the NZK repository root, select a compatible diagnostic project that includes this repair:

```text
julia --startup-file=no --project="<MacroDiagnostics project directory>" Ref_IS/auxiliary/validation/diagnostics/run_diagnostics.jl
```

Run `Ref_IS/auxiliary/setup.jl` first if the extracted model source is missing. The collector uses `assessment_summary`, `check_ids`, and `check_assessment`. It counts coverage separately from findings. Missing, partial, blocked, or unevaluated assessments prevent acceptance.

New scans write to a separate timestamped `runs/` directory. The script refuses a nonempty output directory and does not solve. Its optional arguments are the NZK repository root and a new output directory.

## Previous candidate

The latest run includes an additional guard for ordinary `process_data(...)` calls. Unsupported non-Boolean constraint settings retain an unconfirmed status. Our steel inputs use Boolean settings, and the repeated Ref/Ref_IS check gives the same findings and coverage counts.

The [first candidate Asset report](runs/20261118_steel_parser_candidate/Ref_IS_assets-diagnostics.html) and [first candidate comparison](runs/20261118_steel_parser_candidate/diagnostics_comparison.json) remain unchanged. Their source hashes identify the earlier version.

## Earlier reports and correction

The six HTML files and original JSON summaries directly in this directory remain the November 17 scan records. The original [Ref Asset report](Ref_assets-diagnostics.html) and [Ref_IS Asset report](Ref_IS_assets-diagnostics.html) are unchanged.

The earlier statement that no added asset checks were blocked was incorrect. Our collector read the legacy `checks` list and missed branch coverage. The original [comparison](diagnostics_comparison.json) has `new_asset_blocked_count: 0` and `passed: true`; those fields must not be used as evidence of complete coverage. The 0-error/979-warning counts remain valid.

The [dated correction](coverage_review_20261118.json) records 442 affected base steel asset × period records, or 68 different IDs. Another 204 retrofit option × period records use those templates, but are not extra measured blocked records. The original [diagnostics README](history/20261117/README.md) and [collector](history/20261117/run_diagnostics.jl) remain historical copies. The earlier [delivery manifest](diagnostics_manifest.json) still identifies the original reports.

See [the case README](../../../README.md) for the steel scope, local TDR results, and Korean parameterization work still needed.
