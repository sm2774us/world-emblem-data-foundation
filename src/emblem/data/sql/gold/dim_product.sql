-- Common model: product. Business Central item no. is the enterprise product_key; web attributes are enrichment.
SELECT i.no AS product_key, i.no AS sku, i.description, i.family, i.unit_price AS list_price, i.unit_cost AS std_cost, i.uom,
       coalesce(p.is_visible, false) AS web_published, p.price AS web_price, (p.sku IS NOT NULL) AS on_web
FROM {{ ref('stg_bc__items') }} i LEFT JOIN {{ ref('stg_bg__products') }} p ON p.sku = i.no
