#!/usr/bin/env python3
"""Validate parent-owned project manifests and their submodule boundaries."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "projects"
EXPECTED = {
    "construct",
    "multiyt2mp3",
    "nearestnews",
    "portfoliowebsite",
    "reactgowebsitetemplate",
    "scholarlysources",
}
SUPPORT_SUBMODULES = {"searchme"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET_RE = re.compile(r"(?i)(?:api[_-]?key|secret|password|token)\s*[:=]\s*[^\s,;]+")


def fail(message: str) -> None:
    raise ValueError(message)


def safe_relative(value: str, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        fail(f"{label} must be a repository-relative path: {value}")
    return path


def load_manifests() -> list[dict[str, Any]]:
    files = sorted(CONFIG.glob("*.json"))
    actual = {path.stem for path in files}
    if not EXPECTED.issubset(actual):
        fail(f"Required project manifests are missing: {sorted(EXPECTED - actual)}")
    projects: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for field in ("id", "name", "slug", "repository", "summary", "description", "domain", "technologies", "frameworks", "features", "keywords", "aliases", "suggested_queries", "approved_docs", "sections", "frontend", "backend"):
            if field not in data:
                fail(f"{path.name}: missing required field {field}")
        slug = data["slug"]
        if slug != path.stem or not SLUG_RE.fullmatch(slug):
            fail(f"{path.name}: slug must match its lowercase filename")
        if data["id"] in seen_ids:
            fail(f"{path.name}: duplicate project id {data['id']}")
        seen_ids.add(data["id"])
        repo_path = safe_relative(data["repository"], f"{path.name} repository")
        if not (ROOT / repo_path / ".git").exists() and not (ROOT / repo_path).exists():
            fail(f"{path.name}: submodule path is missing: {repo_path}")
        for doc in data["approved_docs"]:
            doc_path = safe_relative(doc, f"{path.name} approved_docs")
            if not (ROOT / repo_path / doc_path).is_file():
                fail(f"{path.name}: approved public documentation file is missing: {doc}")
        section_ids: set[str] = set()
        for section in data["sections"]:
            if not {"id", "title", "summary", "keywords"}.issubset(section):
                fail(f"{path.name}: each section needs id/title/summary/keywords")
            if not SLUG_RE.fullmatch(section["id"]):
                fail(f"{path.name}: invalid section anchor {section['id']!r}")
            if section["id"] in section_ids:
                fail(f"{path.name}: duplicate section anchor {section['id']}")
            section_ids.add(section["id"])
        frontend = data["frontend"]
        if frontend.get("publish") and not frontend.get("build"):
            fail(f"{path.name}: a published frontend must be buildable")
        if frontend.get("build"):
            package_dir = safe_relative(frontend.get("package_dir", "."), f"{path.name} frontend.package_dir")
            if not (ROOT / repo_path / package_dir / "package.json").is_file():
                fail(f"{path.name}: frontend build is enabled but package.json is missing")
        if frontend.get("root_site") and (not frontend.get("build") or frontend.get("publish")):
            fail(f"{path.name}: a root_site frontend must be built as the site root, not published under /projects")
        rendered = json.dumps(data, ensure_ascii=False)
        if SECRET_RE.search(rendered):
            fail(f"{path.name}: secret-like value found in manifest")
        projects.append(data)
    verify_gitmodules()
    return projects


def verify_gitmodules() -> None:
    gitmodules = ROOT / ".gitmodules"
    if not gitmodules.is_file():
        fail(".gitmodules is missing")
    for slug in sorted(EXPECTED | SUPPORT_SUBMODULES):
        path = f"projects/{slug}"
        remote_path = subprocess.run(
            ["git", "config", "-f", str(gitmodules), "--get-regexp", rf"^submodule\..*\.path$"],
            capture_output=True,
            text=True,
            check=False,
        )
        configured = any(line.endswith(f" {path}") for line in remote_path.stdout.splitlines())
        if not configured:
            fail(f"{path} is not registered in .gitmodules")
        module = ROOT / path
        if not module.is_dir() or not (module / ".git").exists():
            fail(f"{path} is not initialized; run git submodule update --init --recursive")
        section = next((line.split(" ", 1)[0][:-5] for line in remote_path.stdout.splitlines() if line.endswith(f" {path}")), None)
        if not section:
            fail(f"{path} does not have a .gitmodules section")
        url = subprocess.run(
            ["git", "config", "-f", str(gitmodules), "--get", f"{section}.url"],
            capture_output=True,
            text=True,
            check=False,
        )
        if url.returncode != 0 or not url.stdout.strip().startswith("https://"):
            fail(f"{path} must have a portable HTTPS URL in .gitmodules")
        status = subprocess.run(["git", "-C", str(module), "status", "--porcelain"], capture_output=True, text=True, check=False)
        if status.returncode != 0 or status.stdout.strip():
            fail(f"{path} worktree is not clean; refusing to build from modified submodule files")


def main() -> int:
    try:
        projects = load_manifests()
    except (ValueError, json.JSONDecodeError, OSError) as error:
        print(f"project validation failed: {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(projects)} project manifests and initialized clean submodules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
