# Runbook: stale feed (freshness breach)
**Triggers:** `dq_fresh_ad_spend`, `dq_fresh_sales_orders`, `dq_fresh_production`.
1. Compare `max(_source_updated_at)` with the contract `freshness_hours`.
2. Check credentials/token expiry (ad platforms), BC job queue, MES export job on the plant server.
3. **Fix at the source:** owner re-authorises or restarts the job; add the job to Airflow with SLA and alerting so the next outage is detected within the hour.
