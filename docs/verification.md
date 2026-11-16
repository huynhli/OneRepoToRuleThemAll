# Verification record

## Environment

- Date: 2026-11-15.
- Host: Windows PowerShell, Python 3.14.3, Node 24.14.0/npm 11.9.0.
- `docker compose config -q` is available and passes. Docker Desktop's Linux engine was unavailable (`dockerDesktopLinuxEngine` pipe missing), and host Nginx is not installed; Nginx container build/config validation could not run.

## Results observed

| Check | Result |
|---|---|
| `python scripts/validate_projects.py` | Pass: six searchable project manifests, HTTPS submodules, and clean submodule worktrees. SearchMe is a support submodule and is not included as a search result. |
| `python scripts/build_frontends.py` | Pass: PortfolioWebsite built to `dist/` root with the temporary SearchMe launcher adapter; SearchMe built at `dist/search/`; ScholarlySources published under `dist/projects/scholarlysources/`; Construct built but remained unpublished by its manifest. |
| `python -m unittest discover -s tests -v` | Pass: 6 parent tests, including index identity, 384D normalized vectors, deep-link URLs, app-link gating, secret redaction, and static asset bounds. |
| `npm test` in `projects/searchme/` | Pass: 20 tests in 6 files, including semantic/lexical retrieval, project and section deep links, SearchMe GitHub link, launcher click/Ctrl+K behavior, Start-button edge behavior, Tab default handling, and Cloudflare Worker routes. |
| `npm run typecheck` in `projects/searchme/` | Pass. |
| `npm run verify:semantic` in `projects/searchme/` | Pass: all five paraphrased project queries ranked the expected project first using generated vectors and cosine similarity. |
| Search index | Pass: 28 project/section records and normalized 384D vectors; index hash `70b5dce4f7d7`. SearchMe fetches the staged data from `/search-index/`. |
| `python scripts/generate_nginx.py` / `python scripts/generate_compose.py` | Pass: one local optional API route for ScholarlySources; zero Render API routes. Generated Nginx includes `/search/`, `/work/`, root SPA fallback, and published project app routing. |
| `docker compose config -q` | Pass. |
| `npx --yes wrangler@4.162.0 deploy --dry-run --config infrastructure/cloudflare/wrangler.jsonc` | Pass: Wrangler read 102 static files from `dist/` and reported no per-file size violation. No deployment occurred. |
| `docker compose build gateway` | Not run: Docker Desktop's Linux engine was unavailable. Therefore `nginx -t` via Compose could not run; host Nginx is not installed. |
| Local HTTP smoke checks over `dist/` | Pass using a temporary local static server with the configured SPA fallback behavior: `/`, `/notGame`, `/search/`, `/work/construct/`, `/work/portfoliowebsite/`, `/projects/scholarlysources/`, search documents, embeddings, and built assets returned 200; a missing SearchMe `.js` returned 404. This did not exercise Nginx itself. |
| Submodule integrity | Pass: `projects/portfoliowebsite` is clean and unchanged. SearchMe source is clean at local commit `91f816f`; that commit is one ahead of the public remote and was not pushed. |
| Upstream dependency advisories | `npm ci` reported 20 advisories in the pinned PortfolioWebsite frontend dependencies (3 moderate, 17 high). Upstream manifests and lockfile were left unchanged. SearchMe's install reported zero vulnerabilities. |

No remote push or deployment was performed. The parent SearchMe gitlink refers to the local commit above, so other clones and CI cannot fetch it until it is pushed with later authorization.
