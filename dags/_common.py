"""Shared helpers for the DAGs. Task bodies are thin: all logic lives in the tested `emblem` package."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

from emblem import db as dbmod

DEFAULT_ARGS: dict[str, Any] = {
    "owner": "data-platform",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(hours=1),
}


@contextmanager
def warehouse() -> Iterator[Any]:
    con = dbmod.connect(os.environ.get("EMBLEM_DB", "build/emblem.duckdb"))
    try:
        yield con
    finally:
        con.close()


def alert_on_failure(context: dict[str, Any]) -> None:
    from emblem.ops.alerts import notify

    ti = context.get("task_instance")
    notify(
        "airflow_task_failed",
        "error",
        {
            "dag": getattr(ti, "dag_id", "?"),
            "task": getattr(ti, "task_id", "?"),
            "run": str(context.get("run_id")),
        },
    )
