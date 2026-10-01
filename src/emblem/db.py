"""DuckDB access + schema bootstrap (the demo lakehouse engine; Parquet export gives open-format storage)."""

from __future__ import annotations

from pathlib import Path

import duckdb

SCHEMAS = ("bronze", "silver", "gold", "meta", "ref")

META_DDL = [
    """CREATE TABLE IF NOT EXISTS meta.ingest_log(batch_id VARCHAR, dataset VARCHAR, rows_received INTEGER, rows_inserted INTEGER,
       rows_duplicate INTEGER, rows_quarantined INTEGER, status VARCHAR, attempts INTEGER, started_at TIMESTAMP, finished_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS meta.watermarks(dataset VARCHAR PRIMARY KEY, high_watermark TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS meta.schema_changes(batch_id VARCHAR, dataset VARCHAR, change_type VARCHAR, detail VARCHAR,
       severity VARCHAR, detected_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS meta.pipeline_runs(run_id VARCHAR, task VARCHAR, status VARCHAR, started_at TIMESTAMP,
       finished_at TIMESTAMP, rows_out BIGINT, error VARCHAR)""",
    """CREATE TABLE IF NOT EXISTS meta.dq_results(run_id VARCHAR, check_id VARCHAR, dataset VARCHAR, dimension VARCHAR, severity VARCHAR,
       passed BOOLEAN, observed DOUBLE, threshold DOUBLE, detail VARCHAR, checked_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS meta.recon_results(run_id VARCHAR, measure VARCHAR, system_a VARCHAR, value_a DOUBLE, system_b VARCHAR,
       value_b DOUBLE, delta DOUBLE, delta_pct DOUBLE, tolerance_pct DOUBLE, status VARCHAR, root_cause VARCHAR, checked_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS meta.incidents(incident_id VARCHAR PRIMARY KEY, dedupe_key VARCHAR, title VARCHAR, severity VARCHAR,
       domain VARCHAR, owner VARCHAR, status VARCHAR, runbook VARCHAR, escalation VARCHAR, source_fix_action VARCHAR, opened_at TIMESTAMP,
       updated_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS meta.audit_log(seq BIGINT, ts TIMESTAMP, actor VARCHAR, role VARCHAR, action VARCHAR, resource VARCHAR,
       detail VARCHAR, prev_hash VARCHAR, hash VARCHAR)""",
    """CREATE TABLE IF NOT EXISTS meta.events_inbox(event_id VARCHAR PRIMARY KEY, source VARCHAR, topic VARCHAR, payload VARCHAR,
       received_at TIMESTAMP, status VARCHAR, processed_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS meta.ai_usage(ts TIMESTAMP, caller VARCHAR, tool VARCHAR, rows_returned INTEGER, pii_masked BOOLEAN,
       allowed BOOLEAN, detail VARCHAR)""",
]

REF_DDL = [
    "CREATE OR REPLACE TABLE ref.locations AS SELECT * FROM (VALUES ('HOL-FL','Hollywood Plant','plant','FL'),"
    "('ATL-GA','Atlanta Distribution','warehouse','GA'),('DAL-TX','Dallas Plant','plant','TX')) t(location_code,location_name,location_type,state)",
    "CREATE OR REPLACE TABLE ref.fx_rates AS SELECT * FROM (VALUES ('USD',1.0),('CAD',0.73),('EUR',1.08),('GBP',1.27)) t(currency,rate_to_usd)",
]


def connect(path: str | Path = ":memory:", read_only: bool = False) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(path), read_only=read_only)
    if not read_only:
        bootstrap(con)
    return con


def bootstrap(con: duckdb.DuckDBPyConnection) -> None:
    for s in SCHEMAS:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
    for ddl in META_DDL:
        con.execute(ddl)
    for ddl in REF_DDL:
        con.execute(ddl)
