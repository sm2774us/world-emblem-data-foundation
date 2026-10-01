SELECT d.company_key, d.company_name, d.lifecycle_stage, d.account_owner, d.source_systems,
       coalesce(r.revenue_usd, 0) AS revenue_usd, coalesce(o.orders, 0) AS orders, o.last_order_date,
       coalesce(dl.open_pipeline, 0) AS open_pipeline_usd
FROM {{ ref('dim_company') }} d
LEFT JOIN (SELECT company_key, sum(amount_usd) AS revenue_usd FROM {{ ref('fact_revenue') }} GROUP BY 1) r USING (company_key)
LEFT JOIN (SELECT company_key, count(DISTINCT order_no) AS orders, max(order_date) AS last_order_date
           FROM {{ ref('fact_order_line') }} GROUP BY 1) o USING (company_key)
LEFT JOIN (SELECT x.company_key, sum(h.amount) AS open_pipeline FROM {{ ref('stg_hs__deals') }} h
           JOIN {{ ref('xref_company') }} x ON x.source = 'hs' AND x.source_id = h.company_id
           WHERE h.stage IN ('qualified', 'proposal') GROUP BY 1) dl USING (company_key)
