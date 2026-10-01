import pytest

pytest.importorskip("pyspark")
from emblem.pipelines.lakehouse import export_bronze

pytestmark = [pytest.mark.integration, pytest.mark.spark]


def test_spark_and_duckdb_agree_to_the_cent(demo_con, tmp_path):
    from emblem.spark_jobs import conform_orders as job

    export_bronze(demo_con, tmp_path, ["bc.invoices", "bc.sales_lines", "bc.sales_orders"])
    spark = job.session()
    try:
        sp = {
            str(r["posting_month"]): (r["invoices"], round(r["revenue_usd"], 2))
            for r in job.monthly_revenue(spark, tmp_path).collect()
        }
        du = {
            str(r[0]): (r[1], round(r[2], 2))
            for r in demo_con.execute(
                "SELECT posting_month, invoices, revenue_usd FROM gold.mart_revenue_monthly"
            ).fetchall()
        }
        assert sp == du
        mix = {r["channel"]: round(r["amount"], 2) for r in job.order_channel_mix(spark, tmp_path).collect()}
        duck = dict(
            demo_con.execute(
                "SELECT channel, round(sum(line_amount), 2) FROM gold.fact_order_line GROUP BY 1"
            ).fetchall()
        )
        assert mix == duck
    finally:
        spark.stop()
