# World Emblem Data Foundation Walkthrough

Install it, run it, use it, debug it, change it safely, publish it, lock it down, release it. Pick your path.

| You are | Go to |
|---|---|
| Brand new, on Windows 11 | **Part 1** then **Part 2** |
| On Ubuntu, WSL2 or macOS | **Part 3** |
| Preparing the interview demo | **Part 2** (10-minute script) |
| Want the optional engines (Spark, Airflow, dbt) | **Part 4** |
| Debugging in VS Code | **Part 6** |
| About to open a pull request | **Part 7** and **Part 8** |
| Publishing to GitHub | **Part 9** then **Part 10** |
| Something broke | **Troubleshooting** at the end |

Conventions: `bat` blocks run in **Windows Command Prompt**, `powershell` blocks in PowerShell, `bash` blocks in Ubuntu/WSL2/macOS/Git Bash. An unlabelled block is identical everywhere. Project folder: `world-emblem-data-foundation`.

---

## Part 0 · What you are about to run (60 seconds)

A data platform on **synthetic data** that mimics World Emblem's systems (Business Central, HubSpot, BigCommerce, Optimizely, ad platforms, production MES). One command builds a warehouse, loads three batches, runs 25 quality checks and 6 reconciliations, opens incidents, verifies a 90-day plan and writes an HTML dashboard. Another serves that dashboard plus a governed API.

The main demo needs no cloud account, Docker, Java or database server. You need **Git**, **uv** (installs Python 3.14 for you) and a browser.

---

## Part 1 · Windows 11 setup (Command Prompt)

1. Open **Command Prompt** (Start, type `cmd`, Enter). Install the tools once:
   ```bat
   winget install --id Git.Git -e
   winget install --id astral-sh.uv -e
   winget install --id GitHub.cli -e
   winget install --id Microsoft.VisualStudioCode -e
   ```
   Optional, only for the parts named:
   ```bat
   winget install --id EclipseAdoptium.Temurin.21.JDK -e
   winget install --id Docker.DockerDesktop -e
   winget install --id Hashicorp.Terraform -e
   winget install --id Gitleaks.Gitleaks -e
   ```
   (JDK = Spark test, Docker = container run, Terraform = infra validation, Gitleaks = local secret scan.)
2. **Close and reopen** Command Prompt so the programs are on PATH, then check:
   ```bat
   git --version
   uv --version
   gh --version
   ```
   You do **not** install Python: `uv` downloads CPython 3.14 automatically (CI pins uv 0.12.21; any 0.11+ works).
3. Tell Git who you are (once per machine):
   ```bat
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   git config --global init.defaultBranch main
   ```
4. Log in to GitHub (once). Choose **GitHub.com**, **HTTPS**, **Login with a web browser**, follow the one-time code:
   ```bat
   gh auth login
   gh auth status
   ```
5. Get the code.
   * **ZIP route:** unzip `world-emblem-data-foundation.zip`; it contains a folder `wedf` (the project root, the one with `pyproject.toml`):
     ```bat
     cd %USERPROFILE%\Downloads\world-emblem-data-foundation\wedf
     ```
     (adjust to wherever you unzipped it).
   * **Your own GitHub copy** (after Part 9):
     ```bat
     mkdir %USERPROFILE%\code
     cd %USERPROFILE%\code
     git clone https://github.com/sm2774us/world-emblem-data-foundation.git
     cd world-emblem-data-foundation
     ```
6. Install dependencies from the lock file (first run downloads Python 3.14 and about 60 packages):
   ```bat
   uv sync
   ```
7. Install the Git hooks (checks commit messages and lint before each commit; the folder must be a Git repo, see Part 9):
   ```bat
   uv run python tools/install_hooks.py
   ```
8. Sanity check. Expect `68 passed`:
   ```bat
   uv run pytest -m "not e2e and not spark and not airflow" -q
   ```

> `make` is not installed on Windows. Every `make` shortcut has a plain `uv run ...` equivalent in Part 5, so you never need it.

## Part 2 · Run and use it (novice steps and interview script)

1. Build everything (about 20 seconds):
   ```bat
   uv run emblem demo
   ```
   Expect (numbers may differ slightly): `quality 12/25 passing | recon breaks 4 | open incidents 17`, `90-day milestones verified: 14/14`, `dashboard: build/report.html`. The low quality score is **intentional**: the data has planted defects for the platform to find.
2. Open the static report: `start build\report.html` (macOS `open`, Linux `xdg-open`).
3. Or start the live server (dashboard + API):
   ```bat
   uv run emblem serve
   ```
   Wait for `Uvicorn running on http://127.0.0.1:8000`, open <http://127.0.0.1:8000>. Stop with `Ctrl+C`. Interactive API docs: <http://127.0.0.1:8000/docs>.
4. **10-minute interview tour** (left menu):

   | Tab | Say this |
   |---|---|
   | Overview | "Baseline scorecard; every one of the 14 plan milestones is verified by code, not slides." |
   | 1 Current state | Colour-coded flow map; scored findings in the JD's categories (ownership, weak controls, secrets, manual work, duplicates, reconciliation gaps). The estate is an *assumption* from the JD, confirmed in days 1-30. |
   | 2 Architecture | System-of-record matrix with field-level authority; INT-06 flagged as a non-authority writer; platform decision (Fabric) that still wins when weights move ±50%. |
   | 3 Pipelines | Ingest ledger per batch (duplicates absorbed, nothing double-counted); schema drift (rename, new field); BigCommerce volume collapse in batch 3. |
   | 4 Quality & recon | 25 checks over 7 dimensions; reconciliations with root cause (13 web orders never reached the ERP). |
   | Incidents | Severity, **business owner**, escalation ladder, runbook, *fix-at-source* action. |
   | 5 Governance | Masking before/after, audit chain valid, retention dry-run. |
   | 6 AI & BI | Vector search with citations, allow-listed agent tools, usage monitoring, Power BI model, vendor verdicts. |
   | Lineage | Source to gold to consumer, generated from code. |
   | 90-day plan | Exact steps and changes per milestone, verified evidence, roadmap, budget. |
   | JD traceability | Every JD bullet mapped to a file and a command. |

5. **CLI tour** (all work after `uv run emblem demo`; stop a running server first, see Troubleshooting):

   | Command | What you see |
   |---|---|
   | `uv run emblem audit` | scored findings (`--baseline` scorecard, `--json` JSON) |
   | `uv run emblem sor` | system-of-record matrix and conflicting writers |
   | `uv run emblem platform` | ranked platform options and sensitivity |
   | `uv run emblem contracts` | the 16 data contracts |
   | `uv run emblem quality` | check summary and every failure |
   | `uv run emblem reconcile` | six reconciliations |
   | `uv run emblem incidents` | open incidents with owners |
   | `uv run emblem vendors` | vendor integration verdicts |
   | `uv run emblem governance` | roles and retention dry-run |
   | `uv run emblem lineage` | Mermaid diagram (paste into <https://mermaid.live>) |
   | `uv run emblem semantic` | Power BI model JSON |
   | `uv run emblem plan verify` | PASS/FAIL per 90-day milestone |
   | `uv run emblem plan roadmap` / `plan budget` | ranked roadmap / budget range |
   | `uv run emblem run` | re-run all three batches (prints `bronze+0 rows` on replay) |
   | `uv run emblem lakehouse` | gold tables to `build/lakehouse/*.parquet` |
   | `uv run emblem docs` | regenerates `docs/lineage.md`, `docs/90-DAY-PLAN.md`, `docs/JD-COMPLIANCE.md`, `docs/powerbi/model.bim` |

6. **API tour** (server running). Easiest: open <http://127.0.0.1:8000/docs>, run `POST /v1/auth/dev-token` with body `{"role": "data_engineer"}`, copy the `token`, click **Authorize**, paste it, try `GET /v1/datasets/dim_contact`. Compare roles:

   | Role | `dim_contact` (people) | `/v1/incidents` | `/v1/ai/tools/order_status` |
   |---|---|---|---|
   | `admin` | clear | yes | yes |
   | `data_engineer` | **masked** (hashed) | yes | yes |
   | `sales_rep` | clear (may unmask PII) | no | no |
   | `marketing_analyst` | **403 denied** | no | no |
   | `ai_agent` | 403 | no | **403** (not entitled) |

   PowerShell:
   ```powershell
   $t = (Invoke-RestMethod -Method Post http://127.0.0.1:8000/v1/auth/dev-token -ContentType 'application/json' -Body '{"role":"data_engineer"}').token
   Invoke-RestMethod -Headers @{Authorization="Bearer $t"} "http://127.0.0.1:8000/v1/datasets/dim_contact?limit=2" | ConvertTo-Json -Depth 5
   Invoke-RestMethod -Headers @{Authorization="Bearer $t"} "http://127.0.0.1:8000/v1/incidents?status=open" | ConvertTo-Json -Depth 5
   Invoke-RestMethod http://127.0.0.1:8000/metrics
   ```
   bash:
   ```bash
   T=$(curl -s -X POST localhost:8000/v1/auth/dev-token -H 'content-type: application/json' -d '{"role":"data_engineer"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
   curl -s -H "Authorization: Bearer $T" "localhost:8000/v1/datasets/dim_contact?limit=2"
   curl -s -H "Authorization: Bearer $T" "localhost:8000/v1/incidents?status=open"
   curl -s localhost:8000/metrics
   ```
   More endpoints: `/v1/catalog`, `/v1/quality`, `/v1/reconciliation`, `/v1/lineage/gold:mart_revenue_monthly`, `/v1/audit/verify`, `/v1/ai/search?q=embroidered patch`, `/v1/ai/usage`, `/v1/showcase`.

7. **Event-driven demo (signed webhook).** Start the server with a secret you invent (never reuse a real one):
   ```bat
   set EMBLEM_WEBHOOK_SECRET=local-demo-secret-change-me
   uv run emblem serve
   ```
   (bash: `EMBLEM_WEBHOOK_SECRET=local-demo-secret-change-me uv run emblem serve`. PowerShell: `$env:EMBLEM_WEBHOOK_SECRET="local-demo-secret-change-me"; uv run emblem serve`.)
   In a **second** terminal, set the same variable and send a signed order event twice:
   ```bat
   set EMBLEM_WEBHOOK_SECRET=local-demo-secret-change-me
   uv run python tools/send_webhook.py --id evt-1
   uv run python tools/send_webhook.py --id evt-1
   ```
   First prints `200 {"status":"accepted"}`, second `200 {"status":"duplicate"}` (idempotent). In Swagger run `POST /v1/events/drain` as `data_engineer`: `{"processed":1,"dead_letter":0}`. A wrong secret gives `401`; try it.
8. **Container run (optional, Docker Desktop running):**
   ```bat
   docker build -f infra/docker/Dockerfile -t emblem:local .
   mkdir build
   docker run --rm -v "%cd%\build:/app/build" emblem:local demo --out /app/build/report.html
   docker run --rm -p 8000:8000 -v "%cd%\build:/app/build" emblem:local serve --host 0.0.0.0
   ```
   (bash: replace `"%cd%\build` with `"$PWD/build`.) The first container builds the warehouse into the shared `build` folder, the second serves it.

## Part 3 · Ubuntu, WSL2 or macOS

Work inside the Linux filesystem (`~/code`, not `/mnt/c/...`) or installs crawl.
```bash
# Ubuntu / WSL2 prerequisites
sudo apt update && sudo apt install -y git curl make unzip
curl -LsSf https://astral.sh/uv/install.sh | sh        # reopen the terminal afterwards
# GitHub CLI (Ubuntu)
(type -p wget >/dev/null || sudo apt install wget -y) && sudo mkdir -p -m 755 /etc/apt/keyrings \
 && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null \
 && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null \
 && sudo apt update && sudo apt install gh -y
# macOS instead:  brew install git uv gh make
git --version && uv --version && gh --version
git config --global user.name "Your Name" && git config --global user.email "you@example.com" && git config --global init.defaultBranch main
gh auth login

git clone https://github.com/sm2774us/world-emblem-data-foundation.git ~/code/world-emblem-data-foundation
cd ~/code/world-emblem-data-foundation          # ZIP route: unzip, then cd into the wedf folder
make install && make hooks
make demo
make serve                                       # = uv run emblem serve
```
Then follow Part 2 from step 2. Windows browsers reach WSL servers at `http://localhost:8000`.

Shortcuts: `make verify` (lint, types, tests, e2e), `test`, `unit`, `integration`, `e2e`, `spark`, `airflow`, `dbt`, `secrets`, `docs`, `lakehouse`, `docker`, `tf-validate`.

## Part 4 · Optional engines (each is a separate dependency group)

| What | Needs | Commands (any OS) |
|---|---|---|
| **Spark parity** (Spark and DuckDB agree to the cent) | JDK 21 (`java -version`) | `uv sync --group spark` then `uv run pytest -m spark --no-cov` |
| **Airflow DAG integrity** (3 DAGs import, standards, task order) | nothing extra | `uv sync --group airflow` then `uv run pytest -m airflow --no-cov` |
| **dbt build + data tests** on the same warehouse | run the demo first | `uv sync --group dbt`, `uv run emblem demo`, then see below |
| **Parquet lakehouse** | demo first | `uv run emblem lakehouse` (files in `build/lakehouse`) |
| **Terraform validate** | Terraform | `terraform fmt -check -recursive infra/terraform`, then per env: `terraform -chdir=infra/terraform/envs/dev init -backend=false` and `terraform -chdir=infra/terraform/envs/dev validate` (same for `prod`) |
| **Local secret scan** | gitleaks | `gitleaks detect --source . --config .gitleaks.toml --redact --no-banner` |

dbt (expect `PASS=34 ERROR=0`):
```bat
cd dbt_project
set EMBLEM_DB=../build/emblem.duckdb
uv run --project .. dbt build --project-dir . --profiles-dir .
cd ..
```
bash: `cd dbt_project && EMBLEM_DB=../build/emblem.duckdb uv run --project .. dbt build --project-dir . --profiles-dir . && cd ..`

Airflow, dbt and Spark are separate groups, and Airflow conflicts with dbt, so `uv sync --group airflow` **replaces** the other installs. To return to normal: `uv sync`. To run the same steps the DAGs run, without a scheduler: `uv run emblem run`.

## Part 5 · Every check, with and without `make`

| Goal | Command (any OS) | `make` |
|---|---|---|
| Lint | `uv run ruff check src tests dags tools` | `make lint` |
| Format (fix) / check | `uv run ruff format src tests dags tools` / add `--check` | `make fmt` |
| Types (strict) | `uv run mypy` | `make types` |
| Unit + integration + 85% coverage gate | `uv run pytest -m "not e2e and not spark and not airflow" --cov` | `make test` |
| Unit only | `uv run pytest tests/unit --no-cov` | `make unit` |
| End-to-end (real server) | `uv run pytest -m e2e --no-cov` | `make e2e` |
| One test | `uv run pytest tests/unit/test_governance.py -k audit --no-cov` | |
| Regenerate docs and dbt models | `uv run emblem docs` then `python tools/sync_dbt.py` | `make docs` |
| Build the package | `uv build` | |

CI fails if generated docs or dbt models are stale: after changing SQL models, the plan YAML, glossary or traceability, regenerate and commit.

## Part 6 · Debugging in VS Code (basic to advanced)

Open the folder (`code .`), accept the recommended extensions (Python, Debugpy, Ruff, YAML, Terraform, Mermaid). Select the interpreter `.venv` (Ctrl+Shift+P, "Python: Select Interpreter"). Launch configs: `.vscode/launch.json`; tasks (Ctrl+Shift+P, "Tasks: Run Task"): `.vscode/tasks.json`.

**Level 1: read before you step.**
- *Problems* panel (`Ctrl+Shift+M`) shows Ruff errors live; `uv run mypy` for types.
- Every pipeline failure is recorded in the warehouse. Look at the evidence first (stop the API server before this; DuckDB allows one writer):
  ```bat
  uv run python -c "import duckdb;c=duckdb.connect('build/emblem.duckdb',read_only=True);c.sql('select task,status,error from meta.pipeline_runs order by started_at desc limit 5').show()"
  ```
  Useful tables: `meta.pipeline_runs`, `meta.ingest_log`, `meta.schema_changes`, `meta.dq_results`, `meta.recon_results`, `meta.incidents`, `meta.audit_log`, `meta.events_inbox`, `meta.ai_usage`, `bronze.quarantine`.

**Level 2: breakpoints in the pipeline.** Run and Debug (Ctrl+Shift+D) → **2 · Demo pipeline (debug)**. Set a breakpoint in `src/emblem/pipelines/bronze.py` inside `ingest_dataset`. `justMyCode` is off so you can step into libraries. Use *Logpoints* (right-click gutter → Add Logpoint) instead of `print`.

**Level 3: breakpoints in the API.** **1 · API server (debug)**, then call an endpoint from Swagger. Break in `src/emblem/api/app.py` inside `dataset()` and in `src/emblem/security/rbac.py` `apply_policy` to watch masking decisions. Add a *conditional breakpoint* such as `claims["role"] == "sales_rep"`.

**Level 4: tests under the debugger.** Open a test file, choose **3 · Pytest: current file** (coverage is off, otherwise breakpoints misbehave). Terminal alternative: `uv run pytest tests/unit/test_bronze.py -x -s --no-cov --pdb` drops into `pdb` on failure.

**Level 5: end to end.** `tests/e2e/test_e2e.py` starts a real `uvicorn` process. See its output: `uv run pytest -m e2e --no-cov -s`. To debug the server side, start it yourself (Level 3) and call it with `tools/send_webhook.py` or Swagger.

**Level 6: SQL.** All gold logic is plain SQL in `src/emblem/data/sql/gold/*.sql`. Query the warehouse:
```bat
uv run python -c "import duckdb;c=duckdb.connect('build/emblem.duckdb',read_only=True);c.sql('select * from gold.mart_revenue_monthly order by 1').show()"
```

**Level 7: advanced.**
- *Attach to a running process:* `uv run python -m debugpy --listen 5678 --wait-for-client -m emblem serve`, then launch **5 · Attach**.
- *Quality check not firing?* Each check is one SQL statement in `src/emblem/data/quality/checks.yaml`; paste it into the Level 6 command. A check that errors **fails**; it never silently passes.
- *Plan milestone failing?* `uv run emblem plan verify` prints evidence per milestone; verifiers are in `src/emblem/plan/plan.py`.
- *Schema drift:* `uv run python -c "from emblem.sources.synthetic import generate;print(generate(batch=2)['bg.orders'][0])"` shows the renamed field `total`; the contract `aliases` maps it back.
- *Breaking drift:* `generate(batch=3, breaking_drift=True)` drops a required field; rows land in `bronze.quarantine` and the schema check fails (see `tests/integration/test_pipeline.py`).
- *Audit tamper test:* edit a row in `meta.audit_log`, then call `GET /v1/audit/verify` as `auditor`: `first_bad_seq` points at it.

## Part 7 · Contribution flow

1. Branch from `main`: `git switch -c feat/short-description`.
2. Write the **failing regression test first** (Part 8), then the change.
3. Run the Part 5 checks (lint, types, tests). If you touched SQL, plan, glossary or traceability: `uv run emblem docs` and `python tools/sync_dbt.py`.
4. Commit with Conventional Commits (the `commit-msg` hook enforces it): `feat(quality): add duplicate-order check`, `fix(api): cap page size`, `docs: clarify runbook`.
5. Push and open a PR into `main` (direct pushes are blocked):
   ```bat
   git push -u origin HEAD
   gh pr create --fill --title "feat(quality): add duplicate-order check"
   ```
   The **PR title** must be a Conventional Commit; it becomes the squash commit and decides the next version.
6. `ci-ok (required check)` must be green, one code-owner approval (not the author) and all threads resolved. Merge with **Squash and merge** or `gh pr merge --squash --delete-branch`.
7. Never edit `CHANGELOG.md` or `version` in `pyproject.toml` by hand; `release.yml` does it (Part 11).
8. Changes to contracts, system of record, policies, infra or `.github` need the owning reviewer (`.github/CODEOWNERS`).

**Rule: no enhancement or bug fix merges without regression tests.**

## Part 8 · Test catalogue

| Layer | Location | Covers |
|---|---|---|
| Unit | `tests/unit/test_contracts.py` | contract validation, alias/additive/missing-field handling, breaking vs additive diff |
| Unit | `tests/unit/test_bronze.py` | idempotent replay, new versions, quarantine, schema-change ledger, watermarks, rollback, retry/backoff |
| Unit | `tests/unit/test_mdm_forecast.py` | name/domain normalisation, entity-resolution rules, stable keys, Holt forecast |
| Unit | `tests/unit/test_governance.py` | RBAC/masking, encryption, tokens, audit-chain tamper detection, retention, webhook signatures, inbox/dead-letter |
| Unit | `tests/unit/test_architecture_audit.py` | system of record, platform scoring, audit categories, baseline, lineage, vendor scoring, Power BI model |
| Unit | `tests/unit/test_ai_incidents_plan.py` | embeddings, governed search, agent tools, severity/escalation, incident idempotency, all 14 plan milestones |
| Unit | `tests/unit/test_release_traceability.py` | release tool, JD traceability paths, dbt models in sync |
| Integration | `tests/integration/test_pipeline.py` | revenue vs independent computation, entity resolution, idempotent reruns, overlap, drift, lakehouse export |
| Integration | `tests/integration/test_quality.py` | every planted defect detected, clean checks pass, reconciliation root causes |
| Integration | `tests/integration/test_api.py` | auth, masking, audited 403s, webhooks, drain, dashboard, prod refuses unsafe config |
| Integration | `tests/integration/test_spark_parity.py` | Spark equals DuckDB (`-m spark`) |
| Integration | `tests/integration/test_airflow_dags.py` | DAGs import, standards, task order (`-m airflow`) |
| E2E | `tests/e2e/test_e2e.py` | real CLI + real uvicorn + HTTP user journey |

**Add a test.** Put `test_*.py` in the matching folder. Fixtures in `tests/conftest.py`: `fresh_con` (empty warehouse, mutate freely) and `demo_con` (full demo, read-mostly). Name tests as behaviours (`test_replay_is_noop`). Mark integration tests `pytestmark = pytest.mark.integration`, e2e `pytest.mark.e2e`.
**Modify a test** only when the *requirement* changed; change test and code in the same PR and say why.
**Bug fix recipe.** Reproduce with a failing test, confirm it fails for the right reason, fix, confirm green, keep the test forever.
**Add a data check:** append to `src/emblem/data/quality/checks.yaml` (SQL returning one number, threshold, owner action, runbook). **Add a source field:** edit `contracts.yaml`; typing and staging regenerate automatically.

## Part 9 · Publish the repository (public)

From the project root (the folder with `pyproject.toml`). The ZIP already holds one commit; check:
```bat
git status
git log --oneline
```
If it says "not a git repository", run `git init -b main`. Then:
```bat
git add -A
git commit -m "feat: world emblem data foundation showcase"

gh repo create world-emblem-data-foundation --public --description "Governed enterprise data foundation showcase: audit, system-of-record architecture, contract-driven idempotent pipelines (Python, SQL, Spark, Airflow, dbt), quality and reconciliation, RBAC/masking/audit, AI-ready governed access, and a machine-verified 90-day plan." --source . --remote origin --push

gh repo edit --add-topic data-engineering --add-topic python --add-topic uv --add-topic duckdb --add-topic spark --add-topic airflow --add-topic dbt --add-topic data-governance --add-topic data-quality --add-topic fastapi
```
(If you have nothing new to commit, the `commit` line says so; continue.) Before pushing run the secret scan (Part 4) and confirm `.env` is not tracked (`git ls-files .env` prints nothing). The repository is **public**: never commit a real key.

If your GitHub username is not `sm2774us`, replace it in `.github/CODEOWNERS`, `README.md` and `.github/ISSUE_TEMPLATE/config.yml` **before** the push:
```bash
grep -rl sm2774us . --exclude-dir=.git --exclude-dir=.venv | xargs sed -i 's/sm2774us/sm2774us/g'
```
(Windows: VS Code Replace in Files, Ctrl+Shift+H.) Then `git add -A && git commit -m "docs: set repository owner"`.

## Part 10 · Lock down the repository (run once, in this order)

Run inside the repository after the first push; `gh` fills in `:owner/:repo`. The multi-line `<<JSON` blocks need bash (Git Bash or WSL on Windows).

**1. Merge settings: squash only, branches deleted automatically**
```bash
gh repo edit --delete-branch-on-merge --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false
gh api -X PATCH repos/:owner/:repo -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY
```
The second command makes the squash commit use the PR title, which the release tool reads.

**2. Branch protection ruleset**
```bash
gh api -X POST repos/:owner/:repo/rulesets --input .github/rulesets/protect-main.json
```
`protect-main` enforces on `main`: no deletion, no force push, linear history, a PR with **one code-owner approval**, stale approvals dismissed, threads resolved, squash only, and the single status check `ci-ok (required check)` on an up-to-date branch. Bypass is limited to the GitHub Actions app (id 15368) so the approved release job can push the version commit and tag; humans cannot bypass. Change it later:
```bash
gh api repos/:owner/:repo/rulesets --jq '.[] | [.id,.name] | @tsv'
gh api -X PUT repos/:owner/:repo/rulesets/RULESET_ID --input .github/rulesets/protect-main.json
```

**3. No Dependabot or Renovate noise**
```bash
gh api -X DELETE repos/:owner/:repo/vulnerability-alerts
gh api -X DELETE repos/:owner/:repo/automated-security-fixes
```
The `guard` job fails any PR that adds Dependabot or Renovate config. Upgrade deliberately: `uv lock --upgrade` in a normal reviewed PR.

**4. Workflow token read-only by default**
```bash
gh api -X PUT repos/:owner/:repo/actions/permissions/workflow -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false
```

**5. Environments: the release approval gate**
```bash
ME=$(gh api user --jq .id)
gh api -X PUT repos/:owner/:repo/environments/release --input - <<JSON
{"prevent_self_review": false, "reviewers": [{"type": "User", "id": $ME}]}
JSON
gh api -X PUT repos/:owner/:repo/environments/dev
gh api -X PUT repos/:owner/:repo/environments/prod --input - <<JSON
{"prevent_self_review": false, "reviewers": [{"type": "User", "id": $ME}]}
JSON
```
Add teammates by numeric id (`gh api users/NAME --jq .id`).

**6. GitHub secret scanning (defence in depth next to gitleaks)**
```bash
gh api -X PATCH repos/:owner/:repo --input - <<JSON
{"security_and_analysis": {"secret_scanning": {"status": "enabled"}, "secret_scanning_push_protection": {"status": "enabled"}}}
JSON
```

**7. Verify**
```bash
gh repo view --json visibility,description,deleteBranchOnMerge,squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed
gh api repos/:owner/:repo/rulesets --jq '.[] | {name, enforcement}'
gh api repos/:owner/:repo/environments --jq '.environments[].name'
gh run list --limit 5
```

> **Working alone?** GitHub never lets an author approve their own PR, so with one required approval a solo maintainer cannot merge. Either add a collaborator (`gh api -X PUT repos/:owner/:repo/collaborators/USER -f permission=push`) or set `required_approving_review_count` to `0` and `require_code_owner_review` to `false` in `.github/rulesets/protect-main.json` and `PUT` it again (step 2). The release approval gate in step 5 stays manual either way.

**First CI run.** Open a tiny PR (fix a typo in `README.md`, title `docs: fix typo`). Watch **Actions**: `guard`, `secrets`, `verify`, `e2e`, `spark`, `airflow`, `dbt`, `docker`, `terraform`, then `ci-ok`. The author could not execute GitHub Actions, Docker builds or Terraform in the build sandbox, so expect to fix small environmental issues (a provider version, a Docker detail) in a PR; the failing log line tells you exactly where.

## Part 11 · Releases: automated, approval-based

Nothing is versioned by hand. Version and `CHANGELOG.md` come from the Conventional Commit titles of merged PRs (`tools/release.py`).

| Merged PR titles since the last tag | Next version |
|---|---|
| Only `docs`, `chore`, `ci`, `test`, `style` | None: no release, no approval prompt |
| At least one `fix`, `perf` or `refactor` | Patch (1.0.0 → 1.0.1) |
| At least one `feat` | Minor (1.0.0 → 1.1.0) |
| `!` after the type, or a `BREAKING CHANGE:` footer | Major (1.0.0 → 2.0.0) |

1. Merge your PR. Open **Actions → Release**; the `plan` job prints `release=true version=X.Y.Z`.
2. Open the `publish` job waiting for approval, **Review deployments**, tick `release`, **Approve and deploy**.
3. It runs ruff and tests on that exact commit, bumps `pyproject.toml` and `CHANGELOG.md`, commits `chore(release): vX.Y.Z [skip ci]`, tags, pushes, builds the container, pushes `ghcr.io/<owner>/world-emblem-data-foundation:<version>` and `:latest` with SBOM and provenance attestation, and creates the GitHub Release.
4. First release: no tag yet, so the version is whatever `pyproject.toml` says (1.0.0).

Preview locally (read-only): `uv run python tools/release.py plan`.
Verify the image attestation: `gh attestation verify oci://ghcr.io/sm2774us/world-emblem-data-foundation:1.0.0 --repo sm2774us/world-emblem-data-foundation`.
If the push step fails with **GH013 / protected branch**, the Actions bypass is missing: re-import the ruleset, or create a fine-grained token with `contents: write`, store it with `gh secret set RELEASE_TOKEN`, and add its owner to the bypass list.

## Part 12 · Housekeeping

`housekeeping.yml` runs every Sunday and on demand (`gh workflow run housekeeping.yml`). It deletes failed, cancelled, skipped and timed-out runs, then all successful runs except the newest, per workflow. Branch cleanup is automatic (Part 10 step 1). Local: `git fetch --prune`.

## Part 13 · Deploy (optional, manual, keyless, Azure)

Off by default: `deploy.yml` is skipped until `DEPLOY_ENABLED=true`.
1. Install and log in to Azure CLI: `winget install --id Microsoft.AzureCLI -e`, then `az login`.
2. Create the landing zone (storage with bronze/silver/gold, Key Vault, Log Analytics):
   ```bash
   cd infra/terraform/envs/dev
   terraform init
   terraform plan -var tenant_id=$(az account show --query tenantId -o tsv)
   terraform apply -var tenant_id=$(az account show --query tenantId -o tsv)
   ```
   (The `backend "azurerm"` block is commented out; configure remote state before any shared use.)
3. The workflow rolls an existing **Azure Container App** to a new image tag. Create one once (name `<CONTAINER_APP>-dev` in resource group `<RESOURCE_GROUP>-dev`; see `az containerapp create --help`) and a federated (OIDC) credential for this repo on an app registration with rights on that resource group. Put `EMBLEM_AUTH_SECRET` and `EMBLEM_WEBHOOK_SECRET` in Key Vault and reference them from the Container App; `EMBLEM_ENV=prod` refuses to start without them.
4. Set repository variables:
   ```bash
   gh variable set DEPLOY_ENABLED --body true
   gh variable set AZURE_CLIENT_ID --body "<app-registration-client-id>"
   gh variable set AZURE_TENANT_ID --body "<tenant-id>"
   gh variable set AZURE_SUBSCRIPTION_ID --body "<subscription-id>"
   gh variable set CONTAINER_APP --body "wedf-api"
   gh variable set RESOURCE_GROUP --body "rg-wedf"
   ```
5. Run: `gh workflow run deploy.yml -f environment=dev -f version=1.0.0`, then `gh run watch`. It ends with a `/readyz` smoke test and fails if it does not answer.

Steps 3 and 4 use your own Azure tenant and cannot be verified in advance: treat them as a checklist, not a guarantee.

## Part 14 · Where to change what

| I want to... | Edit | Then run |
|---|---|---|
| add a source column or dataset | `src/emblem/data/contracts/contracts.yaml` (demo data: `sources/synthetic.py`) | `uv run pytest -m "not e2e and not spark and not airflow"` |
| change a business definition | `src/emblem/data/sql/gold/*.sql`, `catalog/glossary.yaml` | `uv run emblem docs`, `python tools/sync_dbt.py` |
| add a data-quality check | `src/emblem/data/quality/checks.yaml` | `uv run emblem demo`, `uv run emblem quality` |
| change who may see what | `src/emblem/data/governance/policies.yaml` | `uv run pytest tests/unit/test_governance.py --no-cov` |
| change authority for a domain | `src/emblem/data/architecture/system_of_record.yaml` | `uv run emblem sor` |
| update the 90-day plan | `src/emblem/data/plan/plan_90_day.yaml` | `uv run emblem docs`, `uv run emblem plan verify` |
| change platform weights/scores | `src/emblem/data/architecture/platform_options.yaml` | `uv run emblem platform` |
| replace the assumed estate after discovery | `src/emblem/data/catalog/system_inventory.yaml` | `uv run emblem audit` |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `'uv' is not recognized` | Terminal opened before install | Close and reopen it; `winget install --id astral-sh.uv -e` |
| Python 3.14 not found | uv could not fetch it | Check network/proxy; `uv python install 3.14`; then `uv sync` |
| `No data yet` from CLI or API | Warehouse not built | `uv run emblem demo` |
| Dashboard `/` says "No data yet" | Server started before the demo | Run the demo, restart `uv run emblem serve` |
| `Could not set lock on file ... emblem.duckdb` | A running server holds the file | Stop the server (`Ctrl+C`) before CLI commands |
| Port 8000 in use | Old server | Stop it or `uv run emblem serve --port 8100` |
| Webhook returns 401 | Different secrets, or clock skew over 5 min | Use the identical `EMBLEM_WEBHOOK_SECRET` in both terminals |
| `send_webhook.py`: "Set EMBLEM_WEBHOOK_SECRET" | Variable not set in that terminal | `set` (cmd), `$env:` (PowerShell), `export` (bash) |
| `prod requires EMBLEM_AUTH_SECRET...` | `EMBLEM_ENV=prod` without secrets (by design) | Provide both, or use `EMBLEM_ENV=dev` locally |
| Spark test skipped | No pyspark or no Java | `uv sync --group spark`; install JDK 21 |
| Import errors after switching groups | Groups replace each other | Re-run the matching `uv sync --group ...` |
| CI "docs out of sync" / dbt sync test fails | Generated files stale | `uv run emblem docs` and `python tools/sync_dbt.py`, commit |
| Coverage below 85% | New code without tests | Add tests (Part 8) |
| `commit-msg` rejects a commit | Not Conventional Commits | `type(scope): subject`, e.g. `fix(api): cap page size` |
| Hooks not installed | Not a git repo when the installer ran | `git init -b main`, then `uv run python tools/install_hooks.py` |
| pre-commit warns gitleaks missing | Optional local tool | Install it (Part 1) or rely on CI |
| gitleaks reports a finding | Secret-like string | Remove it, rotate if real; never allow-list a real key |
| `guard` fails: PR title | Not `type(scope): subject` | Edit the title; the check re-runs |
| `guard` fails: dependabot/renovate file | Banned by policy | Delete it; keep Dependabot disabled (Part 10 step 3) |
| Cannot merge my own PR | Ruleset needs another reviewer | See "Working alone?" in Part 10 |
| `gh api .../rulesets` returns 422 | Ruleset already exists | Use the `PUT` form (Part 10 step 2) |
| Release run shows "Waiting" | The approval gate is working | Approve the `release` environment (Part 11) |
| Release stops after `plan` | No releasable commit since the last tag | Expected for docs-only changes |
| Release: GH013 protected branch | Bypass missing | See end of Part 11 |
| Docker build cannot find `uv.lock` | Wrong build context | Run from the project root with `-f infra/docker/Dockerfile .` |
| Terraform cannot download azurerm | Registry blocked | Retry on an unrestricted network |
| WSL very slow | Repo on `/mnt/c` | Move it into `~/code` |
| Windows: `make` not found | Not installed | Use the `uv run` equivalents (Part 5) |
