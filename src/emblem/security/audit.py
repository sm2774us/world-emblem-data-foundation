"""Tamper-evident audit log: every row commits to the previous row's hash (hash chain)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import duckdb

GENESIS = "0" * 64


def _h(prev: str, seq: int, ts: str, actor: str, role: str, action: str, resource: str, detail: str) -> str:
    return hashlib.sha256(
        "|".join([prev, str(seq), ts, actor, role, action, resource, detail]).encode()
    ).hexdigest()


def record(
    con: duckdb.DuckDBPyConnection, actor: str, role: str, action: str, resource: str, detail: str = ""
) -> int:
    row = con.execute("SELECT seq, hash FROM meta.audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    seq, prev = (row[0] + 1, row[1]) if row else (1, GENESIS)
    ts = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    con.execute(
        "INSERT INTO meta.audit_log VALUES (?,?,?,?,?,?,?,?,?)",
        [
            seq,
            ts,
            actor,
            role,
            action,
            resource,
            detail,
            prev,
            _h(prev, seq, ts.isoformat(), actor, role, action, resource, detail),
        ],
    )
    return seq


def verify_chain(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    prev, n = GENESIS, 0
    for seq, ts, actor, role, action, resource, detail, p, h in con.execute(
        "SELECT * FROM meta.audit_log ORDER BY seq"
    ).fetchall():
        if p != prev or h != _h(prev, seq, ts.isoformat(), actor, role, action, resource, detail):
            return {"valid": False, "first_bad_seq": seq, "entries": n}
        prev, n = h, n + 1
    return {"valid": True, "first_bad_seq": None, "entries": n}
