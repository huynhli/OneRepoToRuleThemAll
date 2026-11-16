# Portfolio monorepo

This repository assembles PortfolioWebsite as the root site and SearchMe as its semantic search experience. PortfolioWebsite's nested Vite app keeps its interactive Phaser game at `/` and text portfolio at `/notGame`. SearchMe is served at `/search/`, with project overviews at `/work/{slug}/` and published project apps at `/projects/{slug}/`.

The parent owns project manifests, generated search documents and embeddings, frontend aggregation, routing, and deployment configuration. PortfolioWebsite and SearchMe are submodules alongside the other project repositories. The build reads each pinned commit and applies the launcher adapter only to a temporary PortfolioWebsite copy.

## Quick start

```powershell
git submodule update --init --recursive
python scripts/bootstrap.py
python scripts/build_frontends.py
python scripts/generate_nginx.py
python scripts/generate_compose.py
docker compose up --build
```

Open <http://localhost:8080>. SearchMe loads the semantic model only when a submitted query first needs it. Keyword search remains available if model retrieval or inference fails. Optional project services use Compose profiles; see [deployment](docs/deployment.md).

Clone with all pinned projects using:

```bash
git clone --recurse-submodules <MONOREPO_URL>
```

## Structure

- `projects/portfoliowebsite/`: root portfolio site, with its source left upstream-owned.
- `projects/searchme/`: canonical SearchMe app, retrieval engine, worker, tests, and reusable launcher.
- `config/projects/`: parent-owned searchable metadata and integration settings.
- `generated/search-index/`: local parent-generated search index staged into the SearchMe build.
- `scripts/`: validation, indexing, frontend aggregation, and deterministic infrastructure generation.
- `infrastructure/`: Nginx, Docker, Render, and Cloudflare deployment artifacts.
- `docs/`: architecture, onboarding, deployment, and verification records.

See [architecture](docs/architecture.md), [search design](docs/search-architecture.md), [adding projects](docs/adding-projects.md), and [verification](docs/verification.md).

## Integration boundaries

Every manifest project is discoverable at `/work/{slug}/`. `/projects/{slug}/` is generated only when a committed frontend builds and is approved for static publication. PortfolioWebsite is assembled at `/`; its existing Go backend and external API URLs remain in the upstream repository and are not rewritten by the launcher adapter. ScholarlySources runs locally as an opt-in service; its PyTorch/model runtime is excluded from the constrained Render image. Construct still needs PostgreSQL schema/bootstrap configuration before it can run as a service.

No source is copied back into PortfolioWebsite. The parent build uses `git archive HEAD` in temporary staging directories, and the SearchMe gitlink points to a local source commit until that commit is later pushed with authorization.
