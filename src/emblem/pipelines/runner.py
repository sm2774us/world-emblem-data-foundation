"""End-to-end ELT orchestration (the same callables are wrapped by the Airflow DAGs and the Spark parity job)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import duckdb

from emblem.ops.monitor import new_run_id, task_run
from emblem.pipelines import bronze, forecast, mdm, sqlmodels, staging
from emblem.sources.synthetic import NOW_ANCHOR, generate


def run_batch(
    con: duckdb.DuckDBPyConnection,
    batch: int = 1,
    seed: int = 42,
    scale: float = 1.0,
    breaking_drift: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    run_id = run_id or new_run_id()
    batch_id = f"b{batch}-{datetime.now(UTC):%H%M%S%f}"
    out: dict[str, Any] = {"run_id": run_id, "batch": batch}
    with task_run(con, run_id, f"extract_load_b{batch}") as t:
        stats = bronze.ingest_world(con, generate(seed, scale, batch, breaking_drift), batch_id, NOW_ANCHOR)
        t["rows_out"] = sum(s["inserted"] for s in stats)
        out["bronze"] = stats
    with task_run(con, run_id, "silver_staging") as t:
        out["silver"] = staging.build_staging(con)
        t["rows_out"] = sum(out["silver"].values())
    with task_run(con, run_id, "entity_resolution") as t:
        out["mdm"] = mdm.resolve(con)
        t["rows_out"] = out["mdm"]["records"]
    with task_run(con, run_id, "gold_models") as t:
        out["gold"] = sqlmodels.run_models(con)
        t["rows_out"] = sum(out["gold"].values())
    with task_run(con, run_id, "forecast") as t:
        t["rows_out"] = forecast.build_forecast(con)
    return out
