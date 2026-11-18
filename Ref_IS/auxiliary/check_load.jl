include(joinpath(@__DIR__, "runtime.jl"))
RefISRuntime.activate_runtime()
using MacroEnergy
const ME = MacroEnergy
const CASE_DIR = dirname(@__DIR__)
RefISRuntime.verify_loaded_package(ME)

function check_load()
    case = ME.load_case(CASE_DIR)
    @assert length(case.systems) == 7
    rows = Dict[]
    for (i, system) in enumerate(case.systems)
        steel = filter(a -> startswith(string(ME.id(a)), "steel_"), system.assets)
        electrolyzers = filter(a -> startswith(string(ME.id(a)), "electrolyzer_steel_"), system.assets)
        @assert length(steel) == (i <= 2 ? 85 : 153)
        @assert length(electrolyzers) == 17
        @assert system.settings.Retrofitting
        @assert length(unique(ME.id.(system.assets))) == length(system.assets)
        @assert all(length(ME.time_interval(a.crudesteel_edge)) == 8760 for a in steel)
        td = system.time_data[:Electricity]
        sample = ME.Storage{ME.Electricity}(id=:output_check, timedata=td)
        @assert ME.retrofitted_capacity(sample) === 0.0
        output = ME.get_optimal_capacity_by_field([sample], ME.retrofitted_capacity, 1.0)
        @assert output.value == [0.0]
        push!(rows, Dict("period"=>i, "steel_assets_including_retrofits"=>length(steel),
                         "electrolyzers"=>length(electrolyzers), "hourly_steps"=>8760))
    end
    result = Dict("passed"=>true, "julia_version"=>string(VERSION), "macroenergy_version"=>string(Base.pkgversion(ME)),
                  "bundled_source_selected"=>true, "optimization_performed"=>false, "periods"=>rows)
    println("REF_IS_LOAD_CHECK_JSON ", ME.JSON3.write(result))
    println("PASS: all seven periods loaded; Storage output accessor checked. No optimizer was created.")
end

ME.load_user_additions(CASE_DIR)
ME.refresh_user_type_registries!()
Base.invokelatest(check_load)
