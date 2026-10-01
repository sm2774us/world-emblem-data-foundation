"""Send a correctly SIGNED test webhook to a running API (demonstrates the event-driven path).

Usage: EMBLEM_WEBHOOK_SECRET=<same value the server started with> uv run python tools/send_webhook.py [--url URL] [--id EVENT_ID]
Sending the same --id twice shows idempotency ("duplicate")."""

from __future__ import annotations

import argparse
import json
import os
import time

import httpx

from emblem.ops import events


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--id", default=f"demo-{int(time.time())}")
    ap.add_argument("--order", default="990001")
    a = ap.parse_args()
    secret = os.environ.get("EMBLEM_WEBHOOK_SECRET")
    if not secret:
        print("Set EMBLEM_WEBHOOK_SECRET to the same value the server was started with.")
        return 2
    order = {
        "id": a.order,
        "date_created": "2026-09-30T09:00:00Z",
        "total_inc_tax": 123.45,
        "status": "paid",
        "modified_at": "2026-09-30T09:00:00Z",
    }
    body = json.dumps(order).encode()
    ts = str(time.time())
    r = httpx.post(
        f"{a.url}/v1/webhooks/bigcommerce",
        content=body,
        timeout=10,
        headers={
            "X-Signature": events.sign(secret.encode(), ts, body),
            "X-Timestamp": ts,
            "X-Event-Id": a.id,
            "X-Topic": "order.created",
        },
    )
    print(r.status_code, r.text)
    return 0 if r.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
