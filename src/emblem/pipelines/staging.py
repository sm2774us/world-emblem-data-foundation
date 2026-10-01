"""Silver staging models GENERATED from data contracts: typed, latest-version, deduped per primary key."""

from __future__ import annotations

import duckdb

from emblem.contracts import Contract, load_contracts


def staging_name(c: Contract) -> str:
    return f"stg_{c.table}"


def staging_sql(c: Contract) -> str:
    cols = ",\n  ".join(
        f"TRY_CAST(json_extract_string(_payload, '$.\"{col.name}\"') AS {col.type}) AS {col.name}"
        for col in c.columns
    )
    return (
        f"SELECT\n  {cols},\n  _batch_id, _source_updated_at, _ingested_at\nFROM bronze.{c.table}\n"
        f"QUALIFY row_number() OVER (PARTITION BY json_extract_string(_payload, '$.\"{c.pk}\"')\n"
        f"  ORDER BY _source_updated_at DESC, _ingested_at DESC) = 1"
    )


def build_staging(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in load_contracts().values():
        exists = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='bronze' AND table_name=?",
            [c.table],
        ).fetchone()[0]  # type: ignore[index]
        if not exists:
            continue
        con.execute(f"CREATE OR REPLACE TABLE silver.{staging_name(c)} AS {staging_sql(c)}")
        out[staging_name(c)] = con.execute(f"SELECT count(*) FROM silver.{staging_name(c)}").fetchone()[0]  # type: ignore[index]
    return out
