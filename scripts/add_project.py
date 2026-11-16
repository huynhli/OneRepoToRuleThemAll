#!/usr/bin/env python3
"""Add an HTTPS repository as a submodule and generate a factual manifest proposal."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)


def readme_intro(path: Path) -> str:
    if not path.is_file():
        return ""
    lines = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        item = line.strip()
        if item.startswith("## "):
            break
        if not item or item.startswith("#") or item.startswith("```"):
            continue
        lines.append(item)
        if len(" ".join(lines)) >= 700:
            break
    return " ".join(lines)[:900]


def detect_technologies(repository: Path) -> tuple[list[str], list[str]]:
    detected: list[str] = []
    files = {path.name.lower() for path in repository.rglob("*") if path.is_file() and ".git" not in path.parts}
    if "package.json" in files:
        detected.extend(["JavaScript", "Node.js"])
        package_files = list(repository.rglob("package.json"))[:10]
        for path in package_files:
            try:
                package = json.loads(path.read_text(encoding="utf-8"))
                dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
                for key, label in (("react", "React"), ("vite", "Vite"), ("next", "Next.js"), ("vue", "Vue"), ("@angular/core", "Angular"), ("react-router-dom", "React Router")):
                    if key in dependencies:
                        detected.append(label)
            except (OSError, json.JSONDecodeError):
                pass
    if "go.mod" in files:
        detected.append("Go")
    if "requirements.txt" in files or "pyproject.toml" in files:
        detected.append("Python")
    for needle, label in (("fastapi", "FastAPI"), ("django", "Django"), ("flask", "Flask")):
        if needle in " ".join(p.read_text(encoding="utf-8", errors="ignore")[:20000].lower() for p in list(repository.rglob("requirements*.txt"))[:4]):
            detected.append(label)
    return list(dict.fromkeys(detected)), list(dict.fromkeys([item for item in detected if item in {"React", "Vite", "Next.js", "Vue", "Angular", "React Router", "FastAPI", "Django", "Flask"}]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="public HTTPS Git remote")
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()
    if not SLUG_RE.fullmatch(args.slug):
        parser.error("slug must use lowercase letters, numbers, and hyphens")
    if not args.repo.startswith("https://") or "@" in args.repo.split("//", 1)[-1].split("/", 1)[0]:
        parser.error("repo must be a credential-free HTTPS URL")
    path = f"projects/{args.slug}"
    manifest_path = ROOT / "config" / "projects" / f"{args.slug}.json"
    if (ROOT / path).exists() or manifest_path.exists():
        parser.error(f"project path or manifest already exists for {args.slug}")
    remote = run(["git", "ls-remote", "--heads", args.repo])
    if remote.returncode or not remote.stdout.strip():
        parser.error("remote is unavailable or has no public branch heads")
    added = run(["git", "submodule", "add", args.repo, path])
    if added.returncode:
        print(added.stderr, file=sys.stderr)
        return added.returncode

    repository = ROOT / path
    intro = readme_intro(repository / "README.md")
    name = " ".join(part.capitalize() for part in args.slug.split("-"))
    summary = intro.split(". ", 1)[0].strip() if intro else "No project summary is documented in the pinned README yet."
    technologies, frameworks = detect_technologies(repository)
    files = [str(item.relative_to(repository)).replace("\\", "/") for item in repository.rglob("*") if item.is_file() and ".git" not in item.parts]
    description = intro or "The repository does not document its purpose yet; review this registration before publishing it in the public portfolio."
    keywords = list(dict.fromkeys([*args.slug.split("-"), *technologies]))
    manifest = {
        "id": args.slug,
        "name": name,
        "slug": args.slug,
        "repository": path,
        "summary": summary,
        "description": description,
        "domain": [],
        "technologies": technologies,
        "frameworks": frameworks,
        "features": [intro] if intro else ["Add verified project features before publishing."],
        "keywords": keywords,
        "aliases": [],
        "suggested_queries": [],
        "approved_docs": ["README.md"] if intro else [],
        "sections": [
            {"id": "overview", "title": "Project overview", "summary": summary, "keywords": keywords},
            {"id": "repository-structure", "title": "Repository structure", "summary": f"The pinned repository contains {len(files)} tracked or discovered files; review its documented architecture before enabling builds.", "keywords": ["repository", "architecture", "source code", *technologies]},
        ],
        "frontend": {"build": False, "publish": False, "reason": "Review framework, base path, and router compatibility before enabling static aggregation."},
        "backend": {"kind": "none", "compose": {"enabled": False}, "render": {"enabled": False}},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation = run([sys.executable, "scripts/validate_projects.py"])
    if validation.returncode:
        print(validation.stdout + validation.stderr, file=sys.stderr)
        return validation.returncode
    for script in ("scripts/generate_nginx.py", "scripts/generate_compose.py"):
        result = run([sys.executable, script])
        if result.returncode:
            print(result.stdout + result.stderr, file=sys.stderr)
            return result.returncode
    index = run([sys.executable, "scripts/build_search_index.py"])
    if index.returncode not in (0, 2):
        print(index.stdout + index.stderr, file=sys.stderr)
        return index.returncode
    git_add = run(["git", "add", "--", path, f"config/projects/{args.slug}.json", ".gitmodules"])
    if git_add.returncode:
        print(git_add.stderr, file=sys.stderr)
        return git_add.returncode
    print(f"Registered projects/{args.slug}; generated a parent-owned metadata proposal and staged its pointer/configuration.")
    if not intro:
        print("Review and replace the README-based placeholder metadata before publishing.")
    print("No source checkout was modified beyond the newly created submodule; no commit or push was created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
