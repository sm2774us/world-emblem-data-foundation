# World Emblem Data Foundation: Walkthrough

Run it, use it, debug it, change it safely.

| You are | Go to |
|---|---|
| New, on Windows 11 | Part 1 then Part 2 |
| On Ubuntu / WSL2 / macOS | Part 3 |
| Reviewing for the interview | Part 2 (demo script) |
| About to open a PR | Part 5 and Part 6 |
| Something broke | Troubleshooting |

## Part 1: Windows 11 setup (PowerShell)
```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
winget install --id Microsoft.OpenJDK.21 -e     # only for the Spark parity job
git clone https://github.com/sm2774us/world-emblem-data-foundation.git
cd world-emblem-data-foundation
uv sync            # downloads CPython 3.14 automatically and installs locked dependencies
```

## Part 2: Run and demo (any OS)
```bash
uv run emblem demo        # builds the warehouse, runs checks, opens incidents, verifies the 90-day plan, writes build/report.html
uv run emblem serve       # dashboard + API at http://127.0.0.1:8000  (Swagger at /docs in dev)
```
Suggested 10-minute interview script (dashboard tabs):
1. **Overview**: baseline scorecard, 14/14 milestones verified by code.
2. **1 Current state**: colour-coded flow map, scored findings (ownership, weak controls, secrets, manual work, duplicates, recon gaps).
3. **2 Architecture**: system-of-record matrix, conflicting writer (INT-06), platform decision with sensitivity.
4. **3 Pipelines**: idempotent ingest ledger, schema drift (rename, additive), batch 3 volume collapse.
5. **4 Quality & recon** and **Incidents**: planted defects found, each with owner, escalation, runbook, fix-at-source.
6. **5 Governance**: masking before/after, audit chain, retention dry-run.
7. **6 AI & BI**: vector search with citations, agent tools, usage monitoring, Power BI model, vendor verdicts.
8. **90-day plan**: every milestone with exact steps/changes, verified evidence, roadmap, budget.

API tour:
```bash
TOKEN=$(curl -s -X POST localhost:8000/v1/auth/dev-token -H 'content-type: application/json' -d '{"role":"data_engineer"}' | python -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -H "Authorization: Bearer $TOKEN" "localhost:8000/v1/datasets/dim_contact?limit=2"   # PII masked
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/v1/incidents?status=open
curl -s localhost:8000/metrics
```

## Part 3: Ubuntu / WSL2 / macOS
Work inside the Linux filesystem. `curl -LsSf https://astral.sh/uv/install.sh | sh`, then `make install && make demo`.

## Part 4: Optional engines
| Task | Command |
|---|---|
| Spark parity (needs JDK 21) | `make spark` |
| Airflow DAG integrity | `make airflow` |
| dbt build on the same silver layer | `make dbt` |
| Parquet lakehouse export | `make lakehouse` |
Airflow and dbt are separate dependency groups that conflict on shared pins, so they are never installed together.

## Part 5: How automation works
| Workflow | Trigger | Purpose |
|---|---|---|
| `pr-verification.yml` | PR to `main` | guard (PR title), **gitleaks**, lint/types/tests+coverage, e2e, Spark, Airflow, dbt, Docker smoke, Terraform; single required check `ci-ok (required check)` |
| `release.yml` | push to `main` | plan SemVer from Conventional Commits, **manual approval** (`release` environment), tag, GitHub Release, GHCR image with provenance + SBOM |
| `codeql.yml` | push/PR/weekly | static analysis (public repos / GHAS) |
| `secrets-scan.yml` | push/weekly | gitleaks full history |
| `deploy.yml` | manual | Azure OIDC, no stored keys, smoke test |
| `housekeeping.yml` | weekly | prune workflow history |

## Part 6: GitHub setup (once)
1. Create the repo, push `main`. 2. Settings > Rules > Rulesets > Import `.github/rulesets/protect-main.json` (replace the bypass actor id with your Actions integration or remove it). 3. Settings > Environments: create `release` (required reviewer) and `dev`/`prod`. 4. Actions > Allow GitHub Actions to create PRs: off; Dependabot: off. 5. Optional variables for deploy: `DEPLOY_ENABLED`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `CONTAINER_APP`, `RESOURCE_GROUP`. 6. `make hooks` locally.

## Part 7: Test catalogue
Unit `tests/unit` (contracts, bronze, MDM, security, audit, plan, release tool); integration `tests/integration` (pipeline, quality, API, Spark parity, Airflow DAGs); e2e `tests/e2e` (real CLI + real uvicorn + HTTP). Add a regression test for every fix at the lowest level that reproduces it.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `No data yet` from API/CLI | `uv run emblem demo` |
| Spark test skipped | `uv sync --group spark` and install JDK 21 |
| `docs` drift fails CI | `uv run emblem docs && python tools/sync_dbt.py` and commit |
| gitleaks finding | remove the secret, rotate it, never allow-list real keys |
