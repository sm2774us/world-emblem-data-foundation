import pytest

pytest.importorskip("airflow")
from pathlib import Path

pytestmark = [pytest.mark.integration, pytest.mark.airflow]
DAGS = Path(__file__).resolve().parents[2] / "dags"


@pytest.fixture(scope="module")
def bag():
    from airflow.models import DagBag

    return DagBag(dag_folder=str(DAGS), include_examples=False)


def test_dags_import_cleanly(bag):
    assert bag.import_errors == {}
    assert set(bag.dag_ids) == {"emblem_daily_elt", "emblem_events_drain", "emblem_governance_housekeeping"}


def test_dag_standards(bag):
    for d in bag.dags.values():
        assert d.catchup is False and "emblem" in d.tags
        assert (
            d.default_args["retries"] >= 1
            and d.default_args["owner"] == "data-platform"
            and d.default_args.get("on_failure_callback")
        )


def test_elt_dag_order_and_gate(bag):
    d = bag.dags["emblem_daily_elt"]
    assert [t.task_id for t in d.topological_sort()] == [
        "extract_load",
        "transform",
        "quality_gate",
        "publish",
    ]
    assert d.max_active_runs == 1
