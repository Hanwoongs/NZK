# Use public assessment APIs. Legacy check states do not describe full coverage.
using MacroDiagnostics

is_added_asset(id) = startswith(string(id), "steel_") || startswith(string(id), "electrolyzer_steel_")

function public_assessment_summary(scan; diagnostic=:assets)
    summary = assessment_summary(scan; diagnostic)
    Dict("total" => summary.total, "coverage" => summary.coverage,
         "outcome" => summary.outcome, "bases" => summary.bases,
         "by_rule" => [Dict("domain" => string(r.rule.domain), "rule" => r.rule.id,
                           "total" => r.total, "coverage" => r.coverage,
                           "outcome" => r.outcome, "bases" => r.bases) for r in summary.by_rule])
end

function added_asset_coverage(scan;
        owners=Dict((r.period, r.source, r.path) => r.id for r in scan.asset_constraints.records),
        expected=Set((r.period, r.id, r.source) for r in scan.asset_inventory if is_added_asset(r.id)))
    coverage = Dict(string(s) => 0 for s in (:complete, :partial, :blocked, :not_applicable, :not_evaluated))
    outcomes = Dict(string(s) => 0 for s in (:finding, :no_finding, :unknown, :not_applicable))
    by_rule = Dict{String,Dict{String,Int}}()
    seen = Set{Tuple{Int,String,String}}()
    incomplete = Dict{String,Any}[]
    unmapped = Set{Tuple{Int,String,String}}()
    for id in check_ids(scan; diagnostic=:assets)
        owner_key = (id.period, id.source, id.input_path)
        owner = get(owners, owner_key, nothing)
        if owner === nothing
            push!(unmapped, owner_key)
            continue
        end
        is_added_asset(owner) || continue
        push!(seen, (id.period, owner, id.source))
        state = check_assessment(scan, id)
        state === nothing && error("A public check identity has no assessment: $id")
        coverage[string(state.coverage)] += 1
        outcomes[string(state.outcome)] += 1
        rule_counts = get!(() -> Dict(k => 0 for k in keys(coverage)), by_rule, id.rule.id)
        rule_counts[string(state.coverage)] += 1
        if state.coverage in (:blocked, :partial, :not_evaluated)
            push!(incomplete, Dict("period" => id.period, "asset_id" => owner,
                "source" => id.source, "input_path" => id.input_path, "component" => id.component,
                "rule" => id.rule.id, "coverage" => string(state.coverage), "outcome" => string(state.outcome),
                "scope_confirmed" => state.scope_confirmed,
                "reason_ids" => sort!(unique(string(r.id) for r in state.reasons))))
        end
    end
    sort!(incomplete; by=r -> (r["period"], r["asset_id"], r["source"], r["input_path"], r["component"], r["rule"]))
    missing = sort!(collect(setdiff(expected, seen)))
    resolved = !isempty(expected) && isempty(missing) && isempty(unmapped) &&
               isempty(incomplete) && coverage["complete"] > 0
    Dict("basis" => "Public check_ids/check_assessment APIs; coverage and outcomes are separate.",
         "scope" => "Added steel/electrolyzer records exposed by this scan; does not establish retrofit coverage outside the inventory.",
         "coverage" => coverage, "outcome" => outcomes, "by_rule" => by_rule,
         "expected_inventory_records" => length(expected), "assessed_records" => length(seen),
         "missing_inventory_records" => missing, "unmapped_asset_check_records" => sort!(collect(unmapped)),
         "incomplete_checks" => incomplete, "coverage_resolved" => resolved)
end
