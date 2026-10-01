"""Open-format lakehouse export: gold tables to Parquet (partition-ready) so any engine (Spark, Fabric, Databricks, Snowflake) can read them."""

from __future__ import annotations

from pathlib import Path

import duckdb


def export_gold(con: duckdb.DuckDBPyConnection, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for (t,) in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='gold' AND table_name <> 'ai_documents' ORDER BY 1"
    ).fetchall():
        target = out_dir / f"{t}.parquet"
        con.execute(f"COPY (SELECT * FROM gold.{t}) TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        counts[t] = con.execute(f"SELECT count(*) FROM read_parquet('{target}')").fetchone()[0]  # type: ignore[index]
    return counts


def export_bronze(con: duckdb.DuckDBPyConnection, out_dir: Path, datasets: list[str]) -> dict[str, int]:
    """Raw bronze payloads as Parquet: the hand-off point to Spark (engine-agnostic lakehouse input)."""
    from emblem.contracts import load_contracts

    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for ds in datasets:
        c = load_contracts()[ds]
        target = out_dir / f"{c.table}.parquet"
        con.execute(
            f"COPY (SELECT _payload::VARCHAR AS _payload, _source_updated_at FROM bronze.{c.table}) TO '{target}' (FORMAT PARQUET)"
        )
        counts[ds] = con.execute(f"SELECT count(*) FROM read_parquet('{target}')").fetchone()[0]  # type: ignore[index]
    return counts
