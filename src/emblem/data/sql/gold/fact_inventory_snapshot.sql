-- Common model: inventory. ERP on-hand is authoritative; web level is compared, never trusted.
SELECT inv.inv_id AS inventory_key, inv.item_no AS product_key, inv.location_code AS location_key, inv.qty_on_hand,
       sum(inv.qty_on_hand) OVER (PARTITION BY inv.item_no) AS item_total_on_hand, p.inventory_level AS web_inventory_level,
       p.inventory_level - sum(inv.qty_on_hand) OVER (PARTITION BY inv.item_no) AS web_variance, inv._source_updated_at AS snapshot_ts
FROM {{ ref('stg_bc__inventory') }} inv LEFT JOIN {{ ref('stg_bg__products') }} p ON p.sku = inv.item_no
