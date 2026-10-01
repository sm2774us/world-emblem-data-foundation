# Runbook: pipeline failure, missing orders, volume collapse
**Triggers:** `dq_web_orders_reach_erp`, `dq_volume_*`, `dq_stg_pk_unique_orders`, `dq_bc_item_price_complete`, any failed task in `meta.pipeline_runs`, Airflow `on_failure_callback`.
1. `SELECT * FROM meta.pipeline_runs WHERE status='failed' ORDER BY started_at DESC` and `meta.ingest_log` (attempts, quarantined).
2. Volume collapse: ask the source owner whether the extract is complete; replay the window (replays are no-ops for rows already loaded).
3. Orders missing in ERP: `gold.exc_web_orders_missing_in_erp` is the exception queue; the connector (INT-01) needs retry + dead-letter.
4. Dead-lettered webhook events: `SELECT * FROM meta.events_inbox WHERE status='dead_letter'`; fix mapping, set status back to `received`, call `POST /v1/events/drain`.
5. **Fix at the source:** owning team + vendor harden the connector; Data Platform adds a contract/test so it cannot regress silently.
