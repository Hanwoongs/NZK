include(joinpath(@__DIR__, "auxiliary", "runtime.jl"))
RefISRuntime.activate_runtime()
using MacroEnergy
using Gurobi
RefISRuntime.verify_loaded_package(MacroEnergy)

# This entry point starts the full-resolution optimization.
case, solution = MacroEnergy.run_case(
    @__DIR__;
    optimizer=Gurobi.Optimizer,
    optimizer_attributes=("Method" => 2, "BarConvTol" => 1e-3, "Crossover" => 0),
);
