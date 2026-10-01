import pytest

from emblem.demo import AS_OF
from emblem.quality import checks, reconcile

pytestmark = pytest.mark.integration

PLANTED = {
    "dq_line_quantity_positive",
    "dq_orphan_order_customer",
    "dq_company_duplicates_in_erp",
    "dq_invoice_matches_lines",
    "dq_web_orders_reach_erp",
    "dq_fresh_ad_spend",
    "dq_web_inventory_in_sync",
    "dq_hs_contact_email_complete",
    "dq_volume_bg_orders",
}
CLEAN = {
    "dq_stg_pk_unique_orders",
    "dq_fresh_sales_orders",
    "dq_bc_item_price_complete",
    "dq_no_breaking_schema_change",
}


def test_planted_defects_are_all_detected_and_clean_checks_pass(demo_con):
    res = {r.check_id: r for r in checks.run_checks(demo_con, AS_OF, "t")}
    assert {k for k, v in res.items() if not v.passed} >= PLANTED
    assert {k for k, v in res.items() if v.passed} >= CLEAN
    assert {r.dimension for r in res.values()} == {
        "completeness",
        "accuracy",
        "duplication",
        "consistency",
        "freshness",
        "volume",
        "schema",
    }


def test_broken_check_fails_loudly_never_silently(demo_con):
    r = checks._eval(
        demo_con,
        {
            "id": "x",
            "dataset": "d",
            "dimension": "accuracy",
            "severity": "error",
            "domain": "order",
            "op": "max",
            "threshold": 0,
            "sql": "SELECT * FROM nope",
        },
        AS_OF,
    )
    assert not r.passed and "errored" in r.detail


def test_reconciliation_root_causes_and_tolerances(demo_con):
    rec = {r.measure: r for r in reconcile.reconcile(demo_con)}
    assert (
        rec["orders"].status == "break"
        and "never reached ERP" in rec["orders"].root_cause
        and rec["orders"].delta == 13
    )
    assert (
        rec["revenue"].status == "break"
        and "price override" in rec["revenue"].root_cause
        and "without invoice" in rec["revenue"].root_cause
    )
    assert rec["order_value"].status == "match" and rec["customer_coverage"].status == "match"
    assert (
        rec["customer_count"].delta == 3
        and rec["inventory"].status == "break"
        and "SKU(s) out of sync" in rec["inventory"].root_cause
    )


def test_summary_scores_by_dimension(demo_con):
    s = checks.summarise(checks.run_checks(demo_con, AS_OF, "t2"))
    assert 0 < s["score"] < 1 and s["failed"] == len(s["failures"]) and s["by_dimension"]["schema"] == 1.0
