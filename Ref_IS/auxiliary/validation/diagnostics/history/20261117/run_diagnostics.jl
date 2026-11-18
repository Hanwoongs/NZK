using MacroDiagnostics
using JSON3
using SHA

# This script scans inputs and writes reports. It does not load MacroEnergy or solve.
# Defaults apply when this script is stored in Ref_IS/auxiliary/validation/diagnostics/.
const ROOT = isempty(ARGS) ? normpath(joinpath(@__DIR__, "..", "..", "..", "..")) : abspath(ARGS[1])
const REPORTS = length(ARGS) < 2 ? (@__DIR__) : abspath(ARGS[2])
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
new_asset(id) = startswith(id, "steel_") || startswith(id, "electrolyzer_steel_")
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
    new_checks = filter(c -> new_asset(c.asset_id), result.asset_constraints.checks)
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
        "asset_check_states" => histogram(c.state for c in result.asset_constraints.checks),
        "new_asset_check_states" => histogram(c.state for c in new_checks),
        "new_asset_blocked_checks" => [Dict(string(f) => getfield(c, f) for f in fieldnames(typeof(c)))
                                       for c in new_checks if occursin("blocked", string(c.state))],
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
            " states=", summary["asset_check_states"]); flush(stdout)
end

baseline = warning_keys(summaries["Ref"], "Ref")
candidate = warning_keys(summaries["Ref_IS"], "Ref_IS")
added = Dict(k => n - get(baseline, k, 0) for (k, n) in candidate if n > get(baseline, k, 0))
removed = Dict(k => n - get(candidate, k, 0) for (k, n) in baseline if n > get(candidate, k, 0))
new_summary = summaries["Ref_IS"]
passed = isempty(added) && isempty(new_summary["new_asset_blocked_checks"]) &&
       get(new_summary["new_asset_check_states"], "checked", 0) > 0 &&
       all(new_summary[key] == "confirmed" for key in
           ("node_source_status", "asset_source_status", "asset_constraint_source_status"))
comparison = Dict("passed" => passed, "baseline_warning_error_count" => sum(values(baseline); init=0),
    "candidate_warning_error_count" => sum(values(candidate); init=0), "added_findings" => added,
    "removed_findings" => removed, "new_asset_check_states" => new_summary["new_asset_check_states"],
    "new_asset_blocked_count" => length(new_summary["new_asset_blocked_checks"]),
    "method" => "Multiset difference of severity, code, source and message; only case-root paths normalized.",
    "optimization_performed" => false)
write_json("diagnostics_comparison.json", comparison)
println("DIAGNOSTICS_PASS=", passed, " added=", sum(values(added); init=0),
        " new_blocked=", comparison["new_asset_blocked_count"])
passed || error("Ref_IS introduced diagnostic findings or blocked checks; inspect reports.")
