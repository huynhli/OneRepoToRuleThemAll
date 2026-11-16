# Local and production deployment

## Local portfolio site and gateway

Requirements: Python 3.10+, Node.js 20.19+, npm, Git, and Docker Desktop/Compose. From the monorepo root:

```powershell
git submodule update --init --recursive
python scripts/bootstrap.py
python scripts/build_frontends.py
python scripts/generate_nginx.py
python scripts/generate_compose.py
docker compose up --build
```

Open <http://localhost:8080>. `build_frontends.py` stages PortfolioWebsite with the launcher adapter, regenerates the parent search docs/vectors, builds SearchMe at `/search/`, and assembles `dist/`. `PORTFOLIO_HTTP_PORT` changes the local host port. The index builder needs network access to fetch the pinned public ONNX model the first time. In case model retrieval fails it builds SearchMe with lexical search if the embedding package can otherwise run; semantic mode remains clearly unavailable.

ScholarlySources runs as an opt-in local profile because it downloads/loads a PyTorch sentence-transformer and uses a persistent local model cache:

```powershell
docker compose --profile scholarlysources up --build
```

Its service health endpoint is `/api/health`; the gateway namespaces API calls as `/api/scholarlysources/*`. The service is memory-limited to 2 GiB in local Compose. A local run reached healthy in about 40 seconds, peaked at about 629 MiB during startup, and settled near 566 MiB; the built image was about 2.98 GB. These are one host's observations, not a production capacity guarantee. The current requirements resolved CPU-only application code with large CUDA-enabled PyTorch wheels, so a CPU-specific dependency installation should be evaluated before further deployment work. Construct is not started because its pinned app has no database bootstrap/migration and its backend requires secrets/configuration not supplied by the repository. No fake APIs are added for the other projects.

Stop services with `docker compose down`. The ScholarlySources model volume remains; remove volumes only when intentionally clearing the local cache.

## Static Cloudflare Workers deployment

Build `dist/` first with the commands above. Preview with:

```bash
npx --yes wrangler@4.162.0 dev --config infrastructure/cloudflare/wrangler.jsonc
```

The worker serves PortfolioWebsite at `/`, SearchMe at `/search/`, `/work/*` overviews through SearchMe, and successfully built `/projects/{slug}/*` apps through their own entries. Missing asset paths remain 404s. `/api/{slug}/*` requests are forwarded only when that slug is in `api-targets-render.json`; methods, query strings, bodies and relevant headers are preserved. The origin is read from the `PORTFOLIO_RENDER_ORIGIN` runtime variable, must be HTTPS, and cannot be selected by the caller. No secret is checked in. Set the variable in the Cloudflare Worker environment (or in a local `.dev.vars` file copied from `.dev.vars.example`). The q4 model and version-pinned ONNX Runtime CDN files are fetched only after a semantic query is submitted.

Deployment, if later authorized:

```bash
npx --yes wrangler@4.162.0 deploy --config infrastructure/cloudflare/wrangler.jsonc
```

No Cloudflare resource has been created or deployed. The current Render target map contains no enabled APIs, so the worker returns a clear 404 for API paths until a backend is configured and included in the Render image.

## Render image

After building the static tree and generated Render Nginx config:

```bash
python scripts/build_frontends.py
python scripts/generate_nginx.py
docker build -f infrastructure/render/Dockerfile -t portfolio-render-gateway .
```

The Dockerfile is a single Nginx gateway image and has been built and smoke-tested, but currently runs no project backend. Construct lacks database/schema setup; ScholarlySources' measured local image was 2.98 GB with about 629 MiB startup peak, and its CPU-only Docker process still resolves large CUDA wheels. It remains excluded from the Render target until a smaller CPU dependency strategy and the intended service resource budget are validated. The image must not be described as a consolidated backend bundle until an eligible backend is selected, integrated, measured, and verified. There is no persistent database in this image. Configure an external persistent database for any future app that requires one. Set Render's `PORT` to the exposed web-service port as required by the deployment configuration.

No production resources have been created, pushed, or deployed.
