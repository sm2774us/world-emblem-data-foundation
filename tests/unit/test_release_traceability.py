from datetime import date
from pathlib import Path

import release
import sync_dbt

from emblem.reporting import showcase

ROOT = Path(__file__).resolve().parents[2]


def test_conventional_commit_parsing():
    assert release.parse("feat(api): add endpoint")["scope"] == "api"
    assert release.parse("fix!: break")["breaking"] is True
    assert release.parse("chore: x")["type"] == "chore" and release.parse("random words") is None
    assert release.parse("feat: x", "BREAKING CHANGE: y")["breaking"] is True


def test_bump_rules_and_notes():
    c = lambda t, b=False: {"type": t, "scope": "", "desc": "d", "breaking": b}  # noqa: E731
    assert (
        release.bump("1.2.3", [c("feat", True)]) == "2.0.0" and release.bump("1.2.3", [c("feat")]) == "1.3.0"
    )
    assert (
        release.bump("1.2.3", [c("fix")]) == "1.2.4" and release.bump("1.2.3", [c("docs"), c("ci")]) is None
    )
    n = release.notes(
        "1.3.0", [{"type": "feat", "scope": "api", "desc": "thing", "breaking": False}], date(2026, 1, 2)
    )
    assert "## [1.3.0] - 2026-01-02" in n and "### Added" in n and "**api:** thing" in n


def test_traceability_paths_exist():
    items = showcase.traceability()
    assert len(items) >= 45
    missing = [
        (i["requirement"], p) for i in items for p in i["evidence"].split(";") if not (ROOT / p).exists()
    ]
    assert not missing, missing


def test_dbt_models_in_sync_with_gold_sql():
    for p in sync_dbt.SRC.glob("*.sql"):
        assert (sync_dbt.OUT / p.name).read_text() == sync_dbt.convert(p.read_text()), p.name
    assert "source('silver'" in (sync_dbt.OUT / "dim_product.sql").read_text()


def test_sync_lock_updates_only_root_package_version():
    lock = (
        '[[package]]\nname = "annotated-types"\nversion = "0.7.0"\n\n'
        '[[package]]\nname = "world-emblem-data-foundation"\nversion = "1.0.0"\nsource = { editable = "." }\n'
    )
    out = release.sync_lock(lock, "1.1.1")
    assert 'name = "world-emblem-data-foundation"\nversion = "1.1.1"' in out and 'version = "0.7.0"' in out
    import pytest

    with pytest.raises(ValueError, match="not found"):
        release.sync_lock('[[package]]\nname = "x"\nversion = "1"\n', "2.0.0")


def test_committed_lock_matches_pyproject_version():
    ver = release.current_version()
    lock = (ROOT / "uv.lock").read_text()
    assert f'name = "world-emblem-data-foundation"\nversion = "{ver}"' in lock, (
        "uv.lock is stale: run `uv lock`"
    )
