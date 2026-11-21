import { chromium } from 'playwright-core';
import http from 'node:http';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

function serve(coep) {
  return new Promise((resolve) => {
    const s = http.createServer((req, res) => {
      const h = { 'Content-Type': 'text/html', 'Cross-Origin-Opener-Policy': 'same-origin-allow-popups' };
      if (coep) h['Cross-Origin-Embedder-Policy'] = coep;
      res.writeHead(200, h);
      res.end(`<!doctype html><html><head>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400&family=Roboto:wght@400&display=swap">
<script src="https://pay.google.com/gp/p/js/pay.js" async></script></head>
<body><h1 style="font-family:'Noto Sans Devanagari'">नमस्ते</h1>
<iframe id="looker" src="https://lookerstudio.google.com/embed/reporting/00000000-0000-0000-0000-000000000000/page/1" width="400" height="200"></iframe>
<iframe id="maps" src="https://www.google.com/maps?q=Hyderabad&output=embed" width="400" height="200"></iframe>
<img id="mapimg" src="https://maps.googleapis.com/maps/api/staticmap?center=Hyderabad&zoom=10&size=100x100">
</body></html>`);
    });
    s.listen(0, '127.0.0.1', () => resolve(s));
  });
}

const results = {};
for (const coep of [null, 'credentialless', 'require-corp']) {
  const s = await serve(coep);
  const port = s.address().port;
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox'] });
  const page = await (await browser.newContext()).newPage();
  const failed = [];
  const consoleErr = [];
  page.on('requestfailed', (r) => failed.push(`${r.url().slice(0, 70)} :: ${r.failure()?.errorText}`));
  page.on('console', (m) => { if (m.type() === 'error') consoleErr.push(m.text().slice(0, 140)); });
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'load', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(5000);
  const info = await page.evaluate(async () => ({
    crossOriginIsolated: self.crossOriginIsolated,
    payJsLoaded: typeof window.google === 'object' && !!window.google?.payments,
    fontsStatus: document.fonts.check("16px 'Noto Sans Devanagari'"),
    fontFaces: [...document.fonts].filter((f) => f.status === 'loaded').length,
    lookerFrameBlocked: false,
  }));
  const frames = page.frames().map((f) => f.url().slice(0, 60));
  results[coep || 'none'] = { info, failed, consoleErr, frames };
  await browser.close();
  s.close();
}
console.log(JSON.stringify(results, null, 2));
