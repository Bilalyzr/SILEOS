/**
 * Static file server + API reverse proxy for the frontend container.
 *
 * `serve -s dist` (the previous container command) cannot proxy: every
 * /api/v1 request on the published :3000 port was answered with the SPA's
 * index.html, so a browser hitting the container directly got HTML instead
 * of JSON and every data page failed. nginx (:3100 / the production edge)
 * already routes /api/v1 to the backend before requests reach this
 * container, so the proxy here only matters when :3000 is used directly —
 * but it makes that entry point behave exactly like the edge.
 *
 * Routing mirrors nginx/conf.d/default.conf:
 *   /api/v1/stream/extract  -> backend      (video extraction lives there)
 *   /api/v1/stream/*        -> streaming service (:8001)
 *   /api/v1/*               -> backend      (:8000)
 *   everything else         -> dist/ with SPA fallback to index.html
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = Number(process.env.PORT || 3000);
const DIST = path.join(__dirname, 'dist');
const BACKEND = process.env.BACKEND_ORIGIN || 'http://backend:8000';
const STREAMING = process.env.STREAMING_ORIGIN || 'http://streaming-service:8001';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.eot': 'application/vnd.ms-fontobject',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.mp3': 'audio/mpeg',
  '.pdf': 'application/pdf',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml',
  '.webmanifest': 'application/manifest+json',
  '.wasm': 'application/wasm',
};

function proxy(req, res, target) {
  const url = new URL(target);
  // Forward headers as-is — like nginx's `proxy_set_header Host $host`, the
  // client's original Host survives so the backend's TrustedHostMiddleware
  // (allow-list: localhost / 127.0.0.1 / the prod domains) accepts it.
  // Rewriting it to the upstream name (backend:8000) gets a 400.
  const upstream = http.request(
    {
      protocol: url.protocol,
      hostname: url.hostname,
      port: url.port,
      method: req.method,
      path: req.url,
      headers: req.headers,
    },
    (up) => {
      res.writeHead(up.statusCode || 502, up.headers);
      up.pipe(res);
    },
  );
  upstream.on('error', (err) => {
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json' });
    }
    res.end(JSON.stringify({ detail: 'Service temporarily unavailable.' }));
    console.error(`proxy error ${req.method} ${req.url}:`, err.message);
  });
  req.pipe(upstream);
}

function serveStatic(req, res) {
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  } catch {
    pathname = '/';
  }
  let file = path.normalize(path.join(DIST, pathname));
  // Resolve the public/labs runtime directory that Vite copies to dist/labs.
  if (!file.startsWith(DIST)) {
    res.writeHead(403);
    return res.end('Forbidden');
  }
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) {
      // SPA fallback: unknown paths (client-side routes) get index.html.
      file = path.join(DIST, 'index.html');
    }
    const ext = path.extname(file).toLowerCase();
    const stream = fs.createReadStream(file);
    stream.on('open', () => {
      res.writeHead(200, {
        'Content-Type': MIME[ext] || 'application/octet-stream',
        'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=3600',
      });
      stream.pipe(res);
    });
    stream.on('error', () => {
      res.writeHead(404);
      res.end('Not found');
    });
  });
}

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/v1/stream/extract')) {
    return proxy(req, res, BACKEND);
  }
  if (req.url.startsWith('/api/v1/stream/')) {
    return proxy(req, res, STREAMING);
  }
  if (req.url.startsWith('/api/')) {
    return proxy(req, res, BACKEND);
  }
  return serveStatic(req, res);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`frontend listening on :${PORT} (api -> ${BACKEND}, stream -> ${STREAMING})`);
});
