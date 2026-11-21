import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';

const REPO = '/Users/Shared/Files From e.localized/PDM/Google buildathon /Google_Startup_Buildathon';
const CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PYTHON = path.join(REPO, 'keepwell/.venv/bin/python');
const DIR = path.join(REPO, 'apps/household/build/web');
const MIME = { '.html': 'text/html', '.js': 'application/javascript', '.mjs': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.wasm': 'application/wasm', '.otf': 'font/otf', '.frag': 'text/plain' };

const srv = http.createServer((req, res) => {
  const u = (req.url || '/').split('?')[0];
  let f = path.join(DIR, u === '/' ? 'index.html' : u);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) f = path.join(DIR, 'index.html');
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});
const mocks = spawn(PYTHON, [path.join(REPO, 'mocks/run_mocks.py')], { cwd: REPO, stdio: 'pipe' });

function jpegInfo(b64) {
  const b = Buffer.from(b64, 'base64');
  if (b[0] !== 0xff || b[1] !== 0xd8) return { valid: false, bytes: b.length };
  let i = 2;
  while (i < b.length) {
    if (b[i] !== 0xff) { i++; continue; }
    const m = b[i + 1];
    if (m >= 0xc0 && m <= 0xc3) return { valid: true, bytes: b.length, height: b.readUInt16BE(i + 5), width: b.readUInt16BE(i + 7) };
    i += 2 + b.readUInt16BE(i + 2);
  }
  return { valid: true, bytes: b.length };
}

const out = {};
try {
  await new Promise((r) => srv.listen(5124, '127.0.0.1', r));
  await new Promise((r) => setTimeout(r, 1800));
  const browser = await chromium.launch({
    executablePath: CHROME_PATH, headless: true,
    args: ['--no-sandbox', '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required'],
  });
  const ctx = await browser.newContext({ permissions: ['microphone', 'camera'], viewport: { width: 420, height: 860 } });
  const page = await ctx.newPage();
  const log = { binSent: [], textSent: [], binRecv: 0, textRecv: 0, videoFrames: [] };
  page.on('websocket', (ws) => {
    ws.on('framesent', (f) => {
      if (typeof f.payload === 'string') {
        log.textSent.push(f.payload.slice(0, 100));
        try { const j = JSON.parse(f.payload); if (j.type === 'video_frame') log.videoFrames.push(jpegInfo(j.data)); } catch {}
      } else log.binSent.push(f.payload.length);
    });
    ws.on('framereceived', (f) => { if (typeof f.payload === 'string') log.textRecv++; else log.binRecv++; });
  });

  await page.goto('http://127.0.0.1:5124/#/call', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2500);
  await page.getByRole('button', { name: /Allow microphone/i }).first().click();
  await page.waitForTimeout(6000);
  const s1 = await page.evaluate(() => ({ ...window.__kwMediaStats }));
  out.dialer = {
    pcmChunksSentBinary: log.binSent.length,
    chunkSizeBytesDistinct: [...new Set(log.binSent)],
    chunkMs: [...new Set(log.binSent)].map((n) => n / 2 / 16),
    bridgeStats: s1,
    serverBinaryFramesReceived: log.binRecv,
    serverTextFramesReceived: log.textRecv,
  };

  // Mute: binary chunks must stop leaving the page.
  const before = log.binSent.length;
  const muteBtn = page.getByRole('button', { name: /mute/i }).first();
  if (await muteBtn.count()) {
    await muteBtn.click();
    await page.waitForTimeout(300);
    const mark = log.binSent.length;
    await page.waitForTimeout(1500);
    out.mute = { clicked: true, chunksDuringMute: log.binSent.length - mark, chunksBefore: before };
  } else out.mute = { clicked: false };

  // Video page
  await page.goto('http://127.0.0.1:5124/#/v/demo-video-token', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2500);
  await page.getByRole('button', { name: /Allow camera/i }).first().click();
  await page.waitForTimeout(5500);
  const v = await page.evaluate(() => {
    const el = document.querySelector('video');
    return { hasVideoEl: !!el, videoWidth: el?.videoWidth, videoHeight: el?.videoHeight, hasSrcObject: !!el?.srcObject, stats: { ...window.__kwMediaStats } };
  });
  out.video = { ...v, jpegFramesSent: log.videoFrames.length, frames: log.videoFrames.slice(0, 4),
    maxLongEdge: Math.max(0, ...log.videoFrames.map((f) => Math.max(f.width || 0, f.height || 0))) };
  await page.screenshot({ path: '/tmp/kw-audit/video_page.png' });
  await browser.close();
} catch (e) {
  out.error = String(e);
} finally {
  srv.close();
  mocks.kill('SIGTERM');
}
console.log(JSON.stringify(out, null, 2));
