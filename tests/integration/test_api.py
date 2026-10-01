import json
import secrets
import time

import pytest
from fastapi.testclient import TestClient

from emblem.api.app import create_app
from emblem.ops import events
from emblem.security import audit

pytestmark = pytest.mark.integration
HOOK = secrets.token_hex(16)
AUTH = secrets.token_hex(16)


@pytest.fixture(scope="module")
def client(demo_con):
    app = create_app(
        con=demo_con, env={"EMBLEM_ENV": "dev", "EMBLEM_AUTH_SECRET": AUTH, "EMBLEM_WEBHOOK_SECRET": HOOK}
    )
    return TestClient(app)


def hdr(client, role, sub="tester"):
    tok = client.post("/v1/auth/dev-token", json={"role": role, "sub": sub}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_health_ready_metrics(client):
    assert (
        client.get("/healthz").json()["status"] == "ok" and client.get("/readyz").json()["status"] == "ready"
    )
    m = client.get("/metrics").text
    assert "emblem_runs_total" in m and "emblem_dq_pass_ratio{dataset=" in m


def test_auth_required_and_bad_tokens_rejected(client):
    assert client.get("/v1/catalog").status_code == 401
    assert client.get("/v1/catalog", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/v1/auth/dev-token", json={"role": "emperor"}).status_code == 422


def test_masking_per_role_and_denial_is_audited(client, demo_con):
    eng = client.get("/v1/datasets/dim_contact?limit=3", headers=hdr(client, "data_engineer")).json()
    assert eng["masked_columns"] == ["email", "first_name", "last_name", "phone"] and eng["rows"][0][
        "email"
    ].startswith("h_")
    rep = client.get("/v1/datasets/dim_contact?limit=3", headers=hdr(client, "sales_rep")).json()
    assert rep["masked_columns"] == [] and "@" in (next(r["email"] for r in rep["rows"] if r["email"]) or "")
    assert client.get("/v1/datasets/dim_contact", headers=hdr(client, "marketing_analyst")).status_code == 403
    assert client.get("/v1/datasets/ai_documents", headers=hdr(client, "admin")).status_code == 404
    assert (
        client.get("/v1/datasets/dim_product; DROP TABLE x", headers=hdr(client, "admin")).status_code == 404
    )
    assert client.get("/v1/datasets/dim_product?limit=9999", headers=hdr(client, "admin")).status_code == 422
    assert audit.verify_chain(demo_con)["valid"]
    assert demo_con.execute("SELECT count(*) FROM meta.audit_log WHERE action='denied'").fetchone()[0] >= 1


def test_catalog_only_lists_entitled_datasets(client):
    names = {d["dataset"] for d in client.get("/v1/catalog", headers=hdr(client, "marketing_analyst")).json()}
    assert names == {"fact_marketing_spend", "mart_marketing_roi", "dim_product", "mart_revenue_monthly"}


def test_ops_endpoints_enforce_roles(client):
    assert client.get("/v1/incidents", headers=hdr(client, "ai_agent")).status_code == 403
    inc = client.get("/v1/incidents?status=open", headers=hdr(client, "data_engineer")).json()
    assert inc and all(i["owner"] for i in inc)
    assert client.get("/v1/quality", headers=hdr(client, "auditor")).json()["total"] >= 20
    assert len(client.get("/v1/reconciliation", headers=hdr(client, "finance_analyst")).json()) == 6
    assert client.get("/v1/audit/verify", headers=hdr(client, "auditor")).json()["valid"] is True
    assert client.get("/v1/audit/verify", headers=hdr(client, "sales_rep")).status_code == 403
    up = client.get("/v1/lineage/gold:mart_revenue_monthly", headers=hdr(client, "auditor")).json()[
        "upstream"
    ]
    assert (
        "source:business_central" in up
        and client.get("/v1/lineage/nope", headers=hdr(client, "auditor")).status_code == 404
    )


def test_ai_search_tools_and_usage(client):
    h = hdr(client, "ai_agent", "agent-7")
    assert (
        client.get("/v1/ai/search?q=patch", headers=h).json()
        and client.get("/v1/ai/search?q=x", headers=h).status_code == 422
    )
    ok = client.post("/v1/ai/tools/product_availability?arg=WE-1003", headers=h)
    assert ok.status_code == 200 and ok.json()["rows"]
    assert client.post("/v1/ai/tools/order_status?arg=SO200001", headers=h).status_code == 403
    assert client.post("/v1/ai/tools/drop_everything?arg=x", headers=h).status_code == 404
    assert client.get("/v1/ai/usage", headers=h).status_code == 403
    assert any(
        u["caller"] == "agent-7"
        for u in client.get("/v1/ai/usage", headers=hdr(client, "admin")).json()["usage"]
    )


def _post(client, body: dict, event_id: str, secret=HOOK, ts=None, topic="order.created"):
    raw = json.dumps(body).encode()
    ts = ts or str(time.time())
    return client.post(
        "/v1/webhooks/bigcommerce",
        content=raw,
        headers={
            "X-Signature": events.sign(secret.encode(), ts, raw),
            "X-Timestamp": ts,
            "X-Event-Id": event_id,
            "X-Topic": topic,
        },
    )


def test_webhook_security_idempotency_and_drain(client, demo_con):
    order = {
        "id": "777001",
        "date_created": "2026-09-30T10:00:00Z",
        "total_inc_tax": 123.45,
        "status": "paid",
        "modified_at": "2026-09-30T10:00:00Z",
    }
    assert _post(client, order, "evt-1", secret="wrong-secret").status_code == 401
    assert _post(client, order, "evt-1", ts=str(time.time() - 4000)).status_code == 401
    assert _post(client, order, "evt-1").json() == {"status": "accepted"}
    assert _post(client, order, "evt-1").json() == {"status": "duplicate"}
    assert client.post("/v1/events/drain", headers=hdr(client, "sales_rep")).status_code == 403
    assert client.post("/v1/events/drain", headers=hdr(client, "data_engineer")).json() == {
        "processed": 1,
        "dead_letter": 0,
    }
    assert (
        demo_con.execute(
            "SELECT count(*) FROM bronze.bg__orders WHERE json_extract_string(_payload,'$.id')='777001'"
        ).fetchone()[0]
        == 1
    )
    assert (
        client.post(
            "/v1/webhooks/bigcommerce",
            content=b"{}",
            headers={"X-Signature": "x", "X-Timestamp": "1", "X-Event-Id": "e", "X-Topic": "t"},
        ).status_code
        == 401
    )


def test_showcase_and_dashboard(client):
    snap = client.get("/v1/showcase").json()
    assert snap["plan"]["verification"] and all(v["ok"] for v in snap["plan"]["verification"])
    assert snap["semantic"]["valid"] and snap["lineage"]["edges"] > 80
    html = client.get("/").text
    assert "World Emblem Data Foundation" in html and "const D=" in html and "</script></body>" in html
    assert "@" not in json.dumps(snap["governance"]["masking_demo"]["after"])  # served view is masked


def test_prod_refuses_to_start_without_secrets_and_hides_dev_token(demo_con):
    with pytest.raises(RuntimeError, match="prod requires"):
        create_app(con=demo_con, env={"EMBLEM_ENV": "prod"})
    prod = TestClient(
        create_app(
            con=demo_con,
            env={"EMBLEM_ENV": "prod", "EMBLEM_AUTH_SECRET": AUTH, "EMBLEM_WEBHOOK_SECRET": HOOK},
        )
    )
    assert (
        prod.post("/v1/auth/dev-token", json={"role": "admin"}).status_code == 404
        and prod.get("/docs").status_code == 404
    )
