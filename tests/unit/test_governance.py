import json
import time

import pytest

from emblem.ops import events
from emblem.security import audit, crypto, rbac, retention, tokens


def test_rbac_masks_by_role_and_denies():
    rows = [{"contact_key": "k", "email": "a@b.com", "phone": "555"}]
    out, masked = rbac.apply_policy("data_engineer", "dim_contact", rows)
    assert masked == ["email", "phone"] and out[0]["email"].startswith("h_") and rows[0]["email"] == "a@b.com"
    clear, none = rbac.apply_policy("sales_rep", "dim_contact", rows)
    assert none == [] and clear[0]["email"] == "a@b.com"
    with pytest.raises(rbac.AccessDenied):
        rbac.apply_policy("marketing_analyst", "dim_contact", rows)
    red, _ = rbac.apply_policy(
        "finance_analyst", "dim_company", [{"company_key": "c", "tax_id": "99-1", "credit_limit": 5.0}]
    )
    assert red[0]["tax_id"] == "[REDACTED]" and red[0]["credit_limit"] == "***"


def test_every_policy_dataset_exists_in_gold(demo_con):
    gold = {
        r[0]
        for r in demo_con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='gold'"
        ).fetchall()
    }
    for name, role in rbac.policies()["roles"].items():
        assert set(role["datasets"]) <= gold | {"*"}, name


def test_field_encryption_roundtrip_tamper_and_tokens():
    c = crypto.FieldCipher(b"unit-test-secret-" + b"x" * 8)
    ct = c.encrypt("99-1234567")
    assert ct != "99-1234567" and c.decrypt(ct) == "99-1234567"
    with pytest.raises(ValueError, match="cannot decrypt"):
        c.decrypt(ct[:-3] + "AAA")
    with pytest.raises(ValueError, match="cannot decrypt"):
        crypto.FieldCipher(b"another-secret-value-12345").decrypt(ct)
    assert c.token("A@B.com") == c.token("a@b.com") and c.token("a@b.com").startswith("tk_")


def test_master_secret_required_in_prod():
    with pytest.raises(crypto.KeyMissingError):
        crypto.master_secret({"EMBLEM_ENV": "prod"})
    assert crypto.master_secret({"EMBLEM_ENV": "prod", "EMBLEM_MASTER_SECRET": "s"}) == b"s"
    assert crypto.master_secret({}) != crypto.master_secret({})  # ephemeral dev keys are never reused


def test_audit_chain_detects_tampering(fresh_con):
    for i in range(4):
        audit.record(fresh_con, "u", "admin", "read", f"t{i}")
    assert audit.verify_chain(fresh_con) == {"valid": True, "first_bad_seq": None, "entries": 4}
    fresh_con.execute("UPDATE meta.audit_log SET resource='forged' WHERE seq=2")
    assert audit.verify_chain(fresh_con)["first_bad_seq"] == 2


def test_tokens_roundtrip_expiry_and_forgery():
    key = b"k" * 32
    t = tokens.issue(key, "u", "admin", ttl=10, now=1000)
    assert tokens.verify(key, t, now=1005)["role"] == "admin"
    with pytest.raises(tokens.TokenError, match="expired"):
        tokens.verify(key, t, now=1011)
    with pytest.raises(tokens.TokenError, match="signature"):
        tokens.verify(b"z" * 32, t, now=1005)
    with pytest.raises(tokens.TokenError, match="malformed"):
        tokens.verify(key, "garbage")


def test_retention_dry_run_vs_apply(demo_con, fresh_con):
    from datetime import date

    from emblem.pipelines import bronze
    from emblem.sources.synthetic import NOW_ANCHOR, generate

    bronze.ingest_dataset(
        fresh_con, "mes.work_orders", lambda: generate()["mes.work_orders"], "b1", NOW_ANCHOR
    )
    n = fresh_con.execute("SELECT count(*) FROM bronze.mes__work_orders").fetchone()[0]
    dry = retention.enforce(fresh_con, date(2030, 1, 1))
    assert dry["applied"] is False and dry["bronze"]["mes.work_orders"] == n
    assert fresh_con.execute("SELECT count(*) FROM bronze.mes__work_orders").fetchone()[0] == n
    retention.enforce(fresh_con, date(2030, 1, 1), apply=True)
    assert fresh_con.execute("SELECT count(*) FROM bronze.mes__work_orders").fetchone()[0] == 0


def test_webhook_signature_and_replay():
    body = json.dumps({"id": 1}).encode()
    ts = str(time.time())
    sig = events.sign(b"s", ts, body)
    events.verify_signature(b"s", ts, body, sig)
    with pytest.raises(events.SignatureError, match="mismatch"):
        events.verify_signature(b"s", ts, body + b" ", sig)
    with pytest.raises(events.SignatureError, match="stale"):
        events.verify_signature(
            b"s", str(time.time() - 1000), body, events.sign(b"s", str(time.time() - 1000), body)
        )
    with pytest.raises(events.SignatureError, match="timestamp"):
        events.verify_signature(b"s", "abc", body, sig)


def test_inbox_idempotent_and_dead_letter(fresh_con):
    evt = {
        "id": "9001",
        "date_created": "2026-09-01T00:00:00Z",
        "total_inc_tax": 10.0,
        "modified_at": "2026-09-01T00:00:00Z",
    }
    assert events.receive(fresh_con, "bigcommerce", "e1", "order.created", evt) == "accepted"
    assert events.receive(fresh_con, "bigcommerce", "e1", "order.created", evt) == "duplicate"
    events.receive(fresh_con, "bigcommerce", "e2", "unknown.topic", {})
    assert events.drain(fresh_con) == {"processed": 1, "dead_letter": 1}
    assert events.drain(fresh_con) == {"processed": 0, "dead_letter": 0}
