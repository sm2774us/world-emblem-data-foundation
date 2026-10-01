# Contributing

1. Branch from `main`; use Conventional Commits (`feat:`, `fix:`, `docs:` ...). The `commit-msg` hook (`make hooks`) enforces it.
2. **No change merges without regression tests** at the right level (unit / integration / e2e). Bug fixes include a test that fails without the fix.
3. Run `make verify` and `make secrets` before pushing.
4. Open a PR with a Conventional Commit title. CI job `ci-ok (required check)` must be green and a code owner must approve. Squash merge only.
5. Never edit `CHANGELOG.md` or the version by hand: `release.yml` generates both after an approved release.
6. Changes to contracts, system-of-record, policies or infra are reviewed by the owning department via CODEOWNERS.
7. Do not add Dependabot/Renovate configuration; CI rejects it (dependency updates are deliberate: `uv lock --upgrade` in a reviewed PR).
