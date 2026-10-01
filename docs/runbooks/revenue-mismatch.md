# Runbook: revenue reconciliation break
**Triggers:** `dq_invoice_matches_lines`, reconciliation `revenue`.
**Definition:** revenue = posted invoices in Business Central (USD). Compare to shipped order lines.
1. Read the root cause text: price overrides vs shipped orders without invoice.
2. List `gold.fact_revenue WHERE abs(lines_variance) > 0.01` and shipped orders with no invoice (`stg_bc__sales_orders` anti-join `stg_bc__invoices`).
3. **Fix at the source (Finance):** override requires approval + reason code; unbilled shipments are invoiced or flagged; month-end close checklist includes this reconciliation.
4. Month-end pack must only use `mart_revenue_monthly` once the break is explained or resolved.
**Escalation:** SEV1/SEV2: data engineer immediately, Finance within 15 min (SEV1), CTO within 60 min.
