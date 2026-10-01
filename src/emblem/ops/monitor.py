"""Pipeline observability: run log, health summary and Prometheus text exposition."""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import duckdb


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@contextlib.contextmanager
def task_run(con: duckdb.DuckDBPyConnection, run_id: str, task: str) -> Iterator[dict[str, Any]]:
    ctx: dict[str, Any] = {"rows_out": None}
    started = _now()
    try:
        yield ctx
    except Exception as exc:
        con.execute(
            "INSERT INTO meta.pipeline_runs VALUES (?,?,?,?,?,?,?)",
            [run_id, task, "failed", started, _now(), None, str(exc)[:500]],
        )
        raise
    con.execute(
        "INSERT INTO meta.pipeline_runs VALUES (?,?,?,?,?,?,?)",
        [run_id, task, "success", started, _now(), ctx["rows_out"], None],
    )


def new_run_id() -> str:
    return "run-" + uuid.uuid4().hex[:10]


def health(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    q = lambda s: con.execute(s).fetchone()[0]  # type: ignore[index]  # noqa: E731
    return {
        "runs_total": q("SELECT count(*) FROM meta.pipeline_runs"),
        "runs_failed": q("SELECT count(*) FROM meta.pipeline_runs WHERE status='failed'"),
        "ingest_retries": q("SELECT coalesce(sum(attempts-1),0) FROM meta.ingest_log"),
        "rows_quarantined": q("SELECT coalesce(sum(rows_quarantined),0) FROM meta.ingest_log"),
        "schema_changes": q("SELECT count(*) FROM meta.schema_changes"),
        "breaking_schema_changes": q("SELECT count(*) FROM meta.schema_changes WHERE severity='critical'"),
        "open_incidents": q("SELECT count(*) FROM meta.incidents WHERE status='open'"),
    }


def prometheus(con: duckdb.DuckDBPyConnection) -> str:
    h = health(con)
    lines = []
    for k, v in h.items():
        lines += [f"# TYPE emblem_{k} gauge", f"emblem_{k} {v}"]
    for ds, passed, total in con.execute(
        "SELECT dataset, sum(passed::INT), count(*) FROM meta.dq_results WHERE run_id=(SELECT run_id FROM meta.dq_results ORDER BY checked_at DESC LIMIT 1) GROUP BY 1"
    ).fetchall():
        lines.append(f'emblem_dq_pass_ratio{{dataset="{ds}"}} {passed / total:.4f}')
    return "\n".join(lines) + "\n"
