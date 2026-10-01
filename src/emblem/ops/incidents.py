"""Incident response: severity matrix, owner routing, escalation ladder, runbooks and 'fix at the source' actions."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from emblem.architecture import sor
from emblem.quality.checks import CheckResult
from emblem.quality.reconcile import Recon

CRITICAL_DOMAINS = {"order", "revenue", "inventory"}
SEV = {"critical": 1, "error": 2, "warning": 3}
LADDER = {
    1: [("0 min", "Data engineer on call"), ("15 min", "Domain owner"), ("60 min", "CTO")],
    2: [("0 min", "Data engineer on call"), ("4 h", "Domain owner"), ("1 business day", "CTO")],
    3: [("1 business day", "Data engineer"), ("3 business days", "Domain owner")],
}


def severity(check_severity: str, domain: str) -> int:
    base = SEV.get(check_severity, 3)
    return (
        2 if domain in CRITICAL_DOMAINS and base == 3 else base
    )  # warnings on money-moving domains are never SEV3


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _upsert(
    con: duckdb.DuckDBPyConnection, key: str, title: str, sev: int, domain: str, runbook: str, fix: str
) -> str:
    iid = "INC-" + hashlib.sha1(key.encode()).hexdigest()[:8].upper()  # noqa: S324 - identifier only
    owner = sor.load_sor().get(domain, {}).get("owner", "Data Platform")
    esc = json.dumps([{"after": a, "notify": who} for a, who in LADDER[sev]])
    existing = con.execute("SELECT status FROM meta.incidents WHERE incident_id=?", [iid]).fetchone()
    if existing:
        con.execute(
            "UPDATE meta.incidents SET status='open', severity=?, updated_at=? WHERE incident_id=?",
            [f"SEV{sev}", _now(), iid],
        )
    else:
        con.execute(
            "INSERT INTO meta.incidents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                iid,
                key,
                title,
                f"SEV{sev}",
                domain,
                owner,
                "open",
                f"docs/runbooks/{runbook}.md",
                esc,
                fix,
                _now(),
                _now(),
            ],
        )
    return iid


def open_incidents(
    con: duckdb.DuckDBPyConnection, checks: list[CheckResult], recons: list[Recon]
) -> dict[str, Any]:
    """Idempotent: re-running with the same failures updates, never duplicates. Passing checks auto-resolve their incident."""
    live: set[str] = set()
    for c in checks:
        key = f"dq:{c.check_id}"
        if not c.passed:
            live.add(
                _upsert(
                    con,
                    key,
                    f"{c.check_id}: {c.detail}",
                    severity(c.severity, c.domain),
                    c.domain,
                    c.runbook,
                    c.source_fix or "Owner to investigate source",
                )
            )
        else:
            con.execute(
                "UPDATE meta.incidents SET status='resolved', updated_at=? WHERE dedupe_key=? AND status='open'",
                [_now(), key],
            )
    for r in recons:
        key = f"recon:{r.measure}"
        if r.status == "break":
            live.add(
                _upsert(
                    con,
                    key,
                    f"Reconciliation break on {r.measure}: {r.delta_pct:.2f}% ({r.root_cause})",
                    severity(
                        "critical" if r.domain in CRITICAL_DOMAINS and r.delta_pct > 5 else "error", r.domain
                    ),
                    r.domain,
                    "revenue-mismatch" if r.measure == "revenue" else "pipeline-failure",
                    f"{r.owner}: resolve root cause at source ({r.root_cause})",
                )
            )
        else:
            con.execute(
                "UPDATE meta.incidents SET status='resolved', updated_at=? WHERE dedupe_key=? AND status='open'",
                [_now(), key],
            )
    return {"open": len(live)}


def list_incidents(con: duckdb.DuckDBPyConnection, status: str | None = None) -> list[dict[str, Any]]:
    cols = [
        "incident_id",
        "title",
        "severity",
        "domain",
        "owner",
        "status",
        "runbook",
        "escalation",
        "source_fix_action",
        "opened_at",
    ]
    q = (
        f"SELECT {','.join(cols)} FROM meta.incidents"
        + (" WHERE status=?" if status else "")
        + " ORDER BY severity, incident_id"
    )
    rows = con.execute(q, [status] if status else []).fetchall()
    out = [dict(zip(cols, r, strict=True)) for r in rows]
    for o in out:
        o["escalation"] = json.loads(o["escalation"])
        o["opened_at"] = str(o["opened_at"])
    return out


def runbook_exists(path: str, root: Path) -> bool:
    return (root / path).is_file()
