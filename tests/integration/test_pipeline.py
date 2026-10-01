import pytest

from emblem import db as dbmod
from emblem.pipelines import lakehouse, sqlmodels
from emblem.pipelines.runner import run_batch
from emblem.quality import checks
from emblem.sources.synthetic import build_world, generate

pytestmark = pytest.mark.integration


def test_gold_revenue_equals_independent_computation(demo_con):
    world = build_world()
    latest = {}
    for r in world["bc.invoices"]:
        latest[r["invoice_no"]] = r  # modified_at of invoices is write-once here
    expected = round(sum(r["amount"] for r in latest.values()), 2)
    got = demo_con.execute("SELECT round(sum(amount_usd), 2) FROM gold.fact_revenue").fetchone()[0]
    assert abs(got - expected) < 1.0  # invoices of the last window land in batch 3 (cutoff inclusive)


def test_entity_resolution_collapses_systems(demo_con):
    n_src, n_co = demo_con.execute(
        "SELECT count(*), count(DISTINCT company_key) FROM silver.xref_company"
    ).fetchone()
    assert n_src > n_co == 60
    assert demo_con.execute("SELECT count(*) FROM gold.dim_company WHERE duplicate_in_erp").fetchone()[0] == 3
    assert {
        r[0] for r in demo_con.execute("SELECT DISTINCT match_rule FROM silver.xref_company").fetchall()
    } >= {"exact_name", "fuzzy_name"}


def test_rerunning_every_batch_is_idempotent():
    con = dbmod.connect()
    for b in (1, 2, 3):
        run_batch(con, b)
    before = {
        t: con.execute(f"SELECT count(*) FROM gold.{t}").fetchone()[0]
        for t in ("fact_revenue", "fact_order_line", "dim_company")
    }
    for b in (1, 2, 3):
        r = run_batch(con, b)
        assert sum(s["inserted"] for s in r["bronze"]) == 0
    assert before == {t: con.execute(f"SELECT count(*) FROM gold.{t}").fetchone()[0] for t in before}


def test_incremental_overlap_redelivers_but_never_duplicates(demo_con):
    rows = demo_con.execute(
        "SELECT dataset, sum(rows_duplicate) FROM meta.ingest_log WHERE batch_id NOT LIKE 'b1-%' GROUP BY 1"
    ).fetchall()
    assert sum(r[1] for r in rows) > 0
    assert (
        demo_con.execute("SELECT count(*) - count(DISTINCT no) FROM silver.stg_bc__sales_orders").fetchone()[
            0
        ]
        == 0
    )


def test_status_update_creates_new_version_latest_wins(demo_con):
    assert (
        demo_con.execute("SELECT count(*) FROM bronze.bc__sales_orders").fetchone()[0]
        > demo_con.execute("SELECT count(*) FROM silver.stg_bc__sales_orders").fetchone()[0]
    )


def test_drift_volume_and_freshness_signals(demo_con):
    kinds = {r[0] for r in demo_con.execute("SELECT change_type FROM meta.schema_changes").fetchall()}
    assert kinds == {"renamed_alias", "additive_column"}
    vol = {c.check_id: c for c in checks.volume_checks(demo_con)}
    assert not vol["dq_volume_bg_orders"].passed and vol["dq_volume_bc_sales_orders"].passed


def test_breaking_drift_quarantines_without_stopping_pipeline():
    con = dbmod.connect()
    r = run_batch(con, 3, breaking_drift=True)
    assert con.execute("SELECT count(*) FROM bronze.quarantine").fetchone()[0] == 5 and r["gold"]
    assert not checks.schema_checks(con)[0].passed


def test_sql_models_dag_has_no_cycles_and_orders_dependencies():
    models = sqlmodels.load_models()
    order = sqlmodels.execution_order(models)
    assert order.index("fact_revenue") < order.index("mart_revenue_monthly") < len(order)
    bad = {
        **models,
        "a": sqlmodels.Model("a", "gold", "", ("b",)),
        "b": sqlmodels.Model("b", "gold", "", ("a",)),
    }
    with pytest.raises(ValueError, match="cycle"):
        sqlmodels.execution_order(bad)


def test_lakehouse_parquet_export_roundtrip(demo_con, tmp_path):
    counts = lakehouse.export_gold(demo_con, tmp_path)
    assert (
        counts["fact_revenue"] == demo_con.execute("SELECT count(*) FROM gold.fact_revenue").fetchone()[0]
        and "ai_documents" not in counts
    )
    assert (tmp_path / "dim_company.parquet").stat().st_size > 0


def test_forecast_and_marketing_marts(demo_con):
    assert demo_con.execute("SELECT count(*) FROM gold.forecast_revenue").fetchone()[0] == 3
    assert (
        demo_con.execute("SELECT count(*) FROM gold.mart_marketing_roi WHERE roas IS NOT NULL").fetchone()[0]
        >= 1
    )


def test_generated_world_is_deterministic():
    assert generate(seed=1, scale=0.2) == generate(seed=1, scale=0.2) and generate(
        seed=1, scale=0.2
    ) != generate(seed=2, scale=0.2)
