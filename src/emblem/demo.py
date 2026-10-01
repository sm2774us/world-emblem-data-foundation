"""One-call orchestration of the whole showcase: 3 batches -> AI index -> quality -> reconciliation -> incidents -> audit trail."""

from __future__ import annotations

from datetime import date
from typing import Any

import duckdb

from emblem.ai import index, tools
from emblem.ops import incidents
from emblem.ops.monitor import new_run_id
from emblem.pipelines.runner import run_batch
from emblem.quality import checks, reconcile
from emblem.security import audit as audit_log
from emblem.security import rbac

AS_OF = date(2026, 9, 30)


def build_demo(
    con: duckdb.DuckDBPyConnection, scale: float = 1.0, seed: int = 42, batches: tuple[int, ...] = (1, 2, 3)
) -> dict[str, Any]:
    for b in batches:
        run_batch(con, b, seed, scale)
    index.build_documents(con)
    rid = new_run_id()
    res = checks.run_checks(con, AS_OF, rid)
    rec = reconcile.reconcile(con, rid)
    inc = incidents.open_incidents(con, res, rec)
    audit_log.record(con, "pipeline", "data_engineer", "publish", "gold", f"run {rid}")
    for role, tool, arg in (
        ("ai_agent", "product_availability", "WE-1003"),
        ("ai_agent", "company_summary", "Acme"),
        ("ai_agent", "order_status", "SO200001"),
        ("ai_agent", "order_status", "SO200002"),
        ("ai_agent", "order_status", "SO200003"),
    ):
        try:
            tools.call(con, "demo-agent", role, tool, arg)
        except rbac.AccessDenied, KeyError:
            pass
    return {
        "run_id": rid,
        "checks": checks.summarise(res),
        "recon_breaks": sum(r.status == "break" for r in rec),
        "incidents": inc,
    }
