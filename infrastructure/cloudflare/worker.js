const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };

async function readJsonAsset(env, request, path, fallback) {
  try {
    const assetUrl = new URL(path, request.url);
    const response = await env.ASSETS.fetch(new Request(assetUrl));
    return response.ok ? await response.json() : fallback;
  } catch {
    return fallback;
  }
}

function isHtmlNavigation(request, pathname) {
  return request.method === 'GET'
    && request.headers.get('accept')?.includes('text/html')
    && !pathname.split('/').at(-1)?.includes('.');
}

async function proxyApi(request, env, url) {
  const routes = await readJsonAsset(env, request, '/search-index/api-targets-render.json', {});
  const match = url.pathname.match(/^\/api\/([a-z0-9-]+)(\/.*)?$/);
  const slug = match?.[1];
  if (!slug || !Object.hasOwn(routes, slug)) return new Response(JSON.stringify({ error: 'No API is configured for this project.' }), { status: 404, headers: JSON_HEADERS });

  let origin;
  try {
    origin = new URL(env.PORTFOLIO_RENDER_ORIGIN);
    if (origin.protocol !== 'https:' || origin.username || origin.password || origin.pathname !== '/') throw new Error('The Render origin must be an HTTPS origin without credentials or a path.');
  } catch {
    return new Response(JSON.stringify({ error: 'The portfolio API origin is not configured.' }), { status: 503, headers: JSON_HEADERS });
  }

  const upstream = new URL(`${url.pathname}${url.search}`, origin);
  const headers = new Headers(request.headers);
  for (const name of ['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade', 'host', 'content-length']) headers.delete(name);
  headers.set('x-forwarded-host', url.host);
  headers.set('x-forwarded-proto', 'https');
  headers.set('x-forwarded-for', request.headers.get('cf-connecting-ip') ?? '');
  return fetch(upstream, { method: request.method, headers, body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body, redirect: 'manual' });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/')) return proxyApi(request, env, url);
    if (url.pathname === '/search' && request.method === 'GET') return Response.redirect(new URL('/search/', url), 308);

    const asset = await env.ASSETS.fetch(request);
    if (asset.status !== 404 || !isHtmlNavigation(request, url.pathname)) return asset;

    if (url.pathname.startsWith('/work/') || url.pathname.startsWith('/search/')) {
      const searchme = new URL('/search/index.html', url);
      return env.ASSETS.fetch(new Request(searchme, request));
    }
    if (url.pathname.startsWith('/projects/')) {
      const built = await readJsonAsset(env, request, '/search-index/built-frontends.json', { available: [] });
      const slug = url.pathname.split('/')[2];
      if (slug && built.available?.includes(slug)) {
        const appIndex = new URL(`/projects/${slug}/index.html`, url);
        const app = await env.ASSETS.fetch(new Request(appIndex, request));
        if (app.status !== 404) return app;
      }
    }
    if (!url.pathname.split('/').at(-1)?.includes('.')) {
      const portfolio = new URL('/index.html', url);
      return env.ASSETS.fetch(new Request(portfolio, request));
    }
    return new Response('Not found', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } });
  },
};
