# Runbook: invalid values (negative quantity, zero price, future date, orphan reference)
**Triggers:** `dq_line_quantity_positive`, `dq_line_price_nonzero`, `dq_order_not_future_dated`, `dq_orphan_order_customer`, `dq_scrap_rate_plausible`.
1. Query the offending rows from `silver.stg_*` (the check SQL is in `data/quality/checks.yaml`).
2. Decide with the owner: legitimate (returns, samples, blanket orders) -> encode as a rule; error -> correct at the source.
3. **Fix at the source:** add the validation in Business Central (quantity > 0, order date <= today, mandatory customer FK). Do not filter the rows in reports.
4. Re-run quality; incident auto-resolves.
