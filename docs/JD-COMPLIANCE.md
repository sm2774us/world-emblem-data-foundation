# JD compliance matrix (generated)

| Section | Requirement | Evidence | Demo |
|---|---|---|---|
| 1 Audit | Inventory of data sources/databases/APIs/integrations/jobs/reports/owners/downstream users | `src/emblem/data/catalog/system_inventory.yaml` `src/emblem/catalog/audit.py` | `emblem audit` |
| 1 Audit | Map how customer/product/order/revenue/inventory/marketing/production data moves | `src/emblem/catalog/lineage.py` `docs/lineage.md` | `emblem lineage` |
| 1 Audit | Identify duplicates/missing ownership/weak controls/manual work/recon gaps/security risks/fragile integrations | `src/emblem/catalog/audit.py` `tests/unit/test_architecture_audit.py` | `emblem audit` |
| 1 Audit | Document current architecture and baseline | `docs/ARCHITECTURE.md` `src/emblem/catalog/audit.py` | `emblem audit --baseline` |
| 2 Architecture | Authoritative system per domain and field | `src/emblem/data/architecture/system_of_record.yaml` `src/emblem/architecture/sor.py` | `emblem sor` |
| 2 Architecture | Scalable target architecture without turning one platform into the data platform | `docs/ARCHITECTURE.md` `docs/adr/0001-medallion-and-erp-boundary.md` | `docs/ARCHITECTURE.md` |
| 2 Architecture | Common models and identifiers (customers/companies/products/orders/revenue/inventory/locations/production) | `src/emblem/data/sql/gold` `src/emblem/pipelines/mdm.py` | `emblem run` |
| 2 Architecture | Standards for batch/real-time/APIs/contracts/schema changes/retention | `docs/ENGINEERING-STANDARDS.md` `src/emblem/contracts.py` `src/emblem/ops/events.py` | `emblem contracts` |
| 2 Architecture | Recommend data platform and integration tools | `src/emblem/data/architecture/platform_options.yaml` `src/emblem/architecture/platform.py` `docs/adr/0002-platform-recommendation.md` | `emblem platform` |
| 3 Engineering | Pipelines across BC/HubSpot/ecommerce/marketing/production/internal apps | `src/emblem/pipelines/bronze.py` `src/emblem/sources/synthetic.py` `dags/emblem_daily_elt.py` | `emblem run` |
| 3 Engineering | Tested transformations to consistent reusable data | `src/emblem/data/sql/gold` `tests/integration/test_pipeline.py` `dbt_project/models` | `pytest -m integration` |
| 3 Engineering | Secure APIs and data services for analytics/AI/internal tools | `src/emblem/api/app.py` `tests/integration/test_api.py` | `emblem serve` |
| 3 Engineering | Source control/automated testing/deployment pipelines/release practices | `.github/workflows/pr-verification.yml` `.github/workflows/release.yml` `tools/release.py` | `GitHub Actions` |
| 3 Engineering | Recover from failures/handle changing schemas/avoid duplicate processing | `src/emblem/pipelines/retry.py` `src/emblem/pipelines/bronze.py` `tests/unit/test_bronze.py` | `pytest tests/unit/test_bronze.py` |
| 3 Engineering | Apache Spark | `src/emblem/spark_jobs/conform_orders.py` `tests/integration/test_spark_parity.py` | `pytest -m spark` |
| 3 Engineering | Apache Airflow | `dags/emblem_daily_elt.py` `dags/emblem_events_drain.py` `tests/integration/test_airflow_dags.py` | `pytest -m airflow` |
| 3 Engineering | dbt / Dagster / similar transformation tooling | `dbt_project/dbt_project.yml` `dbt_project/models` `src/emblem/pipelines/sqlmodels.py` | `make dbt` |
| 3 Engineering | Webhooks and event-driven integrations | `src/emblem/ops/events.py` `tests/integration/test_api.py` | `emblem serve` |
| 4 Quality | Automated checks for completeness/accuracy/duplication/freshness/consistency | `src/emblem/data/quality/checks.yaml` `src/emblem/quality/checks.py` | `emblem quality` |
| 4 Quality | Reconcile orders/revenue/inventory/customer counts | `src/emblem/quality/reconcile.py` `tests/integration/test_quality.py` | `emblem reconcile` |
| 4 Quality | Monitor pipeline health/failed jobs/delays/schema changes/volume changes | `src/emblem/ops/monitor.py` `src/emblem/quality/checks.py` | `GET /metrics` |
| 4 Quality | Incident response and escalation | `src/emblem/ops/incidents.py` `docs/runbooks` | `emblem incidents` |
| 4 Quality | Resolve problems at the source not the report | `src/emblem/ops/incidents.py` `src/emblem/data/quality/checks.yaml` | `emblem incidents` |
| 5 Governance | Ownership/access/classification/retention/approved-use standards | `src/emblem/data/governance/policies.yaml` `src/emblem/security/retention.py` | `emblem governance` |
| 5 Governance | RBAC/encryption/audit logging/PII protection | `src/emblem/security/rbac.py` `src/emblem/security/crypto.py` `src/emblem/security/audit.py` | `pytest tests/unit` |
| 5 Governance | Definitions/lineage/integration docs/runbooks/architecture diagrams | `src/emblem/data/catalog/glossary.yaml` `docs/lineage.md` `docs/runbooks` | `emblem docs` |
| 5 Governance | Partner with IT/Legal/business on privacy/security/compliance | `SECURITY.md` `.github/CODEOWNERS` `docs/ENGINEERING-STANDARDS.md` | `CODEOWNERS review` |
| 5 Governance | Department leaders own business meaning and quality | `src/emblem/data/catalog/glossary.yaml` `src/emblem/data/architecture/system_of_record.yaml` | `emblem sor` |
| 6 Enablement | Trusted reusable models for reporting/dashboards/forecasting | `src/emblem/data/sql/gold` `src/emblem/pipelines/forecast.py` | `emblem run` |
| 6 Enablement | Power BI semantic model / governed reporting layer | `src/emblem/reporting/semantic_model.py` `tests/unit/test_architecture_audit.py` | `emblem semantic` |
| 6 Enablement | Structured approved data for AI agents/RAG/vector search/automations/MicroSaaS | `src/emblem/ai/index.py` `src/emblem/ai/tools.py` `src/emblem/ai/embeddings.py` | `GET /v1/ai/search` |
| 6 Enablement | Prevent uncontrolled direct production access | `src/emblem/api/app.py` `src/emblem/security/rbac.py` | `GET /v1/datasets/{name}` |
| 6 Enablement | Monitor how AI and internal apps use data | `src/emblem/ai/tools.py` `tests/unit/test_ai_incidents_plan.py` | `GET /v1/ai/usage` |
| 7 Leadership | Translate technical issues into business risks/options/costs | `docs/90-DAY-PLAN.md` `src/emblem/plan/plan.py` | `emblem plan render` |
| 7 Leadership | Review vendor-built integrations and hold partners accountable | `src/emblem/governance/vendor.py` `src/emblem/data/governance/vendor_reviews.yaml` | `emblem vendors` |
| 7 Leadership | Standards and training for how teams collect/define/share/use data | `docs/ENGINEERING-STANDARDS.md` `docs/TRAINING.md` | `docs/TRAINING.md` |
| 90 Days | Days 1-30 understand the environment | `docs/90-DAY-PLAN.md` `src/emblem/plan/plan.py` | `emblem plan verify` |
| 90 Days | Days 31-60 define the plan | `docs/90-DAY-PLAN.md` `src/emblem/data/plan/plan_90_day.yaml` | `emblem plan verify` |
| 90 Days | Days 61-90 prove the approach | `docs/90-DAY-PLAN.md` `src/emblem/data/plan/plan_90_day.yaml` | `emblem plan verify` |
| Required | SQL, Python, Spark, Airflow | `pyproject.toml` `src/emblem/data/sql/gold` `src/emblem/spark_jobs/conform_orders.py` `dags` | `uv sync --all-groups` |
| Required | Data modelling for operational/analytics/shared enterprise data | `src/emblem/data/sql/gold` `docs/ARCHITECTURE.md` | `emblem run` |
| Required | Cloud data platform/warehouse/lakehouse | `infra/terraform` `src/emblem/pipelines/lakehouse.py` `docs/adr/0002-platform-recommendation.md` | `emblem lakehouse` |
| Required | Git/code review/automated tests/deployment pipelines | `.github/workflows` `.github/rulesets/protect-main.json` `.github/CODEOWNERS` | `GitHub` |
| Required | Explain complex issues to executives | `README.md` `docs/90-DAY-PLAN.md` `WALKTHROUGH.md` | `README.md` |
| Preferred | Business Central / ERP integration | `src/emblem/sources/synthetic.py` `src/emblem/data/contracts/contracts.yaml` | `emblem generate` |
| Preferred | HubSpot / ecommerce / marketing / manufacturing data | `src/emblem/data/contracts/contracts.yaml` | `emblem contracts` |
| Preferred | Fabric/ADF/Synapse/Databricks/Snowflake/BigQuery/Redshift evaluated | `src/emblem/architecture/platform.py` `infra/terraform` | `emblem platform` |
| Preferred | MDM/metadata catalog/lineage/data contracts/schema governance | `src/emblem/pipelines/mdm.py` `src/emblem/catalog/lineage.py` `src/emblem/contracts.py` | `emblem lineage` |
| Security | No hardcoded secrets (gitleaks) | `.gitleaks.toml` `.github/workflows/pr-verification.yml` `.githooks/pre-commit` | `make secrets` |
