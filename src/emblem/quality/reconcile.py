"""Cross-system reconciliation of orders, revenue, inventory and customer counts with root-cause attribution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb


@dataclass
class Recon:
    measure: str
    system_a: str
    value_a: float
    system_b: str
    value_b: float
    tolerance_pct: float
    root_cause: str
    domain: str
    owner: str

    @property
    def delta(self) -> float:
        return self.value_a - self.value_b

    @property
    def delta_pct(self) -> float:
        base = max(abs(self.value_a), abs(self.value_b), 1e-9)
        return abs(self.delta) / base * 100

    @property
    def status(self) -> str:
        return "match" if self.delta_pct <= self.tolerance_pct else "break"

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.update(delta=round(self.delta, 2), delta_pct=round(self.delta_pct, 3), status=self.status)
        return d


def _one(con: duckdb.DuckDBPyConnection, sql: str) -> float:
    v = con.execute(sql).fetchone()[0]  # type: ignore[index]
    return float(v or 0)


def reconcile(con: duckdb.DuckDBPyConnection, run_id: str | None = None) -> list[Recon]:
    r: list[Recon] = []
    miss = _one(con, "SELECT count(*) FROM gold.exc_web_orders_missing_in_erp")
    sample = ", ".join(
        x[0]
        for x in con.execute(
            "SELECT web_order_id FROM gold.exc_web_orders_missing_in_erp ORDER BY 1 LIMIT 5"
        ).fetchall()
    )
    r.append(
        Recon(
            "orders",
            "BigCommerce orders",
            _one(con, "SELECT count(*) FROM silver.stg_bg__orders"),
            "ERP orders w/ web ref",
            _one(con, "SELECT count(*) FROM silver.stg_bc__sales_orders WHERE external_doc_no IS NOT NULL"),
            0.0,
            f"{int(miss)} web order(s) never reached ERP (connector failure); e.g. {sample}"
            if miss
            else "none",
            "order",
            "Ecommerce",
        )
    )
    r.append(
        Recon(
            "order_value",
            "BigCommerce (ex-tax)",
            _one(
                con,
                "SELECT sum(g.total_inc_tax) / 1.07 FROM silver.stg_bg__orders g WHERE EXISTS "
                "(SELECT 1 FROM silver.stg_bc__sales_orders o WHERE o.external_doc_no = 'BG-' || g.id)",
            ),
            "ERP lines (web orders)",
            _one(con, "SELECT sum(line_amount) FROM gold.fact_order_line WHERE channel = 'web'"),
            0.5,
            "tax-adjusted comparison on orders present in both systems",
            "order",
            "Ecommerce",
        )
    )
    over = _one(con, "SELECT count(*) FROM gold.fact_revenue WHERE abs(lines_variance) > 0.01")
    noinv = _one(
        con,
        "SELECT count(*) FROM silver.stg_bc__sales_orders o WHERE status='Shipped' AND NOT EXISTS (SELECT 1 FROM silver.stg_bc__invoices i WHERE i.order_no=o.no)",
    )
    r.append(
        Recon(
            "revenue",
            "Invoices (GL definition)",
            _one(con, "SELECT sum(amount_usd) FROM gold.fact_revenue"),
            "Shipped order lines",
            _one(con, "SELECT sum(line_amount) FROM gold.fact_order_line WHERE status='Shipped'"),
            0.5,
            f"{int(over)} invoice(s) with price override; {int(noinv)} shipped order(s) without invoice",
            "revenue",
            "Finance",
        )
    )
    bad = _one(
        con,
        "SELECT count(DISTINCT product_key) FILTER (WHERE abs(web_variance) > 0) FROM gold.fact_inventory_snapshot",
    )
    skus = _one(con, "SELECT count(DISTINCT product_key) FROM gold.fact_inventory_snapshot")
    r.append(
        Recon(
            "inventory",
            "SKUs tracked in ERP",
            skus,
            "SKUs where web stock = ERP on-hand",
            skus - bad,
            0.0,
            f"{int(bad)} SKU(s) out of sync (stale nightly CSV sync)" if bad else "none",
            "inventory",
            "Ecommerce",
        )
    )
    dup = _one(con, "SELECT count(*) FROM silver.stg_bc__customers") - _one(
        con, "SELECT count(*) FROM gold.dim_company WHERE bc_customer_nos IS NOT NULL"
    )
    r.append(
        Recon(
            "customer_count",
            "ERP customer cards",
            _one(con, "SELECT count(*) FROM silver.stg_bc__customers"),
            "Golden companies (ERP-backed)",
            _one(con, "SELECT count(*) FROM gold.dim_company WHERE bc_customer_nos IS NOT NULL"),
            0.0,
            f"{int(dup)} duplicate ERP customer card(s) merged by entity resolution",
            "company",
            "Finance",
        )
    )
    r.append(
        Recon(
            "customer_coverage",
            "HubSpot companies",
            _one(con, "SELECT count(*) FROM silver.stg_hs__companies"),
            "Golden companies in CRM",
            _one(con, "SELECT count(*) FROM gold.dim_company WHERE source_systems LIKE '%hs%'"),
            0.0,
            "CRM company count equals resolved CRM-linked companies",
            "company",
            "Sales",
        )
    )
    if run_id:
        now = datetime.now(UTC).replace(tzinfo=None)
        for x in r:
            con.execute(
                "INSERT INTO meta.recon_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    run_id,
                    x.measure,
                    x.system_a,
                    x.value_a,
                    x.system_b,
                    x.value_b,
                    x.delta,
                    x.delta_pct,
                    x.tolerance_pct,
                    x.status,
                    x.root_cause,
                    now,
                ],
            )
    return r
