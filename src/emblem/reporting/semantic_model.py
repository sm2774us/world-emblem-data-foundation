"""Power BI semantic model (TMSL/BIM JSON) generated from the gold layer: tables, relationships, DAX measures, RLS roles."""

from __future__ import annotations

import json
from typing import Any

import duckdb

TYPE_MAP = {
    "VARCHAR": "string",
    "DOUBLE": "double",
    "BIGINT": "int64",
    "INTEGER": "int64",
    "DATE": "dateTime",
    "TIMESTAMP": "dateTime",
    "BOOLEAN": "boolean",
}
TABLES = [
    "dim_company",
    "dim_product",
    "dim_location",
    "fact_revenue",
    "fact_order_line",
    "fact_inventory_snapshot",
    "fact_production",
    "mart_revenue_monthly",
    "mart_marketing_roi",
    "forecast_revenue",
]
RELATIONSHIPS = [
    ("fact_revenue", "company_key", "dim_company", "company_key"),
    ("fact_order_line", "company_key", "dim_company", "company_key"),
    ("fact_order_line", "product_key", "dim_product", "product_key"),
    ("fact_inventory_snapshot", "product_key", "dim_product", "product_key"),
    ("fact_inventory_snapshot", "location_key", "dim_location", "location_key"),
    ("fact_production", "product_key", "dim_product", "product_key"),
    ("fact_production", "location_key", "dim_location", "location_key"),
]
MEASURES = {
    "fact_revenue": {
        "Total Revenue": "SUM(fact_revenue[amount_usd])",
        "Invoice Count": "COUNTROWS(fact_revenue)",
        "Revenue YoY %": "VAR cur = [Total Revenue] VAR py = CALCULATE([Total Revenue], DATEADD(fact_revenue[posting_date], -1, YEAR)) RETURN DIVIDE(cur - py, py)",
        "Invoice Variance": "SUM(fact_revenue[lines_variance])",
    },
    "fact_order_line": {
        "Orders": "DISTINCTCOUNT(fact_order_line[order_no])",
        "Avg Order Value": "DIVIDE(SUM(fact_order_line[line_amount]), [Orders])",
    },
    "fact_inventory_snapshot": {
        "On Hand Units": "SUM(fact_inventory_snapshot[qty_on_hand])",
        "Web Stock Variance": "SUM(fact_inventory_snapshot[web_variance])",
    },
    "fact_production": {
        "Scrap Rate": "DIVIDE(SUM(fact_production[qty_scrap]), SUM(fact_production[qty_planned]))",
        "Yield %": "1 - [Scrap Rate]",
    },
    "mart_marketing_roi": {
        "ROAS": "DIVIDE(SUM(mart_marketing_roi[web_revenue]), SUM(mart_marketing_roi[spend]))"
    },
}
RLS = {
    "Sales rep": "dim_company[account_owner] = USERPRINCIPALNAME()",
    "Plant manager": 'dim_location[location_key] IN {"HOL-FL"}',
}


def build(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    tables = []
    for t in TABLES:
        cols = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='gold' AND table_name=? ORDER BY ordinal_position",
            [t],
        ).fetchall()
        hidden = {"tax_id", "credit_limit"}
        tables.append(
            {
                "name": t,
                "columns": [
                    {
                        "name": c,
                        "dataType": TYPE_MAP.get(d.split("(")[0], "string"),
                        "isHidden": c in hidden or (c.endswith("_key") and t.startswith("fact")),
                    }
                    for c, d in cols
                ],
                "measures": [{"name": n, "expression": e} for n, e in MEASURES.get(t, {}).items()],
                "partitions": [
                    {
                        "name": t,
                        "mode": "directLake",
                        "source": {"type": "entity", "entityName": t, "schemaName": "gold"},
                    }
                ],
            }
        )
    rel = [
        {
            "name": f"{a}_{b}",
            "fromTable": a,
            "fromColumn": b,
            "toTable": c,
            "toColumn": d,
            "crossFilteringBehavior": "oneDirection",
        }
        for a, b, c, d in RELATIONSHIPS
    ]
    return {
        "name": "WorldEmblemGovernedModel",
        "compatibilityLevel": 1600,
        "model": {
            "culture": "en-US",
            "tables": tables,
            "relationships": rel,
            "roles": [
                {
                    "name": n,
                    "modelPermission": "read",
                    "tablePermissions": [{"name": expr.split("[")[0], "filterExpression": expr}],
                }
                for n, expr in RLS.items()
            ],
        },
    }


def validate(model: dict[str, Any]) -> list[str]:
    errs = []
    cols = {(t["name"], c["name"]) for t in model["model"]["tables"] for c in t["columns"]}
    for r in model["model"]["relationships"]:
        for tbl, col in ((r["fromTable"], r["fromColumn"]), (r["toTable"], r["toColumn"])):
            if (tbl, col) not in cols:
                errs.append(f"relationship {r['name']}: {tbl}[{col}] missing")
    for t in model["model"]["tables"]:
        for m in t["measures"]:
            for ref_t, ref_c in __import__("re").findall(r"(\w+)\[(\w+)\]", m["expression"]):
                if (ref_t, ref_c) not in cols:
                    errs.append(f"measure {m['name']}: {ref_t}[{ref_c}] missing")
    return errs


def to_json(model: dict[str, Any]) -> str:
    return json.dumps(model, indent=2)
