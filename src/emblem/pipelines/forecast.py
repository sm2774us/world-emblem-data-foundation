"""Forecasting: Holt linear-trend smoothing on monthly revenue (explainable baseline, no heavy deps)."""

from __future__ import annotations

from datetime import date

import duckdb


def holt(series: list[float], alpha: float = 0.5, beta: float = 0.3, horizon: int = 3) -> list[float]:
    if len(series) < 3:
        return [series[-1] if series else 0.0] * horizon
    level, trend = series[0], series[1] - series[0]
    for y in series[1:]:
        prev = level
        level = alpha * y + (1 - alpha) * (level + trend)
        trend = beta * (level - prev) + (1 - beta) * trend
    return [max(0.0, level + (h + 1) * trend) for h in range(horizon)]


def _add_month(d: date, n: int) -> date:
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def build_forecast(con: duckdb.DuckDBPyConnection, horizon: int = 3) -> int:
    rows = con.execute(
        "SELECT posting_month, revenue_usd FROM gold.mart_revenue_monthly ORDER BY 1"
    ).fetchall()
    con.execute(
        "CREATE OR REPLACE TABLE gold.forecast_revenue(month DATE, revenue_usd_forecast DOUBLE, method VARCHAR)"
    )
    if not rows:
        return 0
    last = rows[-2][0] if len(rows) > 1 else rows[-1][0]  # last month is partial: exclude from training
    train = [float(r[1]) for r in rows[:-1]] or [float(rows[0][1])]
    for i, v in enumerate(holt(train, horizon=horizon), start=1):
        con.execute(
            "INSERT INTO gold.forecast_revenue VALUES (?,?,?)", [_add_month(last, i), v, "holt_linear"]
        )
    return horizon
