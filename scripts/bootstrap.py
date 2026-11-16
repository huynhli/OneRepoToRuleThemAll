#!/usr/bin/env python3
"""Prepare checked-out submodules and install SearchMe's frontend dependencies."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=ROOT)
    if result.returncode:
        return result.returncode
    npm = "npm.cmd" if os.name == "nt" else "npm"
    result = subprocess.run([npm, "ci"], cwd=ROOT / "projects" / "searchme", shell=os.name == "nt")
    if result.returncode:
        return result.returncode
    print("Bootstrap complete. Build the parent index and assembled site with python scripts/build_frontends.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
