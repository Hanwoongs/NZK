module RefISRuntime
using SHA
using TOML
import Pkg

const AUX_ROOT = @__DIR__
const CASE_ROOT = dirname(AUX_ROOT)
const SOURCE_DIR = joinpath(AUX_ROOT, "source")
const RUNTIME_DIR = joinpath(AUX_ROOT, ".runtime")
const PACKAGE_DIR = joinpath(RUNTIME_DIR, "MacroEnergy_rc1")
const ENV_DIR = joinpath(RUNTIME_DIR, "environment")
const STORAGE_FILE = "src/model/networks/storage.jl"

file_sha(path) = bytes2hex(open(SHA.sha256, path))
source_record() = TOML.parsefile(joinpath(SOURCE_DIR, "source_manifest.toml"))

function verify_archive(record)
    archive = joinpath(SOURCE_DIR, record["archive_file"])
    patch = joinpath(SOURCE_DIR, record["patch_file"])
    file_sha(archive) == record["archive_sha256"] || error("Source ZIP hash mismatch")
    file_sha(patch) == record["patch_sha256"] || error("Storage patch hash mismatch")
    return archive
end

function verify_tree(root, record; patched)
    isdir(root) || error("Source is missing. Run Ref_IS/auxiliary/setup.jl first.")
    actual = Set(replace(relpath(joinpath(dir, name), root), '\\' => '/')
                 for (dir, _, names) in walkdir(root) for name in names)
    actual == Set(keys(record["files"])) || error("Runtime source file list changed; existing files were preserved")
    for (name, digest) in record["files"]
        expected = patched && name == STORAGE_FILE ? record["storage_after_sha256"] : digest
        file_sha(joinpath(root, name)) == expected || error("Runtime source changed: $name; existing files were preserved")
    end
end

function prepare_source()
    record = source_record()
    archive = verify_archive(record)
    if isdir(PACKAGE_DIR)
        verify_tree(PACKAGE_DIR, record; patched=true)
        println("Verified existing runtime source and Storage fix.")
        return
    end
    ispath(PACKAGE_DIR) && error("The runtime source path already exists and is not a directory")
    mkpath(RUNTIME_DIR)
    stage = mktempdir(RUNTIME_DIR; prefix="extract_")
    try
        # Julia 1.13 includes 7-Zip through Pkg. No system unzip command is needed.
        run(pipeline(`$(Pkg.PlatformEngines.exe7z()) x -y $("-o" * stage) $archive`, stdout=devnull))
        unpacked = joinpath(stage, "MacroEnergy_rc1")
        verify_tree(unpacked, record; patched=false)
        storage = joinpath(unpacked, STORAGE_FILE)
        content = read(storage, String)
        anchor = "retrofitted_capacity_track(g::AbstractStorage,s::Int64)"
        length(findall(anchor, content)) == 1 || error("Storage patch anchor is not unique")
        updated = replace(content, anchor => "retrofitted_capacity(g::AbstractStorage) = 0.0;\n" * anchor; count=1)
        write(storage, updated)
        verify_tree(unpacked, record; patched=true)
        dirname(abspath(PACKAGE_DIR)) == abspath(RUNTIME_DIR) || error("Unexpected runtime destination")
        mv(unpacked, PACKAGE_DIR)
        println("Extracted verified rc1 source and applied the separate Storage output fix.")
    finally
        # Delete only this invocation's temporary extraction directory.
        dirname(realpath(stage)) == realpath(RUNTIME_DIR) || error("Unexpected extraction cleanup path")
        startswith(basename(stage), "extract_") || error("Unexpected extraction directory name")
        rm(stage; recursive=true)
    end
end

function environment_templates()
    return [("Project.toml", "Project.toml"), ("Manifest.lock", "Manifest.toml")]
end

function verify_environment()
    for (input_name, output_name) in environment_templates()
        template = joinpath(AUX_ROOT, "environment", input_name)
        output = joinpath(ENV_DIR, output_name)
        isfile(output) || error("Environment is missing. Run Ref_IS/auxiliary/setup.jl first.")
        TOML.parsefile(output) == TOML.parsefile(template) ||
            error("Local environment differs from the recorded template: $output_name; it was preserved")
    end
end

function prepare_environment()
    mkpath(ENV_DIR)
    for (input_name, output_name) in environment_templates()
        template = joinpath(AUX_ROOT, "environment", input_name)
        output = joinpath(ENV_DIR, output_name)
        isfile(output) || cp(template, output; force=false)
    end
    verify_environment()
end

function activate_runtime()
    record = source_record()
    verify_archive(record)
    verify_tree(PACKAGE_DIR, record; patched=true)
    verify_environment()
    Pkg.activate(ENV_DIR)
end

function verify_loaded_package(ME)
    Base.pkgversion(ME) == v"0.3.0-rc1" || error("Unexpected MacroEnergy version")
    realpath(pathof(ME)) == realpath(joinpath(PACKAGE_DIR, "src", "MacroEnergy.jl")) ||
        error("Unexpected MacroEnergy source; use a fresh Julia process")
    hasmethod(ME.retrofitted_capacity, Tuple{ME.Storage{ME.Electricity}}) || error("Storage output fix is missing")
end
end
