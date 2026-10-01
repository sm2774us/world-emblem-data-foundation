"""Event-driven path: drain the webhook inbox every 5 minutes; failures park in dead_letter for replay."""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.sdk import dag, task

from _common import DEFAULT_ARGS, alert_on_failure, warehouse


@dag(
    dag_id="emblem_events_drain",
    schedule=timedelta(minutes=5),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={**DEFAULT_ARGS, "retries": 1, "on_failure_callback": alert_on_failure},
    tags=["emblem", "events", "tier-1"],
)
def emblem_events_drain():
    @task
    def drain() -> dict[str, int]:
        from emblem.ops import events

        with warehouse() as con:
            return events.drain(con)

    drain()


emblem_events_drain()
