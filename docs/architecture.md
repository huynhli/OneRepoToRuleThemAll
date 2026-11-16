# Repository architecture and inventory

## Boundaries

The parent repository owns project manifests, the generated search index, route/deployment configuration, scripts, and documentation. PortfolioWebsite and SearchMe are Git submodules under `projects/`. SearchMe owns the React/TypeScript search app, hybrid retrieval engine, query embedding worker, tests, and reusable launcher. The parent stores each remote and pinned object ID. Builds use `git archive HEAD` into temporary directories and do not mutate project worktrees.

PortfolioWebsite's nested Vite app is assembled at `/`. Its upstream route map remains intact: the Phaser game is `/`, and the text portfolio is `/notGame`. The build adapter copies the committed SearchMe launcher into a temporary PortfolioWebsite build and connects its open state to Phaser scene pause/resume. It also assigns controller button 8 to the existing Back action, leaving Start (button 9) for the launcher. PortfolioWebsite's backend and external API URLs are not rewritten.

SearchMe is assembled at `/search/`. It uses the parent-generated index from `/search-index/`; `/work/{slug}/` overview and section routes use the same SearchMe bundle. A `/projects/{slug}/` path is generated only for a frontend that successfully builds and is allowed by its manifest. Backend API routes are namespaced `/api/{slug}/` and generated only for enabled targets.

## New source submodules

`projects/portfoliowebsite` is pinned at public commit `dead031`; the Vite app is nested in `portfolioWebsite/`, and its repository also contains a separate Go/Fiber backend. The current adapter does not edit that submodule or its external API URLs.

`projects/searchme` began at public commit `65bf25f`, which contained only a README and license. The existing monorepo search app was moved into that checkout and committed locally so the parent can build it from a pinned gitlink. That commit must be pushed to the SearchMe remote before other clones or CI can fetch the new gitlink.

The original `SearchMe` sibling checkout is separate and was left untouched. `MultiYt2Mp3` also retains unrelated uncommitted sibling work that is excluded from the parent build.

## Runtime shape

The static gateway serves PortfolioWebsite, SearchMe, generated `/work/` overview routes, and successfully aggregated project apps. An optional local ScholarlySources profile serves its API beneath `/api/scholarlysources/`, with the gateway restoring its upstream `/api` prefix. Construct is not enabled until its database/bootstrap requirements are resolved. No backend is selected for Render because ScholarlySources has a heavyweight PyTorch/model runtime and Construct needs external PostgreSQL setup and schema.

Project-specific verified metadata is in [the project registry](../config/projects/). For README-based indexing, only the opening public README description is eligible; source trees, generated model/data files, dependencies, and secrets are excluded.
