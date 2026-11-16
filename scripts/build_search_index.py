#!/usr/bin/env python3
"""Assemble safe, deterministic search documents and real model embeddings."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "generated" / "search-index"
SETTINGS_PATH = ROOT / "config" / "search" / "settings.json"
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|secret)\b\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b"),
]


def clean_public_text(value: str) -> str:
    value = re.sub(r"```.*?```", " ", value, flags=re.DOTALL)
    value = re.sub(r"(?m)^\s*[-*]\s*\[[ xX]\]\s*", "", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"!?(\[[^\]]*\])\([^)]*\)", r"\1", value)
    value = re.sub(r"[`*_>#]", "", value)
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[redacted configuration value]", value)
    return " ".join(value.split())[:1800]


def read_approved_intro(project: dict[str, Any]) -> str:
    excerpts: list[str] = []
    repo = ROOT / project["repository"]
    for relative in project["approved_docs"]:
        if Path(relative).name.lower().startswith("readme"):
            path = repo / relative
            if not path.is_file():
                continue
            paragraphs: list[str] = []
            current: list[str] = []
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = line.strip()
                if stripped.startswith("## "):
                    break
                if stripped.startswith("#") or stripped.startswith("```"):
                    continue
                if stripped:
                    current.append(stripped)
                elif current:
                    paragraphs.append(" ".join(current))
                    current = []
            if current:
                paragraphs.append(" ".join(current))
            excerpts.extend(clean_public_text(item) for item in paragraphs[:3])
    return " ".join(item for item in excerpts if item)[:2400]


def build_documents(projects: list[dict[str, Any]], suggestions: list[str]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for project in projects:
        slug = project["slug"]
        project_text = " ".join(
            [project["name"], project["summary"], project["description"], *project["domain"], *project["technologies"], *project["frameworks"], *project["features"], *project["keywords"], *project["aliases"], read_approved_intro(project)]
        )
        docs.append({
            "id": f"{slug}:project",
            "project_id": project["id"],
            "slug": slug,
            "kind": "project",
            "title": project["name"],
            "summary": project["summary"],
            "text": clean_public_text(project_text),
            "technologies": project["technologies"],
            "keywords": list(dict.fromkeys([*project["keywords"], *project["aliases"], *project["technologies"], *project["frameworks"]])),
            "url": f"/work/{slug}/",
        })
        built_path = OUTPUT / "built-frontends.json"
        available: set[str] = set()
        if built_path.is_file():
            try:
                available = set(json.loads(built_path.read_text(encoding="utf-8")).get("available", []))
            except (json.JSONDecodeError, OSError):
                available = set()
        application_url = f"/projects/{slug}/" if slug in available and project["frontend"].get("publish") else None
        docs[-1]["application_url"] = application_url
        for section in project["sections"]:
            docs.append({
                "id": f"{slug}:{section['id']}",
                "project_id": project["id"],
                "slug": slug,
                "kind": "section",
                "title": section["title"],
                "summary": section["summary"],
                "text": clean_public_text(" ".join([section["title"], section["summary"], project["summary"], *section["keywords"], *project["technologies"]])),
                "technologies": project["technologies"],
                "keywords": list(dict.fromkeys([*section["keywords"], *project["keywords"], *project["aliases"]])),
                "url": f"/work/{slug}/#{section['id']}",
                "application_url": application_url,
            })
    return docs


def main() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_projects import load_manifests

    try:
        projects = load_manifests()
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception as error:  # show the single actionable failure at the command boundary
        print(f"cannot build search index: {error}", file=sys.stderr)
        return 1
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "embeddings.json").unlink(missing_ok=True)
    docs = build_documents(projects, settings["suggested_queries"])
    built_path = OUTPUT / "built-frontends.json"
    available: set[str] = set()
    if built_path.is_file():
        try:
            available = set(json.loads(built_path.read_text(encoding="utf-8")).get("available", []))
        except (json.JSONDecodeError, OSError):
            available = set()
    public_projects = [
        {key: project[key] for key in ("id", "name", "slug", "summary", "description", "technologies", "frameworks", "features", "sections")}
        | {"frontend": {"publish": bool(project["frontend"].get("publish") and project["slug"] in available)}}
        for project in projects
    ]
    (OUTPUT / "projects.json").write_text(json.dumps(public_projects, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    content = json.dumps(docs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    index_meta = {
        "schema_version": settings["schema_version"],
        "index_hash": content_hash,
        "document_count": len(docs),
        "project_count": len(projects),
        "model": settings["embedding_model"],
        "model_revision": settings.get("embedding_revision", "main"),
        "embedding_library": settings["embedding_library"],
        "onnxruntime_web_version": settings["onnxruntime_web_version"],
        "dimensions": settings["embedding_dimensions"],
        "pooling": settings["pooling"],
        "normalize": settings["normalize"],
        "dtype": settings["embedding_dtype"],
        "suggested_queries": settings["suggested_queries"],
        "created_at": "content-addressed",
    }
    (OUTPUT / "documents.json").write_text(json.dumps({"meta": index_meta, "documents": docs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "metadata.json").write_text(json.dumps(index_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "embedding-input.json").write_text(json.dumps({"index_hash": content_hash, "model": settings["embedding_model"], "revision": index_meta["model_revision"], "dtype": settings["embedding_dtype"], "dimensions": settings["embedding_dimensions"], "texts": [doc["text"] for doc in docs], "ids": [doc["id"] for doc in docs]}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(docs)} safe project/section documents ({content_hash[:12]}).")
    npm = "npm.cmd" if os.name == "nt" else "npm"
    command = [npm, "--prefix", str(ROOT / "projects" / "searchme"), "run", "build:embeddings"]
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        (OUTPUT / "embedding-input.json").unlink(missing_ok=True)
        print("Embedding generation did not complete. The lexical index is available; semantic retrieval will report unavailable until the model is installed/downloaded and this command succeeds.", file=sys.stderr)
        print(f"Embedding command failure: {error}", file=sys.stderr)
        return 2
    metadata = json.loads((OUTPUT / "metadata.json").read_text(encoding="utf-8"))
    (OUTPUT / "embedding-input.json").unlink(missing_ok=True)
    metadata["vector_file"] = "embeddings.json"
    (OUTPUT / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated normalized {settings['embedding_dimensions']}D vectors for {len(docs)} records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
