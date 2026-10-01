"""PySpark twin of the revenue/order conformance: same contract-driven typing and latest-version dedupe, engine-agnostic.

Why it exists: the JD asks for Apache Spark. Row volumes in this demo fit DuckDB, but the logic must port unchanged to
Fabric/Databricks at production volumes. tests/integration/test_spark_parity.py proves both engines agree to the cent.
"""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

from emblem.contracts import Contract, load_contracts

SPARK_TYPES = {
    "VARCHAR": T.StringType(),
    "DOUBLE": T.DoubleType(),
    "INTEGER": T.IntegerType(),
    "DATE": T.StringType(),
    "TIMESTAMP": T.StringType(),
    "BOOLEAN": T.BooleanType(),
}


def session(app: str = "emblem-conform") -> SparkSession:
    return (
        SparkSession.builder.master("local[2]")
        .appName(app)
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )


def stage(spark: SparkSession, bronze_dir: Path, c: Contract) -> DataFrame:
    schema = T.StructType([T.StructField(col.name, SPARK_TYPES[col.type]) for col in c.columns])
    df = spark.read.parquet(str(bronze_dir / f"{c.table}.parquet"))
    parsed = df.select(F.from_json("_payload", schema).alias("p"), "_source_updated_at").select(
        "p.*", "_source_updated_at"
    )
    w = Window.partitionBy(c.pk).orderBy(F.col("_source_updated_at").desc())
    out = parsed.withColumn("_rn", F.row_number().over(w)).filter("_rn = 1").drop("_rn")
    for col in c.columns:
        if col.type == "DATE":
            out = out.withColumn(col.name, F.to_date(F.col(col.name)))
    return out


def monthly_revenue(spark: SparkSession, bronze_dir: Path) -> DataFrame:
    inv = stage(spark, bronze_dir, load_contracts()["bc.invoices"])
    return (
        inv.withColumn("posting_month", F.trunc("posting_date", "month"))
        .groupBy("posting_month")
        .agg(F.count("*").alias("invoices"), F.sum("amount").alias("revenue_usd"))
        .orderBy("posting_month")
    )


def order_channel_mix(spark: SparkSession, bronze_dir: Path) -> DataFrame:
    lines = stage(spark, bronze_dir, load_contracts()["bc.sales_lines"])
    orders = stage(spark, bronze_dir, load_contracts()["bc.sales_orders"])
    j = lines.join(orders, lines.order_no == orders.no)
    return (
        j.withColumn("channel", F.when(F.col("external_doc_no").isNotNull(), "web").otherwise("erp"))
        .groupBy("channel")
        .agg(F.sum("line_amount").alias("amount"), F.count("*").alias("lines"))
    )
