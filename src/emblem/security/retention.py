"""Retention enforcement: purge expired raw payloads and events; anonymise old PII. Dry-run unless apply=True."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import duckdb

from emblem.contracts import load_contracts
from emblem.security.rbac import policies


def enforce(con: duckdb.DuckDBPyConnection, as_of: date, apply: bool = False) -> dict[str, Any]:
    pol = policies()["retention"]
    report: dict[str, Any] = {
        "as_of": as_of.isoformat(),
        "applied": apply,
        "bronze": {},
        "events_inbox": 0,
        "ai_usage": 0,
    }
    for c in load_contracts().values():
        exists = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='bronze' AND table_name=?",
            [c.table],
        ).fetchone()[0]  # type: ignore[index]
        if not exists:
            continue
        cutoff = as_of - timedelta(days=min(c.retention_days, pol["bronze_payload_days"]))
        n = con.execute(
            f"SELECT count(*) FROM bronze.{c.table} WHERE _source_updated_at < ?", [cutoff]
        ).fetchone()[0]  # type: ignore[index]
        report["bronze"][c.id] = n
        if apply and n:
            con.execute(f"DELETE FROM bronze.{c.table} WHERE _source_updated_at < ?", [cutoff])
    for tbl, col, key in (
        ("events_inbox", "received_at", "events_inbox_days"),
        ("ai_usage", "ts", "ai_usage_days"),
    ):
        cutoff = as_of - timedelta(days=pol[key])
        n = con.execute(f"SELECT count(*) FROM meta.{tbl} WHERE {col} < ?", [cutoff]).fetchone()[0]  # type: ignore[index]
        report[tbl] = n
        if apply and n:
            con.execute(f"DELETE FROM meta.{tbl} WHERE {col} < ?", [cutoff])
    return report
