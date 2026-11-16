# Implementation plan and progress

## Execution checklist

- [x] Inspect all requested source repositories, remotes, commits, dirty state, files, frameworks, commands, API routes, data stores, and deployment shape.
- [x] Initialize the independent parent Git repository and register its seven HTTPS source/support submodules.
- [x] Write the parent-owned project registry and validation.
- [x] Build the SearchMe React/TypeScript/Vite search experience with overview pages, verified section anchors, autocomplete, suggested queries, keyboard controls, and graceful semantic fallback.
- [x] Generate safe project/section search documents from manifests and approved README introductions.
- [x] Implement lazy browser embeddings, a real shared ONNX sentence-embedding model, vector similarity, lexical/fuzzy ranking, and reciprocal-rank fusion.
- [x] Add isolated static frontend aggregation and explicit backend prerequisite settings.
- [x] Generate Nginx and Compose from enabled manifest settings.
- [x] Prepare static Render gateway image configuration and Cloudflare Worker static/API routing.
- [x] Add submodule update and new-project registration workflows.
- [x] Add CI, tests, and the required engineering/deployment documentation.
- [x] Execute the PortfolioWebsite/SearchMe frontend and search-index builds, Python and SearchMe tests, semantic paraphrase checks, manifest validation, Compose schema validation, and Cloudflare dry run; record results in [verification](verification.md).
- [ ] Run Docker-backed Nginx validation and gateway HTTP flows; the local Docker engine was unavailable during this pass, so only Compose schema and temporary static HTTP smoke checks ran. See [verification](verification.md).
- [ ] Enable a backend in the Render image after an eligible service is selected and its startup, memory, persistence, and resource fit are addressed.

## Repository-driven constraints

- `MultiYt2Mp3`'s original working directory contains uncommitted frontend/backend work. The parent uses the remote committed snapshot only, which contains no application code; the original worktree has been left untouched.
- Construct requires PostgreSQL credentials and has no checked-in migration/schema or database bootstrap. Its frontend is buildable in staging, but not published until the API/database setup is defined.
- ScholarlySources runs in an optional local Compose profile. Its measured image is about 2.98 GB and local memory peaked around 629 MiB while loading the model; the current requirements also install unused CUDA packages for CPU inference. It is not included in the Render API target map while a smaller CPU installation and target resource fit remain unresolved.
- NearestNews and MultiYt2Mp3 remain discoverable from what their pinned commits actually document; no technologies or running apps are invented.

## Validation loop

Run `python scripts/validate_projects.py` after manifest changes. `python scripts/build_frontends.py` performs isolated builds, refreshes the index (including actual model embeddings), builds SearchMe at `/search/`, and assembles `dist/`. Then run the commands in [verification](verification.md). Record commands/results there rather than inferring success from generated files.
