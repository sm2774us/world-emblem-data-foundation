# Runbook: duplicate or incomplete customer records
**Triggers:** `dq_company_duplicates_in_erp`, `dq_bc_customer_email_complete`, `dq_hs_contact_email_complete`, `dq_golden_company_coverage`, reconciliation `customer_count`.
**Impact:** split revenue per customer, wrong credit exposure, duplicate marketing contact.
1. Confirm in `gold.dim_company` (`duplicate_in_erp`, `bc_customer_nos`) and `silver.xref_company` (`match_rule`, `confidence`).
2. Matches with confidence < 0.95 (`fuzzy_name`): steward reviews before any merge. Exact name / shared domain: safe to merge.
3. **Fix at the source:** Finance merges the BC customer cards (BC merge tool) and enables duplicate detection on create; Sales assigns an owner and requires email on HubSpot forms.
4. Re-run `uv run emblem run`; the incident auto-resolves when the check passes. Never delete golden keys: `company_key` is derived from the lowest source id and stays stable.
**Escalation:** SEV2 data engineer -> Finance owner (4 h) -> CTO (1 business day).
