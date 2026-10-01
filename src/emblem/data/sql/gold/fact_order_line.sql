-- Common model: order line. Business Central is authoritative for orders; web orders carry external_doc_no.
SELECT l.line_id AS order_line_key, o.no AS order_no, o.order_date, o.status, o.customer_no, x.company_key,
       l.item_no AS product_key, l.quantity, l.unit_price, l.line_amount,
       CASE WHEN o.external_doc_no IS NOT NULL THEN 'web' ELSE 'erp' END AS channel, o.external_doc_no
FROM {{ ref('stg_bc__sales_lines') }} l
JOIN {{ ref('stg_bc__sales_orders') }} o ON o.no = l.order_no
LEFT JOIN {{ ref('xref_company') }} x ON x.source = 'bc' AND x.source_id = o.customer_no
