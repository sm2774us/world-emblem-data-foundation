from __future__ import annotations

import sys
from pathlib import Path

import pytest

from emblem import db as dbmod
from emblem.demo import build_demo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "dags"))


@pytest.fixture(scope="session")
def demo_con():
    """Whole platform after three batches (read-mostly; tests that mutate must use `fresh_con`)."""
    con = dbmod.connect()
    build_demo(con)
    yield con
    con.close()


@pytest.fixture
def fresh_con():
    con = dbmod.connect()
    yield con
    con.close()
