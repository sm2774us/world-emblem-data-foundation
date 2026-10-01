# Engineering standards for data integrations

Published in the 90-day plan (milestone M3.4). Every new integration or data product must satisfy this checklist **before** go-live; the PR template and CI enforce what can be automated.

## 1. Intake (before building)
- Business owner and the decision the data supports. Domain and **system of record** (`system_of_record.yaml`). If it conflicts with the matrix, change the matrix first.
- Data contract: columns, types, required fields, classification (`public|internal|confidential|pii|restricted`), freshness SLA, retention.
- Access: which roles need it; PII columns masked by default.

## 2. Build
- **Idempotent**: replays and overlap windows are safe (content hash / natural key upsert). Each load is one transaction per dataset.
- **Recoverable**: bounded exponential backoff on transient errors; poison data is quarantined with a reason, never silently dropped.
- **Schema change**: additive = log and PR; rename = alias in the contract; breaking = quarantine + SEV1.
- **Batch vs events**: batch for bulk and reconciliation; webhooks for latency-sensitive events (HMAC signature, timestamp tolerance 5 min, idempotent inbox, dead-letter).
- **Secrets**: Key Vault / GitHub Environments only. No literals, no personal tokens, no shared service accounts. `gitleaks` blocks PRs.
- **Naming**: `bronze.<system>__<entity>`, `silver.stg_<system>__<entity>`, `gold.dim_*|fact_*|mart_*`; keys end in `_key` and are stable.

## 3. Test (all required)
| Level | Evidence |
|---|---|
| Unit | pure logic, edge cases, failure modes |
| Integration | real DuckDB pipeline, API, Spark parity, Airflow DAG import |
| End-to-end | real CLI and HTTP server, no mocks |
| Data | quality checks + reconciliation for the new domain |
Regression rule: a bug fix ships with a test that fails without the fix. Coverage gate 85%.

## 4. Operate
- Runbook in `docs/runbooks`; incident routing to the **business owner** with a fix-at-source action.
- Metrics (`/metrics`), alerts (`on_failure_callback`), freshness and volume checks.
- Retention enforced (dry-run first), audit log verified weekly.

## 5. Vendor-built integrations
Scored on documentation (25), security (30), maintainability (25), delivery quality (20). A zero on *secrets in vault* or *idempotency* blocks acceptance regardless of score. Output: dated remediation commitments.

## 6. Change process
Conventional Commit PR title -> CODEOWNERS review -> required check `ci-ok` -> squash merge -> automated SemVer release with manual approval.
