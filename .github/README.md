# Note on CI

`.github/workflows/` was removed on this branch.

Those five files (`ci.yml`, `documentation.yml`, `TagBot.yml`,
`CompatHelper.yml`, `changelog-sync.yml`) are MacroEnergy.jl's own package CI,
inherited when this branch was based on `upstream/release-0.3`. They are not
useful here:

- `ci.yml` would run the Julia package test suite on every push to a research
  repo, burning Actions minutes
- `documentation.yml` would try to deploy package docs to `gh-pages`
- `TagBot` and `CompatHelper` only apply to a registered Julia package

They were also the practical blocker: pushing them requires a Personal Access
Token with the `workflow` scope.

To restore them:

```bash
git checkout upstream/release-0.3 -- .github/workflows
```

and push with a token that has `workflow` scope.
