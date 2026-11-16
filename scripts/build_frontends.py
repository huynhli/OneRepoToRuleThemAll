#!/usr/bin/env python3
"""Build committed project UIs in temporary worktrees and assemble one static tree."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
GENERATED_INDEX = ROOT / "generated" / "search-index"
SEARCHME_REPO = ROOT / "projects" / "searchme"
sys.path.insert(0, str(ROOT / "scripts"))
from validate_projects import load_manifests, safe_relative  # noqa: E402


def run(command: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    if os.name == "nt":
        import subprocess as sp
        result = sp.run(sp.list2cmdline(command), cwd=cwd, shell=True, text=True)
    else:
        result = subprocess.run(command, cwd=cwd, text=True)
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def extract_commit(repository: Path, destination: Path) -> None:
    status = subprocess.run(["git", "-C", str(repository), "status", "--porcelain"], capture_output=True, text=True, check=True)
    if status.stdout.strip():
        raise RuntimeError(f"Refusing to build dirty submodule {repository.relative_to(ROOT)}")
    archive = subprocess.run(["git", "-C", str(repository), "archive", "--format=tar", "HEAD"], capture_output=True, check=True).stdout
    import io
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        for member in bundle.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isdir() or member.isfile()):
                raise RuntimeError(f"Unsafe or unsupported source entry in {repository.name}: {member.name}")
        bundle.extractall(destination)


def patch_staged_frontend(source_root: Path, frontend: dict, slug: str) -> None:
    rewrite = frontend.get("staged_api_rewrite")
    if rewrite:
        file = source_root / safe_relative(rewrite["file"], "staged_api_rewrite.file")
        content = file.read_text(encoding="utf-8")
        if rewrite["from"] not in content:
            raise RuntimeError(f"Expected API path {rewrite['from']!r} was not found in staged {file.name}")
        file.write_text(content.replace(rewrite["from"], rewrite["to"]), encoding="utf-8", newline="\n")

    if frontend.get("router") == "react-router-dom":
        found = False
        for source in source_root.rglob("*.tsx"):
            content = source.read_text(encoding="utf-8")
            if "<BrowserRouter>" in content and "basename=" not in content:
                source.write_text(content.replace("<BrowserRouter>", "<BrowserRouter basename={import.meta.env.BASE_URL}>"), encoding="utf-8", newline="\n")
                found = True
        if not found:
            raise RuntimeError(f"{slug}: configured React Router was not found in a patchable BrowserRouter entry")


def patch_staged_portfolio(source_root: Path, searchme_source: Path) -> None:
    """Mount the SearchMe launcher and pause Phaser only in the staged site copy."""
    source = searchme_source / "src"
    component_dir = source_root / "src" / "components"
    launcher_dir = source_root / "src" / "launcher"
    component_dir.mkdir(parents=True, exist_ok=True)
    launcher_dir.mkdir(parents=True, exist_ok=True)
    for file_name in ("SearchMeLauncher.tsx", "searchme-launcher.css"):
        shutil.copy2(source / "components" / file_name, component_dir / file_name)
    shutil.copy2(source / "launcher" / "gamepad.ts", launcher_dir / "gamepad.ts")

    main_file = source_root / "src" / "main.tsx"
    main = main_file.read_text(encoding="utf-8")
    app_import = "import App from './App.tsx'"
    if app_import not in main or "SearchMeLauncher" in main:
        raise RuntimeError("PortfolioWebsite main.tsx did not match the expected launcher insertion point")
    main = main.replace(app_import, app_import + "\nimport SearchMeLauncher from './components/SearchMeLauncher.tsx'")
    if "        <App />" not in main:
        raise RuntimeError("PortfolioWebsite main.tsx did not contain its App mount")
    main = main.replace("        <App />", "        <>\n          <App />\n          <SearchMeLauncher />\n        </>")
    main_file.write_text(main, encoding="utf-8", newline="\n")

    game_file = source_root / "src" / "pages" / "GamePage.tsx"
    game = game_file.read_text(encoding="utf-8")
    old_back = "const gamepadBack = !!pad?.buttons[9]?.pressed"
    if old_back not in game:
        raise RuntimeError("PortfolioWebsite Start/Back mapping did not match the expected button 9 binding")
    game = game.replace(old_back, "const gamepadBack = !!pad?.buttons[8]?.pressed")
    listener_anchor = "        game.events.on(GAME_EVENTS.RESUME_OPEN, openResumePanel)"
    pause_bridge = '''        const syncSearchMePause = () => {
            const shouldPause = document.documentElement.dataset.searchmeOpen === "true"
            for (const scene of game.scene.scenes) {
                if (shouldPause) scene.scene.pause()
                else scene.scene.resume()
            }
        }
        const onSearchMePanelState = () => syncSearchMePause()
        window.addEventListener("searchme:panel-state", onSearchMePanelState)
        syncSearchMePause()
'''
    if game.count(listener_anchor) != 1:
        raise RuntimeError("PortfolioWebsite Phaser setup did not match the expected pause bridge insertion point")
    game = game.replace(listener_anchor, listener_anchor + "\n" + pause_bridge.rstrip("\n"))
    cleanup_anchor = "            game.events.off(GAME_EVENTS.RESUME_OPEN, openResumePanel)"
    if game.count(cleanup_anchor) != 1:
        raise RuntimeError("PortfolioWebsite Phaser cleanup did not match the expected listener removal point")
    game = game.replace(cleanup_anchor, cleanup_anchor + "\n            window.removeEventListener(\"searchme:panel-state\", onSearchMePanelState)")
    game_file.write_text(game, encoding="utf-8", newline="\n")


def main() -> int:
    try:
        projects = load_manifests()
    except Exception as error:
        print(f"frontend build stopped: {error}", file=sys.stderr)
        return 1
    resolved_dist = DIST.resolve()
    if resolved_dist.parent != ROOT.resolve() or resolved_dist.name != "dist":
        print(f"unsafe generated output path: {resolved_dist}", file=sys.stderr)
        return 1
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    built: list[str] = []
    available: list[str] = []
    failures: dict[str, str] = {}

    with tempfile.TemporaryDirectory(prefix="portfolio-project-build-") as temp_name:
        staging = Path(temp_name)
        searchme_source = staging / "searchme-source"
        extract_commit(SEARCHME_REPO, searchme_source)
        for project in projects:
            frontend = project["frontend"]
            if not frontend.get("build"):
                continue
            slug = project["slug"]
            try:
                repo = ROOT / project["repository"]
                build_root = staging / slug
                build_root.mkdir()
                extract_commit(repo, build_root)
                package_dir = build_root / safe_relative(frontend.get("package_dir", "."), "frontend.package_dir")
                patch_staged_frontend(package_dir, frontend, slug)
                if frontend.get("root_site"):
                    patch_staged_portfolio(package_dir, searchme_source)
                run(["npm", "ci"], package_dir)
                base = "/" if frontend.get("root_site") else f"/projects/{slug}/"
                command = ["npm", "run", "build", "--", f"--base={base}"]
                environment = os.environ.copy()
                if frontend.get("api_prefix") and slug == "construct":
                    environment["VITE_API_BASE_URL_DOCKER_COMPOSE"] = frontend["api_prefix"]
                # Keep the project's source and package install isolated in the temporary archive.
                if os.name == "nt":
                    import subprocess as sp
                    result = sp.run(sp.list2cmdline(command), cwd=package_dir, env=environment, shell=True)
                else:
                    result = subprocess.run(command, cwd=package_dir, env=environment)
                if result.returncode:
                    raise subprocess.CalledProcessError(result.returncode, command)
                output = package_dir / "dist"
                if not output.is_dir() or not (output / "index.html").is_file():
                    raise RuntimeError("Build completed without a static dist/index.html")
                built.append(slug)
                if frontend.get("root_site"):
                    for item in output.iterdir():
                        destination = DIST / item.name
                        if item.is_dir():
                            shutil.copytree(item, destination, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, destination)
                elif frontend.get("publish"):
                    destination = DIST / "projects" / slug
                    shutil.copytree(output, destination)
                    available.append(slug)
                else:
                    print(f"Built {slug} successfully; not published: {frontend.get('publish_reason', 'manifest disables publication')}.")
            except Exception as error:
                failures[slug] = str(error)
                print(f"Frontend build failed for {slug}: {error}", file=sys.stderr)

        GENERATED_INDEX.mkdir(parents=True, exist_ok=True)
        build_state = {"available": sorted(available), "built": sorted(built), "failed": dict(sorted(failures.items()))}
        (GENERATED_INDEX / "built-frontends.json").write_text(json.dumps(build_state, indent=2) + "\n", encoding="utf-8")

        index_result = run([sys.executable, str(ROOT / "scripts" / "build_search_index.py")], ROOT, check=False)
        if index_result.returncode == 2:
            print("Warning: semantic vectors are unavailable; building SearchMe with lexical search.", file=sys.stderr)
        elif index_result.returncode:
            print("Search-index build failed; static frontend assembly was not completed.", file=sys.stderr)
            return index_result.returncode

        try:
            searchme_root = staging / "searchme-build"
            extract_commit(SEARCHME_REPO, searchme_root)
            searchme_public = searchme_root / "public" / "search-index"
            shutil.copytree(GENERATED_INDEX, searchme_public, dirs_exist_ok=True)
            run(["npm", "ci"], searchme_root)
            searchme_command = ["npm", "run", "build", "--", "--base=/search/", "--outDir", str(searchme_root / "dist")]
            if os.name == "nt":
                import subprocess as sp
                result = sp.run(sp.list2cmdline(searchme_command), cwd=searchme_root, shell=True)
            else:
                result = subprocess.run(searchme_command, cwd=searchme_root)
            if result.returncode:
                raise subprocess.CalledProcessError(result.returncode, searchme_command)
            search_output = searchme_root / "dist"
            shutil.copytree(search_output, DIST / "search", dirs_exist_ok=True)
            built_index = search_output / "search-index"
            if not built_index.is_dir():
                raise RuntimeError("SearchMe build did not include its staged public search index")
            shutil.copytree(built_index, DIST / "search-index", dirs_exist_ok=True)
            shutil.rmtree(DIST / "search" / "search-index")
            max_asset_size = 25 * 1024 * 1024
            for asset in DIST.rglob("*"):
                if not asset.is_file() or asset.stat().st_size <= max_asset_size:
                    continue
                if asset.name.startswith("ort-wasm-simd-threaded.asyncify") and asset.suffix == ".wasm":
                    asset.unlink()
                    print(f"Externalized {asset.name} to the pinned ONNX Runtime CDN to stay within Cloudflare's 25 MiB per-file limit.")
                    continue
                raise RuntimeError(f"Static deployment asset exceeds 25 MiB: {asset.relative_to(DIST)} ({asset.stat().st_size} bytes)")
        except Exception as error:
            print(f"SearchMe build failed: {error}", file=sys.stderr)
            return 1

    if failures:
        print("Some configured project frontends failed to build:", file=sys.stderr)
        for slug, error in failures.items():
            print(f"  {slug}: {error}", file=sys.stderr)
        if any(project["slug"] in failures and (project["frontend"].get("publish") or project["frontend"].get("root_site")) for project in projects):
            return 1
    print(f"Assembled PortfolioWebsite at /, SearchMe at /search/, and app frontend(s): {', '.join(available) if available else 'none'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
