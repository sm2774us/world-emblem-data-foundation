# World Emblem Data Foundation

[![ci](https://github.com/sm2774us/world-emblem-data-foundation/actions/workflows/pr-verification.yml/badge.svg)](https://github.com/sm2774us/world-emblem-data-foundation/actions/workflows/pr-verification.yml)

A working, tested showcase for the **Senior Data Engineer / Data Architect** role at World Emblem International. It does not describe the job; it does it, on synthetic data: audit the estate, decide the architecture, build governed pipelines, prove quality, enforce governance, enable BI and AI, and execute a **machine-verified 90-day plan**.

## 1. Synopsis
World Emblem runs on Business Central, HubSpot, Optimizely, BigCommerce, marketing platforms and production systems. The gap is ownership of data *between* them. This repo is that owner, as code:

| JD area | What exists | Entry point |
|---|---|---|
| 1 Audit and current-state mapping | inventory-as-code, 39 scored findings, baseline scorecard, flow map, generated lineage | `emblem audit`, `emblem lineage` |
| 2 Enterprise architecture | system-of-record matrix (field-level), common keys/models, contracts, platform decision matrix + sensitivity | `emblem sor`, `emblem platform`, `emblem contracts` |
| 3 Engineering and integration | idempotent bronze, generated silver, SQL gold, MDM, Spark, Airflow, dbt, webhooks, governed API | `emblem run`, `dags/`, `dbt_project/` |
| 4 Quality and reliability | 25 checks over 7 dimensions, 6 reconciliations, incidents, escalation, runbooks, Prometheus | `emblem quality`, `reconcile`, `incidents` |
| 5 Governance and security | RBAC, masking, field encryption, hash-chained audit, retention, classification | `emblem governance` |
| 6 Reporting, AI, products | Power BI semantic model (BIM), forecast, vector index, allow-listed agent tools, usage monitoring | `emblem semantic`, `GET /v1/ai/*` |
| 7 Leadership | vendor scorecard, standards, training, translated business risks | `emblem vendors`, `docs/` |
| First 90 days | 14 milestones with exact steps/changes, each verified by code | `emblem plan verify`, `docs/90-DAY-PLAN.md` |

Every JD bullet is mapped to code, tests and a command in [`docs/JD-COMPLIANCE.md`](docs/JD-COMPLIANCE.md) (and a test fails if a path goes missing).

## 2. Directory structure
```text
src/emblem/
  contracts.py            data contracts: load/validate/normalise/diff
  sources/synthetic.py    deterministic simulators for BC, HubSpot, BigCommerce, Optimizely, ads, MES (with planted defects)
  pipelines/              bronze (idempotent), staging (generated), sqlmodels (dbt-style runner), mdm, forecast, lakehouse, retry, runner
  spark_jobs/             PySpark twin of revenue/order conformance
  quality/                checks (7 dimensions), reconcile (root-cause attribution)
  ops/                    incidents, events (webhooks), monitor (metrics), alerts
  security/               rbac+masking, crypto, audit chain, retention, tokens
  architecture/           system-of-record, platform scoring
  catalog/                audit engine, lineage
  governance/             vendor review
  ai/                     embeddings, governed index, agent tools
  reporting/              Power BI model, snapshot, dashboard
  plan/                   90-day plan engine + verifiers
  api/app.py              FastAPI governed service       cli.py  `emblem` command
  data/                   YAML as source of truth: contracts, SoR, inventory, policies, checks, plan, glossary, SQL models
dags/                     Airflow 3 DAGs (daily ELT, event drain, governance housekeeping)
dbt_project/              dbt models generated from the canonical SQL (tools/sync_dbt.py)
tests/{unit,integration,e2e}
docs/                     ARCHITECTURE, 90-DAY-PLAN, JD-COMPLIANCE, ENGINEERING-STANDARDS, TRAINING, lineage, adr/, runbooks/, powerbi/
infra/{docker,terraform}  .github/ (workflows, ruleset, CODEOWNERS, templates)   .gitleaks.toml
```

## 3. Compile, build and run
Python is interpreted: there is nothing to transpile; "build" = resolve and lock dependencies, type-check, test, package.
Requirements: **uv 0.12.x** (pinned 0.12.21) and **CPython 3.14** (latest stable; uv downloads it). JDK 21 only for the Spark test.
```bash
uv sync                    # install from uv.lock (use `uv sync --locked` in CI)
uv run emblem demo         # full showcase -> build/report.html
uv run emblem serve        # http://127.0.0.1:8000  (dashboard, /docs, /metrics)
make verify                # ruff + mypy --strict + tests (85% coverage gate) + e2e
make spark | airflow | dbt # optional engines (separate dependency groups)
make secrets               # gitleaks with .gitleaks.toml
uv build                   # wheel/sdist;   docker build -f infra/docker/Dockerfile -t emblem .
```
More in [WALKTHROUGH.md](WALKTHROUGH.md).

## 4. Solution explained (from the JD's point of view)
**Audit.** `system_inventory.yaml` models systems, integrations (mechanism, schedule, secret store, documented, retries, idempotent, monitored), jobs, reports and downstream consumers. `catalog/audit.py` converts it into findings in the JD's exact categories (duplicates, missing ownership, weak controls, manual work, reconciliation gaps, security risks, fragile integrations) and a six-axis baseline. The estate is an *assumption* from the JD, to be confirmed in days 1-30.
**Architecture.** One authority per domain with field-level overrides; a validator proves each authority hosts its domain and flags any non-authority writing into it (INT-06). Gold SQL survivorship follows the matrix. The platform choice (Microsoft Fabric) comes from a weighted matrix whose winner is stress-tested by perturbing weights ±50%.
**Engineering.** Contracts generate typing, drift handling and SLAs. Bronze is append-only with SHA-256 content keys, `ON CONFLICT DO NOTHING`, one transaction per dataset, bounded exponential retry, quarantine for poison rows, schema-change ledger. Replays and overlap windows are provably no-ops. Silver keeps the latest version per key. Entity resolution (exact, shared domain, fuzzy ≥0.92) produces stable `company_key`s. Gold models are SQL with `ref()`, topologically ordered; the same SQL is emitted as a dbt project and the revenue logic is re-implemented in PySpark with a to-the-cent parity test. Airflow DAGs are thin wrappers with retries, backoff, `max_active_runs=1`, failure callbacks and a critical-check gate before publish. Webhooks are HMAC-signed with replay protection and an idempotent inbox with dead-letter.
**Quality.** Checks are declarative YAML (SQL returning one number); a broken check fails loudly. Volume and schema checks use pipeline metadata. Six reconciliations attribute root cause. Incidents are idempotent, auto-resolve, route to the *business owner* via the SoR matrix, carry an escalation ladder and a **fix-at-source** action ("resolve the source, not the report").
**Governance.** Policies-as-code (roles, entitlements, classification, masking, retention) under CODEOWNERS. Field-level Fernet encryption with HKDF-derived keys (env only; prod refuses to start without secrets), deterministic tokenisation, hash-chained audit log, retention dry-run by default.
**Enablement.** Power BI BIM generated from gold (relationships, DAX measures, RLS) and validated against the schema. Only approved non-PII text is embedded; agents get parameterised tools, not SQL, and every call is audited and monitored. Direct production access is replaced by gold + API.
**90-day plan.** `plan_90_day.yaml` holds exact steps, changes, exit criteria, metrics and a verifier per milestone. `emblem plan verify` executes them against the running platform; `docs/90-DAY-PLAN.md` is generated and tested for drift. Roadmap ranks `(value+risk+AI)/effort`; budget is an editable range.

## 5. Technology choices and why
| Choice | Why (JD lens) |
|---|---|
| Python 3.14 + **uv** | JD: Python; uv gives locked, fast, reproducible installs; `UV_FROZEN` in CI |
| DuckDB + Parquet | zero-infra lakehouse stand-in; same SQL runs on Fabric/Databricks; open format keeps the platform choice reversible |
| SQL models + dbt export | JD: SQL, dbt; models are the tested, versioned transformation layer |
| PySpark | JD: Apache Spark; parity test proves portability to production volumes |
| Airflow 3 (`airflow.sdk`) | JD: Airflow; code-first, DAG integrity tested |
| Pydantic/FastAPI | typed, secure data services for analytics/AI/internal tools |
| YAML as source of truth | owners can review contracts/policies in PRs; docs and tests derive from it |
| Hash-chained audit, HMAC webhooks, Fernet | audit logging, integrity, encryption without exotic dependencies |
| Hashed n-gram embeddings | dependency-free, deterministic vector search; swap `embed()` for Azure OpenAI in prod |
| mypy `--strict`, ruff (incl. `S` security rules) | maintainability and secure-by-default code |

## 6. CI/CD, testing and GitHub best practices
* **Pyramid:** unit (pure logic, failure modes) > integration (real DuckDB pipeline, API via TestClient, Spark parity, Airflow DagBag) > e2e (real CLI + uvicorn + HTTP, no mocks). Coverage gate 85%.
* **Pipeline** (`pr-verification.yml`): guard (Conventional-Commit PR title, no Dependabot/Renovate) -> **gitleaks full-history** -> ruff/mypy/tests -> e2e, Spark, Airflow, dbt, Docker hardened smoke (read-only, non-root, cap-drop, refuses unsafe prod config), Terraform fmt/validate -> single required check `ci-ok (required check)`.
* **Branch protection** (`.github/rulesets/protect-main.json`): PR required, CODEOWNERS review, linear history, squash only, stale-review dismissal, required status check.
* **Supply chain:** actions pinned to commit SHAs, locked dependencies, SBOM + provenance attestation, OIDC (no stored cloud keys), manual approval environment for releases.
* **Secrets:** `.gitleaks.toml` (default ruleset + project rules, minimal synthetic allow-list) in pre-commit hook, PR job and weekly scan.
* **Releases:** SemVer + CHANGELOG generated from Conventional Commits (`tools/release.py`, tested).
* **Docs:** WALKTHROUGH, ADRs, runbooks, SECURITY, CONTRIBUTING, PR/issue templates.

## 7. Limits (honest)
Synthetic data; the estate and scores are hypotheses to be confirmed in days 1-30; the risk and budget figures are illustrative. Terraform, Docker and GitHub Actions were not executed in the authoring sandbox.

MIT licensed.
