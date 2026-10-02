"""Black-box: real CLI + real uvicorn process + real HTTP. Nothing is mocked."""

import json
import os
import secrets
import socket
import subprocess
import sys
import time

import httpx
import pytest

from emblem.ops import events

pytestmark = pytest.mark.e2e


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    d = tmp_path_factory.mktemp("e2e")
    db, report = str(d / "e2e.duckdb"), str(d / "report.html")
    env = {
        **os.environ,
        "EMBLEM_AUTH_SECRET": secrets.token_hex(16),
        "EMBLEM_WEBHOOK_SECRET": secrets.token_hex(16),
        "EMBLEM_ENV": "dev",
    }
    demo = subprocess.run(
        [sys.executable, "-m", "emblem", "--db", db, "demo", "--out", report, "--scale", "0.6"],
        capture_output=True,
        text=True,
        env=env,
        timeout=240,
        check=False,
    )
    assert demo.returncode == 0, demo.stderr
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "emblem", "--db", db, "serve", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            if httpx.get(base + "/healthz", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.25)
    else:
        proc.kill()
        pytest.fail("server did not start")
    yield {
        "base": base,
        "hook": env["EMBLEM_WEBHOOK_SECRET"].encode(),
        "demo_out": demo.stdout,
        "report": report,
    }
    proc.terminate()
    proc.wait(timeout=10)


def _token(base, role):
    return {
        "Authorization": "Bearer "
        + httpx.post(base + "/v1/auth/dev-token", json={"role": role}).json()["token"]
    }


def test_demo_cli_output_and_static_report(server):
    assert "quality" in server["demo_out"] and "milestones verified" in server["demo_out"]
    html = open(server["report"], encoding="utf-8").read()
    assert "World Emblem Data Foundation" in html and "JD traceability" in html


def test_full_user_journey_over_http(server):
    b = server["base"]
    assert "World Emblem" in httpx.get(b + "/", timeout=60).text
    assert httpx.get(b + "/v1/catalog").status_code == 401
    eng = httpx.get(b + "/v1/datasets/dim_contact?limit=2", headers=_token(b, "data_engineer")).json()
    assert (eng["masked_columns"] and eng["rows"][0]["email"] is None) or eng["rows"][0]["email"].startswith(
        "h_"
    )
    assert (
        httpx.get(b + "/v1/datasets/dim_contact", headers=_token(b, "marketing_analyst")).status_code == 403
    )
    # event-driven path: signed webhook -> inbox -> drain -> bronze, duplicates absorbed
    body = json.dumps(
        {
            "id": "880001",
            "date_created": "2026-09-30T08:00:00Z",
            "total_inc_tax": 50.0,
            "modified_at": "2026-09-30T08:00:00Z",
        }
    ).encode()
    ts = str(time.time())
    h = {
        "X-Signature": events.sign(server["hook"], ts, body),
        "X-Timestamp": ts,
        "X-Event-Id": "e2e-1",
        "X-Topic": "order.created",
    }
    assert httpx.post(b + "/v1/webhooks/bigcommerce", content=body, headers=h).json()["status"] == "accepted"
    assert httpx.post(b + "/v1/webhooks/bigcommerce", content=body, headers=h).json()["status"] == "duplicate"
    assert httpx.post(b + "/v1/events/drain", headers=_token(b, "admin")).json()["processed"] == 1
    # governance evidence
    assert httpx.get(b + "/v1/audit/verify", headers=_token(b, "auditor")).json()["valid"] is True
    assert httpx.get(b + "/v1/ai/search?q=embroidered patch", headers=_token(b, "ai_agent")).json()
    assert "emblem_open_incidents" in httpx.get(b + "/metrics").text


def test_cli_commands_run(server, tmp_path):
    db = server["base"]  # keep linter quiet; commands below run on a fresh db
    out = subprocess.run(
        [sys.executable, "-m", "emblem", "--db", str(tmp_path / "x.duckdb"), "audit", "--baseline"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "reliability_pct" in json.loads(out) and db
    bad = subprocess.run(
        [sys.executable, "-m", "emblem", "--db", str(tmp_path / "empty.duckdb"), "quality"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert bad.returncode != 0 and "uv run emblem demo" in (bad.stderr + bad.stdout)


def test_docs_command_is_self_contained_on_a_fresh_checkout(tmp_path):
    """Regression: CI runs `emblem docs` on a clean clone with no prior demo; it must build its own data."""
    (tmp_path / "docs").mkdir()
    r = subprocess.run(
        [sys.executable, "-m", "emblem", "--db", str(tmp_path / "w.duckdb"), "docs"],
        cwd=tmp_path, capture_output=True, text=True, timeout=240, check=False,
    )  # fmt: skip
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "docs" / "90-DAY-PLAN.md").stat().st_size > 1000 and (
        tmp_path / "docs" / "powerbi" / "model.bim"
    ).exists()
