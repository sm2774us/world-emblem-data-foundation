"""Agent tool registry: allow-listed, parameterised queries only (no free SQL), RBAC-checked and usage-logged."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import duckdb

from emblem.security import rbac

TOOLS: dict[str, dict[str, Any]] = {
    "product_availability": {
        "dataset": "fact_inventory_snapshot",
        "param": "sku",
        "description": "On-hand units across plants for a SKU",
        "sql": "SELECT product_key AS sku, max(item_total_on_hand) AS on_hand_units, max(web_inventory_level) AS web_level FROM gold.fact_inventory_snapshot WHERE product_key = ? GROUP BY 1",
    },
    "company_summary": {
        "dataset": "mart_company_360",
        "param": "company_name",
        "description": "Revenue, orders and lifecycle for a company (no personal data)",
        "sql": "SELECT company_name, lifecycle_stage, revenue_usd, orders, last_order_date FROM gold.mart_company_360 WHERE company_name ILIKE ? LIMIT 5",
    },
    "order_status": {
        "dataset": "fact_order_line",
        "param": "order_no",
        "description": "Status and value of a sales order",
        "sql": "SELECT order_no, any_value(status) AS status, sum(line_amount) AS amount FROM gold.fact_order_line WHERE order_no = ? GROUP BY 1",
    },
}


def tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": n,
            "description": t["description"],
            "input_schema": {
                "type": "object",
                "properties": {t["param"]: {"type": "string"}},
                "required": [t["param"]],
            },
        }
        for n, t in TOOLS.items()
    ]


def _log(
    con: duckdb.DuckDBPyConnection,
    caller: str,
    tool: str,
    rows: int,
    masked: bool,
    allowed: bool,
    detail: str,
) -> None:
    con.execute(
        "INSERT INTO meta.ai_usage VALUES (?,?,?,?,?,?,?)",
        [datetime.now(UTC).replace(tzinfo=None), caller, tool, rows, masked, allowed, detail],
    )


def call(con: duckdb.DuckDBPyConnection, caller: str, role: str, tool: str, arg: str) -> dict[str, Any]:
    if tool not in TOOLS:
        _log(con, caller, tool, 0, False, False, "unknown tool")
        raise KeyError(f"unknown tool '{tool}'")
    spec = TOOLS[tool]
    cur = con.execute(spec["sql"], [arg if tool != "company_summary" else f"%{arg}%"])
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
    try:
        rows, masked = rbac.apply_policy(role, spec["dataset"], rows)
    except rbac.AccessDenied as exc:
        _log(con, caller, tool, 0, False, False, str(exc))
        raise
    _log(con, caller, tool, len(rows), bool(masked), True, f"{tool}({arg})")
    return {"tool": tool, "rows": rows, "masked_columns": masked}


def usage_summary(
    con: duckdb.DuckDBPyConnection, max_rows_per_call: int = 50, max_denied: int = 3
) -> dict[str, Any]:
    rows = con.execute(
        "SELECT caller, tool, count(*), sum(rows_returned), sum((NOT allowed)::INT) FROM meta.ai_usage GROUP BY 1,2 ORDER BY 1,2"
    ).fetchall()
    out = [
        {"caller": r[0], "tool": r[1], "calls": r[2], "rows": int(r[3] or 0), "denied": int(r[4] or 0)}
        for r in rows
    ]
    flags = [
        f"{o['caller']}/{o['tool']}: {o['denied']} denied calls" for o in out if o["denied"] >= max_denied
    ]
    flags += [
        f"{o['caller']}/{o['tool']}: avg {o['rows'] / o['calls']:.0f} rows/call"
        for o in out
        if o["calls"] and o["rows"] / o["calls"] > max_rows_per_call
    ]
    return {
        "usage": out,
        "flags": flags,
        "standards": [
            "allow-listed tools only",
            "RBAC on every call",
            "no PII columns",
            "every call audited",
            "denied-call alerting",
        ],
    }
