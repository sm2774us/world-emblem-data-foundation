# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning: [SemVer](https://semver.org/).

## [1.0.0] - 2026-10-01

### Added
- Current-state audit engine (inventory, scored findings, baseline scorecard, flow map) and system-of-record matrix with validator.
- Contract-driven medallion pipeline (idempotent bronze, generated silver, SQL gold, entity resolution, forecast), Spark parity job, Airflow DAGs, dbt project.
- Quality engine (7 dimensions), six reconciliations, incident response with escalation and runbooks, Prometheus metrics.
- Governance: RBAC and masking, field encryption, tamper-evident audit chain, retention, signed webhooks.
- AI enablement: approved-document vector index, allow-listed agent tools, usage monitoring; Power BI semantic model generator.
- Machine-verifiable 90-day plan, platform decision matrix, vendor review scorecard, HTML showcase dashboard and governed API.
- CI/CD: PR verification with required check, gitleaks, CodeQL, release with approval gate, OIDC deploy, housekeeping, protect-main ruleset.

### Known limitations
- Data is synthetic; the estate in `system_inventory.yaml` is an assumed hypothesis built from the job description.
- Terraform, Docker builds and GitHub Actions were not executed in the authoring sandbox (they are validated by CI on first push).
