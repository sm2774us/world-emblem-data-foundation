"""Alert sinks: structured log always; optional webhook (e.g. Teams/Slack/PagerDuty) when EMBLEM_ALERT_WEBHOOK is set."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

log = logging.getLogger("emblem.alerts")


def notify(event: str, severity: str, detail: dict[str, Any]) -> bool:
    payload = {"event": event, "severity": severity, **detail}
    log.warning("ALERT %s", json.dumps(payload, default=str))
    url = os.environ.get("EMBLEM_ALERT_WEBHOOK")
    if not url:
        return False
    try:
        return httpx.post(url, json=payload, timeout=5).is_success
    except httpx.HTTPError:
        log.exception("alert webhook delivery failed")
        return False
