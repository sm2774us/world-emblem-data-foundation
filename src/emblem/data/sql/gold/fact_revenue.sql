-- Common model: revenue = posted invoices (Finance definition), converted to USD with ref.fx_rates.
SELECT i.invoice_no AS revenue_key, i.order_no, i.posting_date, date_trunc('month', i.posting_date)::DATE AS posting_month,
       i.amount * coalesce(fx.rate_to_usd, 1.0) AS amount_usd, i.currency, o.customer_no, x.company_key,
       coalesce(l.lines_total, 0) AS lines_total, i.amount - coalesce(l.lines_total, 0) AS lines_variance
FROM {{ ref('stg_bc__invoices') }} i
LEFT JOIN {{ ref('stg_bc__sales_orders') }} o ON o.no = i.order_no
LEFT JOIN (SELECT order_no, sum(line_amount) AS lines_total FROM {{ ref('stg_bc__sales_lines') }} GROUP BY 1) l ON l.order_no = i.order_no
LEFT JOIN {{ ref('xref_company') }} x ON x.source = 'bc' AND x.source_id = o.customer_no
LEFT JOIN {{ ref('fx_rates') }} fx ON fx.currency = i.currency
