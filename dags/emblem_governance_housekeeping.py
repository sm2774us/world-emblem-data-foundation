"""Weekly governance housekeeping: retention enforcement (dry-run unless the `apply` param is true) and audit-chain verification."""

from __future__ import annotations

from datetime import date, datetime

from airflow.sdk import Param, dag, task

from _common import DEFAULT_ARGS, alert_on_failure, warehouse


@dag(
    dag_id="emblem_governance_housekeeping",
    schedule="0 5 * * 0",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={**DEFAULT_ARGS, "on_failure_callback": alert_on_failure},
    params={"apply": Param(False, type="boolean")},
    tags=["emblem", "governance"],
)
def emblem_governance_housekeeping():
    @task
    def retention(params: dict | None = None) -> dict:
        from emblem.security import retention as r

        with warehouse() as con:
            return r.enforce(con, date(2026, 9, 30), apply=bool((params or {}).get("apply", False)))

    @task
    def verify_audit_chain() -> dict:
        from airflow.sdk.exceptions import AirflowFailException

        from emblem.security import audit

        with warehouse() as con:
            res = audit.verify_chain(con)
            if not res["valid"]:
                raise AirflowFailException(f"audit chain tampered at seq {res['first_bad_seq']}")
            return res

    retention() >> verify_audit_chain()


emblem_governance_housekeeping()
