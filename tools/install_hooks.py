"""Point git at the repo's hooks (idempotent). Skipped silently outside a git checkout."""

import subprocess
from pathlib import Path

if (Path(__file__).resolve().parents[1] / ".git").exists():
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], check=True)  # noqa: S607
    print("git hooks installed (.githooks)")
