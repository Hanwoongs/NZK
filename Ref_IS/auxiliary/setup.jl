include(joinpath(@__DIR__, "runtime.jl"))
import Pkg

allowed = Set(["--source-only", "--offline"])
all(arg in allowed for arg in ARGS) || error("Usage: julia Ref_IS/auxiliary/setup.jl [--source-only] [--offline]")
VERSION == v"1.13.1" || @warn "This environment was verified with Julia 1.13.1" current_version=VERSION
RefISRuntime.prepare_source()
RefISRuntime.prepare_environment()
if "--source-only" in ARGS
    println("Source and environment files are ready. Dependencies were not installed; no model was loaded or solved.")
else
    "--offline" in ARGS && Pkg.offline(true)
    RefISRuntime.activate_runtime()
    Pkg.instantiate(; allow_autoprecomp=false, julia_version_strict=true)
    RefISRuntime.verify_environment()
    println("Dependencies are installed. Run Ref_IS/auxiliary/check_load.jl next. No model was loaded or solved.")
end
