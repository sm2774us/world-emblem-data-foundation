import pytest

from emblem.pipelines import bronze
from emblem.pipelines.retry import TransientError, retry
from emblem.sources.synthetic import NOW_ANCHOR, generate


def _items():
    return generate(scale=0.2)["bc.items"]


def test_replay_is_noop(fresh_con):
    rows = _items()
    first = bronze.ingest_dataset(fresh_con, "bc.items", lambda: rows, "b1", NOW_ANCHOR)
    again = bronze.ingest_dataset(fresh_con, "bc.items", lambda: rows, "b1-replay", NOW_ANCHOR)
    assert first["inserted"] == len(rows) and again["inserted"] == 0 and again["duplicate"] == len(rows)


def test_changed_row_is_new_version_not_duplicate(fresh_con):
    rows = _items()
    bronze.ingest_dataset(fresh_con, "bc.items", lambda: rows, "b1", NOW_ANCHOR)
    changed = [{**rows[0], "unit_price": 99.0, "modified_at": "2026-09-01T00:00:00Z"}]
    assert bronze.ingest_dataset(fresh_con, "bc.items", lambda: changed, "b2", NOW_ANCHOR)["inserted"] == 1


def test_quarantine_and_critical_schema_change(fresh_con):
    rows = [
        {"inv_id": "x", "location_code": "HOL-FL", "qty_on_hand": 1, "modified_at": "2026-01-01T00:00:00Z"}
    ]  # item_no missing
    s = bronze.ingest_dataset(fresh_con, "bc.inventory", lambda: rows, "b1", NOW_ANCHOR)
    assert s["quarantined"] == 1 and s["inserted"] == 0
    assert fresh_con.execute("SELECT count(*) FROM bronze.quarantine").fetchone()[0] == 1
    assert (
        fresh_con.execute("SELECT count(*) FROM meta.schema_changes WHERE severity='critical'").fetchone()[0]
        == 1
    )


def test_alias_and_additive_drift_recorded(fresh_con):
    r = {
        "id": "1",
        "date_created": "2026-01-01T00:00:00Z",
        "total": 5.0,
        "modified_at": "2026-01-01T00:00:00Z",
        "new_field": "x",
    }
    bronze.ingest_dataset(fresh_con, "bg.orders", lambda: [r], "b2", NOW_ANCHOR)
    kinds = {x[0] for x in fresh_con.execute("SELECT change_type FROM meta.schema_changes").fetchall()}
    assert kinds == {"renamed_alias", "additive_column"}
    assert (
        fresh_con.execute(
            "SELECT json_extract_string(_payload,'$.total_inc_tax') FROM bronze.bg__orders"
        ).fetchone()[0]
        == "5.0"
    )


def test_watermark_advances_monotonically(fresh_con):
    rows = _items()
    bronze.ingest_dataset(fresh_con, "bc.items", lambda: rows, "b1", NOW_ANCHOR)
    bronze.ingest_dataset(
        fresh_con,
        "bc.items",
        lambda: [{**rows[0], "modified_at": "2020-01-01T00:00:00Z", "unit_price": 1.0}],
        "b2",
        NOW_ANCHOR,
    )
    assert str(fresh_con.execute("SELECT high_watermark FROM meta.watermarks").fetchone()[0]).startswith(
        "2025-04-01"
    )


def test_failure_rolls_back_and_logs(fresh_con, monkeypatch):
    rows = _items()
    real, calls = bronze.row_hash, []

    def boom(payload):
        calls.append(1)
        if len(calls) == 3:
            raise RuntimeError("disk full")
        return real(payload)

    monkeypatch.setattr(bronze, "row_hash", boom)
    with pytest.raises(RuntimeError, match="disk full"):
        bronze.ingest_dataset(fresh_con, "bc.items", lambda: rows, "b1", NOW_ANCHOR)
    assert fresh_con.execute("SELECT count(*) FROM bronze.bc__items").fetchone()[0] == 0  # all-or-nothing
    assert fresh_con.execute("SELECT status FROM meta.ingest_log").fetchone()[0] == "failed"
    monkeypatch.setattr(bronze, "row_hash", real)
    assert bronze.ingest_dataset(fresh_con, "bc.items", lambda: rows, "b1-retry", NOW_ANCHOR)[
        "inserted"
    ] == len(rows)  # clean replay


def test_retry_recovers_then_gives_up():
    calls = []
    delays = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TransientError("503")
        return "ok"

    assert retry(flaky, sleep=delays.append) == ("ok", 3) and delays == [0.5, 1.0]
    with pytest.raises(TransientError, match="gave up"):
        retry(lambda: (_ for _ in ()).throw(TransientError("down")), attempts=2, sleep=lambda _s: None)


def test_ingest_retries_transient_extract(fresh_con):
    state = {"n": 0}

    def extract():
        state["n"] += 1
        if state["n"] < 2:
            raise TransientError("429")
        return _items()

    s = bronze.ingest_dataset(fresh_con, "bc.items", extract, "b1", NOW_ANCHOR)
    assert s["attempts"] == 2 and s["inserted"] > 0
