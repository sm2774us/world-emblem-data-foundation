## What and why

## Regression evidence (required)
- [ ] Tests added/updated at the right level (unit / integration / e2e); bug fixes include a test that fails without the fix
- [ ] `make verify` passes locally
- [ ] Data contract / system-of-record / policy changes reviewed by the owning department (see CODEOWNERS)

## Data and security checklist
- [ ] New or changed source has a contract (`contracts.yaml`), classification, freshness SLA and retention
- [ ] Idempotent and replay-safe; failure behaviour described
- [ ] No secrets, no widened permissions, no direct production access (`make secrets` clean)
- [ ] Runbook / docs / CHANGELOG-relevant behaviour updated (PR title is a Conventional Commit)
