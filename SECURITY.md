# Security policy

Report vulnerabilities privately via GitHub **Security > Report a vulnerability**; do not open a public issue. Acknowledgement within 3 business days.

- Demonstration platform with **synthetic data only**. No real personal data should ever be loaded into a dev environment.
- `EMBLEM_ENV=prod` refuses to start without `EMBLEM_AUTH_SECRET` and `EMBLEM_WEBHOOK_SECRET`, and disables `/v1/auth/dev-token` and `/docs`.
- Secrets are never committed: `gitleaks` runs in pre-commit, on every PR (full history) and weekly. See `.gitleaks.toml`.
- Threat model summary: SQL injection (parameterised queries; dataset names allow-listed from `information_schema`), webhook forgery/replay (HMAC + timestamp), privilege escalation (RBAC from `policies.yaml`, CODEOWNERS on policy files), audit tampering (hash chain), supply chain (actions pinned by SHA, locked dependencies, provenance attestation, SBOM).
