"""Vendor-built integration review: weighted scorecard, blocking criteria and accountability actions."""

from __future__ import annotations

from typing import Any

import yaml

from emblem.contracts import DATA_DIR


def load() -> dict[str, Any]:
    return yaml.safe_load((DATA_DIR / "governance" / "vendor_reviews.yaml").read_text())  # type: ignore[no-any-return]


def evaluate(cfg: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = cfg or load()
    out = []
    for rv in cfg["reviews"]:
        dims, actions = {}, []
        for dim, spec in cfg["rubric"].items():
            got = sum(rv["scores"][i] for i in spec["items"])
            dims[dim] = round(100 * got / (2 * len(spec["items"])), 1)
            actions += [
                f"{rv['vendor']}: deliver '{i.replace('_', ' ')}'"
                for i in spec["items"]
                if rv["scores"][i] == 0
            ]
        total = round(sum(dims[d] * cfg["rubric"][d]["weight"] for d in dims) / 100, 1)
        blockers = [b for b in cfg["blocking"] if rv["scores"][b] == 0]
        verdict = (
            "REJECT until blockers fixed"
            if blockers
            else ("ACCEPT" if total >= 75 else "ACCEPT WITH CONDITIONS")
        )
        out.append(
            {
                "vendor": rv["vendor"],
                "integration": rv["integration"],
                "dimensions": dims,
                "total": total,
                "blockers": blockers,
                "verdict": verdict,
                "actions": actions,
            }
        )
    return out
