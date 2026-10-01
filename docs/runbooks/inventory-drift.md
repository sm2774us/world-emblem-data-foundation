# Runbook: web stock out of sync with ERP
**Triggers:** `dq_web_inventory_in_sync`, reconciliation `inventory`.
1. `gold.fact_inventory_snapshot` shows `web_variance` per SKU. ERP on-hand is authoritative.
2. Check JOB-01 (nightly CSV export) and INT-02 logs. Stale or failed export is the usual cause.
3. **Fix at the source (Ecommerce + Operations):** replace the nightly CSV with an event-driven push from BC (roadmap R3); until then alert on export failure and re-run the job.
4. Overselling risk: temporarily hide SKUs with large negative variance in the storefront.
