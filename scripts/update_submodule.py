#!/usr/bin/env python3
"""Advance one clean submodule to a selected remote branch and stage its gitlink."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="registered project slug")
    parser.add_argument("--ref", default="main", help="remote branch name, default: main")
    args = parser.parse_args()
    if not REF_RE.fullmatch(args.slug) or args.slug.startswith("-"):
        parser.error("slug must contain lowercase letters, digits, and hyphens")
    if not REF_RE.fullmatch(args.ref) or args.ref.startswith("-") or ".." in args.ref or args.ref.endswith(("/", ".")):
        parser.error("ref must be a safe branch name such as main")
    module = ROOT / "projects" / args.slug
    if not module.is_dir():
        parser.error(f"unknown submodule: {args.slug}")
    try:
        if git("status", "--porcelain", cwd=module):
            raise RuntimeError(f"Refusing to update dirty submodule projects/{args.slug}")
        configured = git("remote", "get-url", "origin", cwd=module)
        if not configured.startswith("https://"):
            raise RuntimeError("origin must be a portable HTTPS remote")
        git("fetch", "--no-tags", "origin", f"refs/heads/{args.ref}", cwd=module)
        selected = git("rev-parse", "FETCH_HEAD^{commit}", cwd=module)
        git("checkout", "--detach", selected, cwd=module)
        git("add", "--", f"projects/{args.slug}")
        print(f"Updated projects/{args.slug} to {selected} and staged its parent gitlink.")
        print("No commit or push was created.")
    except Exception as error:
        print(f"submodule update failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
