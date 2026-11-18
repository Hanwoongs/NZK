using MacroDiagnostics
using JSON3
using SHA
using Dates
include(joinpath(@__DIR__, "coverage_summary.jl"))

# This script scans inputs and writes reports. It does not load MacroEnergy or solve.
# Defaults apply when this script is stored in Ref_IS/auxiliary/validation/diagnostics/.
const ROOT = isempty(ARGS) ? normpath(joinpath(@__DIR__, "..", "..", "..", "..")) : abspath(ARGS[1])
const REPORTS = length(ARGS) < 2 ? joinpath(@__DIR__, "runs", Dates.format(now(), "yyyymmdd_HHMMSS")) : abspath(ARGS[2])
ispath(REPORTS) && (!isdir(REPORTS) || !isempty(readdir(REPORTS))) && error("Use a new, empty report directory; saved reports must be preserved.")
const SOURCE = joinpath(ROOT, "Ref_IS", "auxiliary", ".runtime", "MacroEnergy_rc1")
isfile(joinpath(SOURCE, "src", "MacroEnergy.jl")) || error("Run Ref_IS/auxiliary/setup.jl before diagnostics")
mkpath(REPORTS)

histogram(values) = begin
    counts = Dict{String,Int}()
    for value in values
        key = string(value)
        counts[key] = get(counts, key, 0) + 1
    end
    counts
end
file_sha(path) = bytes2hex(open(SHA.sha256, path))
function findings(messages)
    Dict("severity_counts" => histogram(m.severity for m in messages),
         "code_counts" => histogram(m.code for m in messages),
         "messages" => [Dict("severity" => string(m.severity), "code" => m.code,
                            "message" => m.message, "source" => m.source) for m in messages])
end
function normalize(text, name)
    value = string(text)
    for path in (joinpath(ROOT, name), replace(joinpath(ROOT, name), '\\' => '/'))
        value = replace(value, path => "<CASE>")
    end
    value
end
function warning_keys(summary, name)
    keys = String[]
    for section in ("topology", "nodes", "assets"), m in summary[section]["messages"]
        lowercase(m["severity"]) in ("warning", "error") || continue
        push!(keys, join([section, m["severity"], m["code"],
            normalize(m["source"], name), normalize(m["message"], name)], " | "))
    end
    histogram(keys)
end
function write_json(name, data)
    open(joinpath(REPORTS, name), "w") do io
        JSON3.pretty(io, data)
        println(io)
    end
end
function input_hashes(name)
    base = joinpath(ROOT, name)
    hashes = Dict{String,String}()
    for folder in ("assets", "system", "settings", "user_additions")
        path = joinpath(base, folder)
        isdir(path) || continue
        for (directory, _, files) in walkdir(path), file in files
            full = joinpath(directory, file)
            hashes[replace(relpath(full, base), '\\' => '/')] = file_sha(full)
        end
    end
    hashes["system_data.json"] = file_sha(joinpath(base, "system_data.json"))
    hashes
end

summaries = Dict{String,Any}()
for name in ("Ref", "Ref_IS")
    println("SCAN_START ", name); flush(stdout)
    before = input_hashes(name)
    result = scan_case(joinpath(ROOT, name); macroenergy_path=SOURCE,
                       node_diagnostics=true, asset_diagnostics=true)
    coverage = added_asset_coverage(result)
    summary = Dict(
        "case" => name, "source" => SOURCE,
        "diagnostics_version" => string(Base.pkgversion(MacroDiagnostics)),
        "diagnostics_package" => pathof(MacroDiagnostics), "julia_version" => string(VERSION),
        "scan_seconds" => result.scan_elapsed_seconds,
        "node_count" => length(result.node_inventory), "asset_count" => length(result.asset_inventory),
        "connection_count" => length(result.topology_inventory),
        "schema_status" => string(result.macroenergy_schema_status),
        "node_source_status" => string(result.node_diagnostics.source_status),
        "asset_source_status" => string(result.asset_diagnostics.source_status),
        "asset_constraint_source_status" => string(result.asset_constraints.source_status),
        "node_coverage_notes" => result.node_diagnostics.coverage_notes,
        "asset_constraint_notes" => result.asset_constraints.notes,
        "asset_assessment_summary" => public_assessment_summary(result),
        "added_asset_assessments" => coverage,
        "input_sha256" => before,
        "topology" => findings(result.messages),
        "nodes" => findings(result.node_diagnostics.messages),
        "assets" => findings(result.asset_diagnostics.messages))
    summaries[name] = summary
    write_json("$(name)_scan_summary.json", summary)
    for diagnostic in (:topology, :nodes, :assets)
        # Use explicit names so a report remains identifiable outside this folder.
        filename = "$(name)_$(diagnostic)-diagnostics.html"
        write_html_report(result, joinpath(REPORTS, filename);
                          diagnostic, language=:en, detail=true)
    end
    before == input_hashes(name) || error("Input files changed during the scan: $name")
    println("SCAN_DONE ", name, " assets=", summary["asset_count"],
            " coverage=", coverage["coverage"]); flush(stdout)
end

baseline = warning_keys(summaries["Ref"], "Ref")
candidate = warning_keys(summaries["Ref_IS"], "Ref_IS")
added = Dict(k => n - get(baseline, k, 0) for (k, n) in candidate if n > get(baseline, k, 0))
removed = Dict(k => n - get(candidate, k, 0) for (k, n) in baseline if n > get(candidate, k, 0))
new_summary = summaries["Ref_IS"]
coverage = new_summary["added_asset_assessments"]
source_confirmed = all(new_summary[key] == "confirmed" for key in
    ("node_source_status", "asset_source_status", "asset_constraint_source_status"))
passed = isempty(added) && coverage["coverage_resolved"] && source_confirmed
comparison = Dict("passed" => passed,
    "no_new_warning_error_findings" => isempty(added),
    "added_asset_coverage_resolved" => coverage["coverage_resolved"],
    "source_confirmed" => source_confirmed,
    "baseline_warning_error_count" => sum(values(baseline); init=0),
    "candidate_warning_error_count" => sum(values(candidate); init=0),
    "added_findings" => added, "removed_findings" => removed,
    "added_asset_coverage" => coverage["coverage"], "added_asset_outcomes" => coverage["outcome"],
    "added_asset_incomplete_check_count" => length(coverage["incomplete_checks"]),
    "added_asset_missing_inventory_records" => coverage["missing_inventory_records"],
    "unmapped_asset_check_records" => coverage["unmapped_asset_check_records"],
    "method" => "Warning/error multiset comparison plus public assessment coverage; only case-root paths normalized.",
    "optimization_performed" => false)
write_json("diagnostics_comparison.json", comparison)
write_json("run_manifest.json", Dict("created_at" => string(now()), "output_directory" => REPORTS,
    "collector_sha256" => file_sha(@__FILE__),
    "coverage_helper_sha256" => file_sha(joinpath(@__DIR__, "coverage_summary.jl")),
    "historical_reports_overwritten" => false, "optimization_performed" => false))
println("DIAGNOSTICS_PASS=", passed, " added=", sum(values(added); init=0),
        " incomplete=", comparison["added_asset_incomplete_check_count"], " reports=", REPORTS)
passed || error("Diagnostic acceptance is incomplete; inspect findings and public coverage records in $REPORTS.")
