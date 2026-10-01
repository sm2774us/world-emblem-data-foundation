-- Exception queue: web orders with no Business Central counterpart (fix at the integration, not the report).
SELECT g.id AS web_order_id, g.date_created, g.total_inc_tax, g.status, g.customer_id
FROM {{ ref('stg_bg__orders') }} g
WHERE NOT EXISTS (SELECT 1 FROM {{ ref('stg_bc__sales_orders') }} o WHERE o.external_doc_no = 'BG-' || g.id)
