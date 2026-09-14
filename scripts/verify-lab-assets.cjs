/* Browser verification of an extracted release, without the development server.
 * Install playwright, or set PLAYWRIGHT_MODULE to an existing installation.
 * Usage: node scripts/verify-lab-assets.cjs <frontend directory> <report directory>
 */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(process.argv[2] || 'frontend');
const out = path.resolve(process.argv[3] || 'output/lab-verification');
const publicRoot = path.join(root, 'public');
const labs = JSON.parse(fs.readFileSync(path.join(root, 'labs/catalog/labs.json')));
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.png': 'image/png', '.glb': 'model/gltf-binary' };
const server = http.createServer((req, res) => {
  const file = path.resolve(publicRoot, '.' + decodeURIComponent(new URL(req.url, 'http://local').pathname));
  if (!file.startsWith(publicRoot + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); res.end('Missing asset'); return; }
  res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  fs.mkdirSync(out, { recursive: true });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ headless: true,
    ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}),
    args: ['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const results = [];
  try {
    for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
      const context = await browser.newContext({ viewport });
      for (const lab of labs) {
        const page = await context.newPage(), errors = [];
        page.on('pageerror', error => errors.push(error.message));
        page.on('response', response => { if (response.status() >= 400 && !response.url().endsWith('/favicon.ico')) errors.push(`${response.status()} ${new URL(response.url()).pathname}`); });
        let scene;
        try {
          await page.goto(base + lab.embed_url, { waitUntil: 'load' });
          await page.waitForFunction(() => !window.L3 || window.__sashaScene?.ready, null, { timeout: 7000 });
          scene = await page.evaluate(() => ({
            webgl: !!window.__sashaScene,
            drawCalls: window.__sashaScene?.renderer.info.render.calls || 0,
            canvas: [...document.querySelectorAll('canvas')].some(c => c.width > 100 && c.height > 100),
            domStage: !!document.querySelector('.lk-stage svg, .lk-stage table td, .lk-stage button'),
            overflow: document.documentElement.scrollWidth > innerWidth + 2,
          }));
          if (!scene.canvas && !scene.domStage) errors.push('No initialized canvas or interactive DOM stage');
          if (scene.webgl && !scene.drawCalls) errors.push('WebGL scene has no draw calls');
          if (scene.overflow) errors.push('Horizontal overflow');
          const slider = page.locator('input[type=range]').first();
          if (await slider.count()) { await slider.focus(); await slider.press('ArrowRight'); }
          if (lab.slug === 'cbse-dna-helix-3d') {
            const unzip = page.locator('#unzip');
            if (await unzip.count()) { await unzip.focus(); for (let i=0;i<20;i++) await unzip.press('ArrowRight'); }
            await page.screenshot({ path: path.join(out, `dna-${viewport.width}.png`) });
          }
        } catch (error) { errors.push(error.message); }
        results.push({ slug: lab.slug, viewport: viewport.width, ...scene, errors });
        await page.close();
      }
      await context.close();
    }
  } finally { await browser.close(); server.close(); }
  const report = { root, cases: results.length, failed: results.filter(r => r.errors.length).length, results };
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ cases: report.cases, failures: results.filter(r => r.errors.length) }, null, 2));
  process.exitCode = report.failed ? 1 : 0;
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
