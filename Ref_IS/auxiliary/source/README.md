# Standard rc1 source snapshot

`MacroEnergy-0.3.0-rc1.zip` contains the standard MacroEnergy `0.3.0-rc1` runtime source: 181 files under `MacroEnergy_rc1/`. It includes `src/`, `ext/`, `Project.toml`, and the upstream license. It contains no ESAG additions, local output fix, model case, results, or downloaded Julia dependencies.

This is the previously selected local standard-package snapshot. The original archive did not record an immutable upstream commit. `source_manifest.toml` identifies the exact ZIP and individual files with SHA-256 hashes. The Storage file was restored from its hash-verified backup before packaging.

The separate `storage_retrofit_output.patch` adds:

```julia
retrofitted_capacity(g::AbstractStorage) = 0.0;
```

Run `julia --startup-file=no Ref_IS/auxiliary/setup.jl` from the repository root. Setup verifies the archive, extracts it into `Ref_IS/auxiliary/.runtime/MacroEnergy_rc1/`, and applies this one-line change to that local copy. It checks the expected source hashes before and after the change. The ZIP remains unchanged. Git ignores `auxiliary/.runtime/`.

The patch prevents the previously reproduced Storage capacity-output failure in Myopic runs with `Retrofitting=true`. It changes no constraint-library file. PF was not tested.

Do not manually edit or recompress the ZIP for routine steel parameter changes. Edit `../template/config.json` instead. A deliberate source-version update must also update the source hashes, patch expectations, environment, and validation record.

See [the case README](../../README.md) for setup, scope, the completed local TDR trial, and remaining parameterization work.
