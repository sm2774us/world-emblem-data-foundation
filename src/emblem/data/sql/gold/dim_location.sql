-- Common model: location (plants and warehouses). Authoritative: reference data owned by Operations.
SELECT location_code AS location_key, location_name, location_type, state FROM {{ ref('locations') }}
