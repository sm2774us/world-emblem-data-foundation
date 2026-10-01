# 90-Day Plan: Senior Data Engineer / Data Architect, World Emblem International

> Generated from `src/emblem/data/plan/plan_90_day.yaml` by `uv run emblem plan render`. Do not edit by hand. Baselines marked *assumed* are hypotheses to confirm in Days 1-30.
> Every milestone is verified by code: `uv run emblem plan verify`.

## Days 1-30: Understand the environment

**Goal:** Know every system, flow, owner and risk; publish an honest baseline.

### M1.1 (days 1-7): Inventory systems, data stores, integrations, jobs, reports and owners

**JD requirement:** Inventory the major systems, data stores, integrations, reports, and owners.

**Exact steps**

1. Day 1: obtain read-only admin views (BC web client + API setup, HubSpot settings, BigCommerce control panel, Optimizely, ad platforms, MES SQL Server catalog, Azure/M365 tenant, Power BI admin portal).
2. Day 1-3: pull machine-readable inventories: BC API/job-queue entries, HubSpot workflows + private apps, BigCommerce webhooks + API accounts, SQL Agent jobs, Windows Task Scheduler, Power BI workspaces and refresh schedules.
3. Day 3-5: record each item in catalog/system_inventory.yaml (system, integration, job, report, owner, admin, store, access, mechanism, schedule, secret store, documented/monitored/retries/idempotent).
4. Day 5-7: run the audit engine; review every finding with the system admin; mark each flag CONFIRMED or REFUTED in the YAML (git history = audit trail).

**Exact changes**

- Create the catalog as code (YAML in Git) instead of a spreadsheet; PR review by owners via CODEOWNERS.
- Assign an interim owner to every ownerless item; no item stays 'null' past Day 10.

**Demonstrated by:** `src/emblem/data/catalog/system_inventory.yaml`, `src/emblem/catalog/audit.py`  
**Run it:** `uv run emblem audit`  
**Exit criteria:** 100% of systems/integrations/jobs/reports inventoried with an owner and admin; findings list reviewed with owners.  
**Metric:** Items with accountable owner: ~83% (assumed) -> 100%

### M1.2 (days 3-15): Meet technical teams and departments; capture pain points and planned projects

**JD requirement:** Meet with technical teams and business departments to understand current processes, pain points, and planned projects.

**Exact steps**

1. Day 3-10: 45-minute interviews: CTO, Infrastructure, Applications (BC), Finance, Operations, Ecommerce, Marketing, Sales, Director of AI. Same script: what decisions use data, which numbers are disputed, what breaks monthly.
2. Day 8-12: capture the disputed definitions (revenue, order, active customer, on-hand) with the owning leader and write them into catalog/glossary.yaml.
3. Day 12-15: collect planned projects (AI agents, MicroSaaS apps) and their data needs into downstream_consumers.

**Exact changes**

- Each definition gets exactly one owning department and one gold model that implements it.
- Publish a 1-page 'what I heard' readback to every interviewee for correction.

**Demonstrated by:** `src/emblem/data/catalog/glossary.yaml`  
**Run it:** `uv run emblem lineage --json`  
**Exit criteria:** Every disputed KPI has an owner, a written definition and a target model.  
**Metric:** KPIs with signed-off definition: 0 of 7 -> 7 of 7

### M1.3 (days 8-22): Map highest-risk and highest-value data flows

**JD requirement:** Map the highest-risk and highest-value data flows.

**Exact steps**

1. Day 8-14: trace customer, product, order, revenue, inventory, marketing and production end to end (source field -> integration -> report) for the 3 flows with the biggest money exposure: web order -> ERP -> invoice, inventory ERP -> web, ad spend -> ROI.
2. Day 14-20: score each flow by value (revenue touched) x risk (missing controls, weak secrets, manual steps) using the audit severity model.
3. Day 20-22: draw the as-is map from data (flow_map), colour integrations red/amber/green by control coverage.

**Exact changes**

- Generate maps from YAML/lineage code so they cannot drift from reality; no hand-drawn Visio.

**Demonstrated by:** `src/emblem/catalog/lineage.py`, `docs/lineage.md`  
**Run it:** `uv run emblem lineage`  
**Exit criteria:** Top-3 value flows and top-3 risk flows documented with owners and failure modes.  
**Metric:** Integrations rated red: ~6 of 8 (assumed) -> known and prioritised

### M1.4 (days 15-30): Establish the baseline for quality, reliability, security and documentation

**JD requirement:** Establish an initial baseline for data quality, reliability, security, and documentation.

**Exact steps**

1. Day 15-20: stand up a read-only landing zone (bronze) with extracts from BC, HubSpot, BigCommerce and ad platforms using service principals with read scopes only.
2. Day 20-25: run the 26-check quality suite and the 6 reconciliations (orders, order value, revenue, inventory, customer counts) against that landing zone.
3. Day 25-28: compute the scorecard: reliability, security, documentation, ownership, automation, data quality.
4. Day 28-30: present the baseline and the planted/real defects found, each with business impact in dollars or hours.

**Exact changes**

- Open one incident per failing control with severity, owner, runbook and a 'fix at the source' action.

**Demonstrated by:** `src/emblem/quality/checks.py`, `src/emblem/quality/reconcile.py`, `src/emblem/data/quality/checks.yaml`  
**Run it:** `uv run emblem demo`  
**Exit criteria:** Written baseline scorecard approved by the CTO; every break has an owner.  
**Metric:** Automated checks running daily: 0 -> 26

## Days 31-60: Define the plan

**Goal:** Decide who owns what, where data lives and how it flows; get sign-off.

### M2.1 (days 31-40): System-of-record matrix for critical domains (with field-level authority)

**JD requirement:** Create the system-of-record matrix for critical data domains.

**Exact steps**

1. Day 31-34: for each of 10 domains list which system creates, which edits, which reads; record conflicts (e.g. HubSpot and BC both editing company).
2. Day 34-38: workshop with each domain owner to choose ONE authority; allow field exceptions only where another system is genuinely better (web visibility, lifecycle stage).
3. Day 38-40: encode as system_of_record.yaml; validator fails CI if an authority does not host the domain or a non-authority writes into it.

**Exact changes**

- Single-writer rule: only the authority writes a domain; others get read-only copies or field-scoped writes.
- Retire INT-04 (Zapier BC->HubSpot) and fold INT-03 into one governed company flow.

**Demonstrated by:** `src/emblem/data/architecture/system_of_record.yaml`, `src/emblem/architecture/sor.py`  
**Run it:** `uv run emblem sor`  
**Exit criteria:** Matrix signed by the 5 business owners; validator green in CI.  
**Metric:** Domains with one authority: ~4 of 10 (assumed) -> 10 of 10

### M2.2 (days 36-48): Common business entities, identifiers and shared definitions

**JD requirement:** Define common business entities and the most important shared data definitions.

**Exact steps**

1. Day 36-40: define keys: company_key (resolved), contact_key (email hash), product_key (BC item no.), order_no, revenue_key, inventory_key, location_key, work_order_key.
2. Day 40-44: build entity resolution for companies (exact normalised name, shared non-free domain, fuzzy name >= 0.92) with confidence + match rule stored per record.
3. Day 44-48: implement the common models as SQL (dim_company, dim_contact, dim_product, dim_location, fact_order_line, fact_revenue, fact_inventory_snapshot, fact_production).

**Exact changes**

- Keys are deterministic and stable (hash of lowest source id), so re-runs never renumber customers.
- Matches below threshold go to a steward review queue instead of auto-merging.

**Demonstrated by:** `src/emblem/pipelines/mdm.py`, `src/emblem/data/sql/gold`  
**Run it:** `uv run emblem run`  
**Exit criteria:** All 8 entities materialised with unique keys; duplicate-customer rate measured.  
**Metric:** Duplicate customer records: 5% of ERP cards (planted) -> 0 unmerged

### M2.3 (days 41-52): Target architecture, data platform and tool recommendation

**JD requirement:** Present the target architecture, governance model, security approach, and recommended technology plan.

**Exact steps**

1. Day 41-45: draft medallion architecture (bronze raw, silver typed/conformed, gold governed) with batch, event and API paths; ADR for each major choice.
2. Day 45-50: score Fabric, Databricks, Snowflake, BigQuery, Synapse and Redshift against weighted criteria; run weight-sensitivity analysis.
3. Day 50-52: present options, cost bands and a recommendation; keep pipeline code portable (SQL + Spark + Delta/Parquet) so the platform choice is reversible.

**Exact changes**

- Business Central stays an ERP: no analytics or AI workload runs inside it.
- Orchestration in Airflow (code-first, testable); transformations as versioned SQL/dbt models.

**Demonstrated by:** `src/emblem/data/architecture/platform_options.yaml`, `docs/ARCHITECTURE.md`, `docs/adr`  
**Run it:** `uv run emblem platform`  
**Exit criteria:** CTO approves platform and tooling; ADRs merged.  
**Metric:** Decision robustness: n/a -> winner holds under +/-50% weight change

### M2.4 (days 45-56): Governance model and security approach

**JD requirement:** Establish practical standards for data ownership, access, classification, retention, and approved use.

**Exact steps**

1. Day 45-48: classify every contract column (public/internal/confidential/pii/restricted).
2. Day 48-52: define roles and dataset entitlements; masking per classification; field encryption for restricted columns; keys in Key Vault.
3. Day 52-56: turn on audit logging with a hash chain; set retention per dataset; review with IT and Legal.

**Exact changes**

- Access via governed gold views and APIs only; revoke direct production-database grants for BI and AI.
- Secrets move to Key Vault; plaintext and personal tokens rotated.

**Demonstrated by:** `src/emblem/data/governance/policies.yaml`, `src/emblem/security`  
**Run it:** `uv run emblem governance`  
**Exit criteria:** Policies approved by IT and Legal; audit chain verifies; retention dry-run reviewed.  
**Metric:** Integrations on vaulted secrets: ~25% (assumed) -> 100%

### M2.5 (days 52-60): Prioritised roadmap by business value, risk, effort and AI readiness

**JD requirement:** Create a prioritized roadmap based on business value, risk, effort, and AI readiness.

**Exact steps**

1. Day 52-56: list candidate data products and fixes; score value, risk reduction, AI readiness (1-5) and effort (1-5).
2. Day 56-60: rank by (value + risk + AI readiness) / effort; agree top 3 with the CTO and department leaders.

**Exact changes**

- First pipeline = web order -> ERP -> revenue reconciliation (highest value and risk).

**Demonstrated by:** `src/emblem/plan/plan.py`  
**Run it:** `uv run emblem plan roadmap`  
**Exit criteria:** Ranked roadmap with owners and dates accepted.  
**Metric:** Backlog items scored: 0 -> all

## Days 61-90: Prove the approach

**Goal:** Ship one governed data product end to end, with tests, monitoring and standards others can copy.

### M3.1 (days 61-75): Deliver the first governed pipeline / shared data product

**JD requirement:** Deliver the first high-value governed pipeline or shared data product.

**Exact steps**

1. Day 61-65: write data contracts for BC orders/lines/invoices and BigCommerce orders; generate staging models from them.
2. Day 65-70: build idempotent bronze ingest (content-hash dedupe, watermark, quarantine) and gold revenue and order models.
3. Day 70-75: publish mart_revenue_monthly as the single Finance-approved revenue definition; cut the month-end pack over to it.

**Exact changes**

- Retry with exponential backoff; transactions per dataset; replays are no-ops.
- Schema drift: known renames mapped via contract aliases, additive fields logged, breaking changes quarantined.

**Demonstrated by:** `src/emblem/pipelines/bronze.py`, `src/emblem/pipelines/staging.py`, `src/emblem/data/contracts/contracts.yaml`  
**Run it:** `uv run emblem run`  
**Exit criteria:** Month-end revenue reproduced from the governed mart; reruns are provably idempotent.  
**Metric:** Month-end close data prep: manual, days (assumed) -> automated, minutes

### M3.2 (days 70-82): Automated testing, monitoring, reconciliation and incident response on the pilot

**JD requirement:** Add automated testing, monitoring, documentation, and reconciliation to the selected use case.

**Exact steps**

1. Day 70-74: enable quality checks (completeness, accuracy, duplication, freshness, consistency, volume, schema) in the DAG; failures stop downstream publish for critical checks.
2. Day 74-78: schedule reconciliation for orders, revenue, inventory and customer counts with tolerances and root-cause text.
3. Day 78-82: wire incidents: severity matrix, owner routing, escalation ladder, runbook links, auto-resolve; Prometheus metrics for pipeline health.

**Exact changes**

- A reconciliation break opens an incident for the BUSINESS OWNER to fix at source; Data Platform does not patch the report.

**Demonstrated by:** `src/emblem/ops/incidents.py`, `src/emblem/ops/monitor.py`, `dags`, `docs/runbooks`  
**Run it:** `uv run emblem incidents`  
**Exit criteria:** Every failing check has an incident with owner, runbook and escalation; metrics scraped.  
**Metric:** Mean time to detect a feed outage: days (assumed) -> < 1 hour

### M3.3 (days 75-85): Governed access for reporting, AI agents and internal apps

**JD requirement:** Prepare structured and approved data for AI agents, retrieval systems, automations, and internal MicroSaaS applications.

**Exact steps**

1. Day 75-78: publish the Power BI semantic model (relationships, DAX measures, RLS roles) over gold only.
2. Day 78-82: stand up the governed API (RBAC, masking, audit) and the AI retrieval index of approved non-PII documents.
3. Day 82-85: register agent tools as allow-listed parameterised queries; log and alert on usage.

**Exact changes**

- Direct production access for reports and AI is switched off; every consumer uses gold, API or semantic model.

**Demonstrated by:** `src/emblem/reporting/semantic_model.py`, `src/emblem/api/app.py`, `src/emblem/ai`  
**Run it:** `uv run emblem serve`  
**Exit criteria:** One BI report and one agent tool run on governed access with audit evidence.  
**Metric:** Consumers on direct production access: ~3 (assumed) -> 0

### M3.4 (days 78-86): Engineering standards, vendor accountability and operating process

**JD requirement:** Publish the initial engineering standards and operating process for future integrations.

**Exact steps**

1. Day 78-82: publish standards (contracts, idempotency, retries, tests, CI, secrets, naming, change process) and the integration intake checklist.
2. Day 82-86: score vendor-built integrations on documentation, security, maintainability and delivery quality; issue written acceptance conditions.

**Exact changes**

- No integration goes live without a contract, a runbook, tests, monitoring and an owner (enforced in PR template and CI).

**Demonstrated by:** `docs/ENGINEERING-STANDARDS.md`, `src/emblem/governance/vendor.py`, `.github/PULL_REQUEST_TEMPLATE.md`  
**Run it:** `uv run emblem vendors`  
**Exit criteria:** Standards published; vendors have dated remediation commitments.  
**Metric:** Vendor integrations meeting standard: 0 of 2 -> 2 of 2 with dates

### M3.5 (days 84-90): Updated roadmap, staffing recommendation, budget view and milestones

**JD requirement:** Provide an updated roadmap, staffing recommendation, budget view, and delivery milestones.

**Exact steps**

1. Day 84-88: re-score the roadmap with measured effort from the pilot; size staffing (data engineer, analytics engineer) and platform run cost.
2. Day 88-90: present results versus the Day-30 baseline and the next two quarters of milestones.

**Exact changes**

- Budget is a range with explicit assumptions, refreshed each quarter.

**Demonstrated by:** `src/emblem/data/plan/plan_90_day.yaml`  
**Run it:** `uv run emblem plan budget`  
**Exit criteria:** Roadmap, staffing and budget accepted by the CTO.  
**Metric:** Baseline vs Day-90 scorecard: Day 30 -> improvement on every axis

## Prioritised roadmap

| Rank | ID | Item | Value | Risk | AI | Effort | Priority |
|---|---|---|---|---|---|---|---|
| 1 | R5 | Secrets to Key Vault and revoke direct DB access | 3 | 5 | 2 | 2 | 5.0 |
| 2 | R1 | Web order -> ERP reconciliation and connector hardening | 5 | 5 | 3 | 3 | 4.33 |
| 3 | R2 | Governed revenue mart and month-end automation | 5 | 4 | 3 | 3 | 4.0 |
| 4 | R3 | Inventory event-driven sync BC -> web | 4 | 4 | 3 | 3 | 3.67 |
| 5 | R7 | AI retrieval index and agent tool gateway | 4 | 2 | 5 | 3 | 3.67 |
| 6 | R6 | Marketing ROI mart and ad-spend automation | 3 | 2 | 2 | 2 | 3.5 |
| 7 | R4 | Golden company and contact (MDM) with steward queue | 4 | 3 | 5 | 4 | 3.0 |
| 8 | R8 | Production yield and scrap mart from MES | 3 | 2 | 3 | 3 | 2.67 |

## Budget view (annual, USD)

| Item | Low | High |
|---|---|---|
| Data platform capacity (low-high) | 36,000 | 78,000 |
| Orchestration and monitoring (managed Airflow or AKS) | 6,000 | 18,000 |
| Security tooling (Key Vault | 3,000 | 9,000 |
| Vendor remediation work | 10,000 | 40,000 |
| Analytics engineer (loaded cost) | 120,000 | 160,000 |
| **Total** | **175,000** | **305,000** |

Assumptions: Fabric F64-class capacity or Databricks equivalent; Key Vault + Log Analytics; 1 additional analytics engineer from Q3
