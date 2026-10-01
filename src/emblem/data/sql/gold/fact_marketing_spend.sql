SELECT id AS spend_key, spend_date, platform, campaign, spend, clicks, impressions FROM {{ ref('stg_mkt__ad_spend') }}
