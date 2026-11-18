# Ref and Ref_IS diagnostic reports

We reran MACRO Diagnostics on the current clone on November 17, 2026. Both cases used the same standard rc1 source, including the Storage output fix prepared by `Ref_IS/auxiliary/setup.jl`. This was a static scan; no model was solved.

## Open a report

The filenames include the case name, so they stay easy to identify when copied or downloaded separately.

| Report | Ref baseline | Ref_IS with steel |
| --- | --- | --- |
| Topology | [Ref_topology-diagnostics.html](Ref_topology-diagnostics.html) | [Ref_IS_topology-diagnostics.html](Ref_IS_topology-diagnostics.html) |
| Nodes | [Ref_nodes-diagnostics.html](Ref_nodes-diagnostics.html) | [Ref_IS_nodes-diagnostics.html](Ref_IS_nodes-diagnostics.html) |
| Assets | [Ref_assets-diagnostics.html](Ref_assets-diagnostics.html) | [Ref_IS_assets-diagnostics.html](Ref_IS_assets-diagnostics.html) |

All six files are the tool's detailed English HTML reports. They can be opened directly in a browser. Paths shown in them describe the computer used for this scan.

## What we found

| Case | Errors | Warnings |
| --- | ---: | ---: |
| Ref | 0 | 979 |
| Ref_IS | 0 | 979 |

These totals include all three diagnostic modules and all periods; they are not counts of unique underlying issues. The comparison found no added warning/error findings after steel integration. We left the existing Ref warnings in place.

We compared the severity, code, source, and full message, including repeated occurrences. Only the case-root paths were normalized for this comparison. There were 34,493 completed checks for the added steel and electrolyzer assets, with 0 blocked checks for those assets.

Retrofit coverage still needs care. `RETROFIT_SETTING_UNCONFIRMED` appeared 7 times for Ref_IS, so these reports do not establish complete retrofit coverage. The small synthetic tests and successful local TDR run provide separate execution evidence.

## Details and rerunning

- Tool: MacroDiagnostics 0.1.2, run with Julia 1.11.3.
- Model source: standard MacroEnergy 0.3.0-rc1 from `Ref_IS/auxiliary/.runtime/MacroEnergy_rc1`, with the separate Storage output fix.
- Model run environment: Julia 1.13.1. The diagnostic tool uses its own environment and does not change it.
- Machine-readable findings: [Ref](Ref_scan_summary.json), [Ref_IS](Ref_IS_scan_summary.json), and [the comparison](diagnostics_comparison.json).
- Input and report hashes: the scan summaries and [diagnostics_manifest.json](diagnostics_manifest.json).

To rerun with the same diagnostic tool installed, run this command from the NZK repository root:

```text
julia --startup-file=no --project="<MacroDiagnostics project directory>" Ref_IS/auxiliary/validation/diagnostics/run_diagnostics.jl
```

Use the tool's compatible Julia environment; this scan used Julia 1.11.3 and the 0.1.2 project. Run `Ref_IS/auxiliary/setup.jl` first if the extracted model source is missing. The script scans both cases and writes the six explicitly named HTML files, two scan summaries, and the comparison. It does not solve. This README and the delivery hash manifest describe the recorded scan; update them when sharing new results.

See [the case README](../../../README.md) for the steel scope, local TDR results, and parameterization work still needed.
