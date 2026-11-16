// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest';
import worker from './worker.js';

function makeEnv({ available = [], apiTargets = {} } = {}) {
  return {
    ASSETS: {
      async fetch(request) {
        const url = new URL(request.url);
        if (url.pathname === '/search-index/built-frontends.json') return Response.json({ available });
        if (url.pathname === '/search-index/api-targets-render.json') return Response.json(apiTargets);
        if (url.pathname.endsWith('/index.html') && (url.pathname === '/index.html' || url.pathname === '/search/index.html' || url.pathname.includes('/projects/'))) return new Response(`<html>${url.pathname}</html>`, { status: 200, headers: { 'content-type': 'text/html' } });
        return new Response('missing', { status: 404 });
      },
    },
    PORTFOLIO_RENDER_ORIGIN: 'https://portfolio-api.example',
  };
}

afterEach(() => vi.unstubAllGlobals());

describe('Cloudflare static/API worker', () => {
  it('falls back only for a known app HTML route', async () => {
    const env = makeEnv({ available: ['scholarlysources'] });
    const response = await worker.fetch(new Request('https://portfolio.example/projects/scholarlysources/downloads/abc', { headers: { accept: 'text/html' } }), env);
    expect(response.status).toBe(200);
    expect(await response.text()).toContain('/projects/scholarlysources/index.html');
  });

  it('serves SearchMe for direct /search and /search/ navigations', async () => {
    const env = makeEnv();
    const redirected = await worker.fetch(new Request('https://portfolio.example/search', { headers: { accept: 'text/html' } }), env);
    expect(redirected.status).toBe(308);
    expect(redirected.headers.get('location')).toBe('https://portfolio.example/search/');
    const response = await worker.fetch(new Request('https://portfolio.example/search/', { headers: { accept: 'text/html' } }), env);
    expect(response.status).toBe(200);
    expect(await response.text()).toContain('/search/index.html');
  });

  it('serves project overview routes through SearchMe', async () => {
    const response = await worker.fetch(new Request('https://portfolio.example/work/construct/#authentication', { headers: { accept: 'text/html' } }), makeEnv());
    expect(response.status).toBe(200);
    expect(await response.text()).toContain('/search/index.html');
  });

  it('serves PortfolioWebsite for its text route after a direct refresh', async () => {
    const response = await worker.fetch(new Request('https://portfolio.example/notGame', { headers: { accept: 'text/html' } }), makeEnv());
    expect(response.status).toBe(200);
    expect(await response.text()).toContain('/index.html');
  });

  it('keeps a missing application asset a 404 instead of returning HTML', async () => {
    const response = await worker.fetch(new Request('https://portfolio.example/projects/scholarlysources/assets/missing.js', { headers: { accept: '*/*' } }), makeEnv({ available: ['scholarlysources'] }));
    expect(response.status).toBe(404);
    expect(await response.text()).toBe('missing');
  });

  it('proxies only allowlisted APIs and preserves method, query, and body', async () => {
    const fetchMock = vi.fn(async (_input, init) => new Response(JSON.stringify({ method: init.method, body: await new Response(init.body).text() }), { status: 202 }));
    vi.stubGlobal('fetch', fetchMock);
    const env = makeEnv({ apiTargets: { scholarlysources: { upstream_prefix: '/api' } } });
    const response = await worker.fetch(new Request('https://portfolio.example/api/scholarlysources/search?limit=3', { method: 'POST', body: '{"query":"papers"}', headers: { 'content-type': 'application/json' } }), env);
    expect(response.status).toBe(202);
    expect(fetchMock.mock.calls[0][0].toString()).toBe('https://portfolio-api.example/api/scholarlysources/search?limit=3');
    expect(await response.json()).toEqual({ method: 'POST', body: '{"query":"papers"}' });
  });

  it('does not accept an unregistered API slug', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const response = await worker.fetch(new Request('https://portfolio.example/api/arbitrary/anything'), makeEnv());
    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
