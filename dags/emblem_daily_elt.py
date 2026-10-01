"""Daily ELT: extract/load -> staging -> entity resolution -> gold -> quality gate -> reconciliation -> incidents -> publish."""

from __future__ import annotations

from datetime import date, datetime

from airflow.sdk import dag, task

from _common import DEFAULT_ARGS, alert_on_failure, warehouse


@dag(
    dag_id="emblem_daily_elt",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={**DEFAULT_ARGS, "on_failure_callback": alert_on_failure},
    tags=["emblem", "elt", "tier-1"],
    doc_md="Idempotent daily load. Replays are safe (content-hash dedupe). Critical quality failures stop `publish`.",
)
def emblem_daily_elt():
    @task(task_id="extract_load")
    def extract_load(batch: int = 2) -> int:
        from emblem.pipelines import bronze
        from emblem.sources.synthetic import NOW_ANCHOR, generate

        with warehouse() as con:
            stats = bronze.ingest_world(con, generate(batch=batch), f"airflow-b{batch}", NOW_ANCHOR)
            return sum(s["inserted"] for s in stats)

    @task(task_id="transform")
    def transform() -> dict[str, int]:
        from emblem.pipelines import forecast, mdm, sqlmodels, staging

        with warehouse() as con:
            staging.build_staging(con)
            mdm.resolve(con)
            gold = sqlmodels.run_models(con)
            forecast.build_forecast(con)
            return gold

    @task(task_id="quality_gate")
    def quality_gate() -> str:
        from airflow.sdk.exceptions import AirflowFailException

        from emblem.ops import incidents
        from emblem.ops.monitor import new_run_id
        from emblem.quality import checks, reconcile

        with warehouse() as con:
            rid = new_run_id()
            res = checks.run_checks(con, date(2026, 9, 30), rid)
            incidents.open_incidents(con, res, reconcile.reconcile(con, rid))
            crit = [r.check_id for r in res if not r.passed and r.severity == "critical"]
            if crit:
                raise AirflowFailException(f"critical data quality failures block publish: {crit}")
            return rid

    @task(task_id="publish")
    def publish() -> dict[str, int]:
        from pathlib import Path

        from emblem.pipelines.lakehouse import export_gold

        with warehouse() as con:
            return export_gold(con, Path("build/lakehouse"))

    extract_load() >> transform() >> quality_gate() >> publish()


emblem_daily_elt()
