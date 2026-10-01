# ADR 0003: Data contracts drive ingestion; idempotency by content hash
Status: accepted. **Decision:** One YAML contract per source dataset generates typing, drift handling, classification and SLAs. Rows are keyed by SHA-256 of the canonical payload; `ON CONFLICT DO NOTHING` makes replays harmless; each dataset loads in one transaction.
**Consequences:** Retries, overlap windows and re-deliveries are safe. A new version of a record is a new hash; staging keeps the latest per primary key.
