"""Deterministic hashed bag-of-ngrams embeddings (dependency-free). Swap `embed` for Azure OpenAI / Fabric embeddings in production;
the governed index, approval flags and retrieval contract stay identical."""

from __future__ import annotations

import hashlib
import math
import re

DIM = 256


def embed(text: str, dim: int = DIM) -> list[float]:
    vec = [0.0] * dim
    words = re.findall(r"[a-z0-9]+", text.lower())
    grams = words + [w[i : i + 3] for w in words for i in range(max(1, len(w) - 2))]
    for g in grams:
        h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big")
        vec[h % dim] += 1.0 if (h >> 63) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
