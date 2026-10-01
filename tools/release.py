"""SemVer + changelog from Conventional Commits (squash-merged PR titles). `plan` is read-only; `apply` edits pyproject + CHANGELOG."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CC = re.compile(r"^(?P<type>[a-z]+)(\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<desc>.+)$")
SECTIONS = {
    "feat": "Added",
    "fix": "Fixed",
    "perf": "Performance",
    "refactor": "Changed",
    "docs": "Documentation",
    "ci": "CI",
    "test": "Tests",
    "build": "Build",
}


def parse(subject: str, body: str = "") -> dict[str, str | bool] | None:
    m = CC.match(subject.strip())
    if not m:
        return None
    return {
        "type": m["type"],
        "scope": m["scope"] or "",
        "desc": m["desc"],
        "breaking": bool(m["bang"]) or "BREAKING CHANGE" in body,
    }


def bump(version: str, commits: list[dict[str, str | bool]]) -> str | None:
    major, minor, patch = (int(x) for x in version.split("."))
    if any(c["breaking"] for c in commits):
        return f"{major + 1}.0.0"
    if any(c["type"] == "feat" for c in commits):
        return f"{major}.{minor + 1}.0"
    if any(c["type"] in ("fix", "perf", "refactor") for c in commits):
        return f"{major}.{minor}.{patch + 1}"
    return None


def notes(version: str, commits: list[dict[str, str | bool]], today: date | None = None) -> str:
    out = [f"## [{version}] - {(today or date.today()).isoformat()}", ""]
    for t, title in SECTIONS.items():
        items = [c for c in commits if c["type"] == t]
        if items:
            out += (
                [f"### {title}"]
                + [f"- {'**' + str(c['scope']) + ':** ' if c['scope'] else ''}{c['desc']}" for c in items]
                + [""]
            )
    return "\n".join(out)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True, cwd=ROOT).stdout.strip()  # noqa: S603,S607


def current_version() -> str:
    m = re.search(r'^version = "(\d+\.\d+\.\d+)"', (ROOT / "pyproject.toml").read_text(), re.M)
    assert m, "version not found"
    return m[1]


def commits_since_tag() -> list[dict[str, str | bool]]:
    tags = _git("tag", "--list", "v*", "--sort=-v:refname").splitlines()
    rng = f"{tags[0]}..HEAD" if tags else "HEAD"
    raw = _git("log", rng, "--pretty=format:%s%x1f%b%x1e")
    return [
        c
        for rec in raw.split("\x1e")
        if rec.strip()
        and (c := parse(*rec.strip().split("\x1f", 1) if "\x1f" in rec else (rec.strip(), ""))) is not None
    ]


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "plan"
    cur = current_version()
    tagged = bool(_git("tag", "--list", "v*"))
    commits = commits_since_tag()
    nxt = bump(cur, commits) if tagged else cur  # first release ships the seeded version
    release = nxt is not None
    version = nxt or cur
    if cmd == "plan":
        summary = f"release={str(release).lower()} version={version}"
        print(summary)
        if os.environ.get("GITHUB_OUTPUT"):
            Path(os.environ["GITHUB_OUTPUT"]).open("a").write(summary.replace(" ", "\n") + "\n")
        return 0
    if not release:
        return 0
    body = notes(version, commits)
    (ROOT / "RELEASE_NOTES.md").write_text(body)
    if version != cur:
        py = ROOT / "pyproject.toml"
        py.write_text(
            re.sub(r'^version = ".*"', f'version = "{version}"', py.read_text(), count=1, flags=re.M)
        )
        log = ROOT / "CHANGELOG.md"
        head, _, tail = log.read_text().partition("\n## ")
        log.write_text(head + "\n" + body + "\n## " + tail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
