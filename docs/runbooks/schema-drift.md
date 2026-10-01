# Runbook: schema drift
**Triggers:** `dq_no_breaking_schema_change`; rows in `meta.schema_changes`.
* `renamed_alias` (info): known rename handled by contract `aliases`; confirm with the owner and update the contract.
* `additive_column` (warning): new field kept in the payload; add it to the contract by PR (classification + owner) or ignore explicitly.
* `breaking_missing_required` (critical): rows are in `bronze.quarantine`. Ask the source owner to restore the field or version the contract (`contracts.diff_contracts` classifies the change). After the fix, replay the batch: quarantined rows load, nothing duplicates.
