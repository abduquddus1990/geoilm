// index.html ni kadrma-kadr render qilib, FFmpeg orqali ovozsiz MP4 yasaydi.
// Ishlatish: node render.js <chiqish.mp4> <events.json>
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path');

const OUT = process.argv[2] || 'silent.mp4';
const EVENTS = process.argv[3] || 'events.json';
const FPS = +(process.env.FPS || 30);

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || undefined,
    args: ['--run-all-compositor-stages-before-draw'],
  });
  const page = await browser.newPage({ viewport: { width: 720, height: 1280 } });
  page.on('pageerror', e => console.error('Sahifa xatosi:', e.message));
  await page.goto('file://' + path.join(__dirname, 'index.html'));
  await page.waitForFunction('window.READY === true', { timeout: 60000 });

  const D = await page.evaluate('DURATION');
  fs.writeFileSync(EVENTS, JSON.stringify({ D, ev: await page.evaluate('EVENTS') }));
  const N = Math.round(D * FPS);

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-vf', 'scale=1080:1920:flags=lanczos', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', OUT],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const cdp = await page.context().newCDPSession(page);
  const t0 = Date.now();
  for (let f = 0; f < N; f++) {
    await page.evaluate(`render(${f / FPS})`);
    const r = await cdp.send('Page.captureScreenshot', { format: 'jpeg', quality: 93, optimizeForSpeed: true });
    if (!ff.stdin.write(Buffer.from(r.data, 'base64'))) await new Promise(res => ff.stdin.once('drain', res));
    if (f % 300 === 0) console.log(`  kadr ${f}/${N}  (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg xato: ' + c)))));
  await browser.close();
  console.log(`Render tugadi: ${OUT} (${D.toFixed(1)} s)`);
})().catch(e => { console.error(e); process.exit(1); });
