"""Platform recommendation: weighted scoring + weight-perturbation sensitivity (is the winner robust?)."""

from __future__ import annotations

import random
from typing import Any

import yaml

from emblem.contracts import DATA_DIR


def load() -> dict[str, Any]:
    return yaml.safe_load((DATA_DIR / "architecture" / "platform_options.yaml").read_text())  # type: ignore[no-any-return]


def score(cfg: dict[str, Any], weights: dict[str, float] | None = None) -> list[dict[str, Any]]:
    w = weights or {k: v["weight"] for k, v in cfg["criteria"].items()}
    total = sum(w.values())
    ranked = [
        {
            "option": k,
            "label": o["label"],
            "score": round(sum(w[c] * o["scores"][c] for c in w) / total, 3),
            "breakdown": o["scores"],
        }
        for k, o in cfg["options"].items()
    ]
    return sorted(ranked, key=lambda r: (-r["score"], r["option"]))


def sensitivity(cfg: dict[str, Any], trials: int = 500, jitter: float = 0.5, seed: int = 7) -> dict[str, Any]:
    rnd = random.Random(seed)  # noqa: S311 - seeded sensitivity analysis, not security
    base = {k: v["weight"] for k, v in cfg["criteria"].items()}
    wins: dict[str, int] = {}
    for _ in range(trials):
        w = {k: max(0.01, v * (1 + rnd.uniform(-jitter, jitter))) for k, v in base.items()}
        win = score(cfg, w)[0]["option"]
        wins[win] = wins.get(win, 0) + 1
    return {
        "trials": trials,
        "jitter_pct": int(jitter * 100),
        "win_share": {k: round(v / trials, 3) for k, v in sorted(wins.items(), key=lambda kv: -kv[1])},
    }


def recommendation() -> dict[str, Any]:
    cfg = load()
    ranked = score(cfg)
    return {
        "ranking": ranked,
        "winner": ranked[0],
        "sensitivity": sensitivity(cfg),
        "criteria": cfg["criteria"],
        "tools": cfg["integration_tools"],
    }
