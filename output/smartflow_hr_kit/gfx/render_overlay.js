// Renders the overlay (text tags, highlight rings, end-card CTA) as transparent 1080x1920 PNGs and checks the TikTok safe zone.
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const spec = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'work', 'spec.json'), 'utf8'));
const OUT = process.env.OV_DIR || path.join(__dirname, 'ov'); fs.mkdirSync(OUT, { recursive: true });
let frames = [];
if (process.env.FRAMES) { for (const p of process.env.FRAMES.split(',')) { if (p.includes('-')) { const [a, b] = p.split('-').map(Number); for (let i = a; i < b; i++) frames.push(i); } else frames.push(+p); } }
else for (let i = 0; i < spec.N; i++) frames.push(i);
// TikTok safe zone for text: below the top bar (y >= 220), above caption/username (y <= 1500), clear of the right action rail (x <= 960 below y 700)
const SAFE = { top: 220, bottom: 1500, left: 60, right: 1020, railX: 960, railY: 700 };
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.addInitScript((s) => { window.__SPEC = s; }, spec);
  await p.goto('file://' + path.join(__dirname, 'overlay.html'));
  await p.waitForFunction(() => window.ready === true);
  let bad = 0; const report = [];
  for (const f of [100, 160, 220, 290, 375, 440, 520, 570, 599]) {
    await p.evaluate(f => window.renderAt(f), f);
    const boxes = await p.evaluate(() => [...document.querySelectorAll('.tag, #cta')].filter(e => getComputedStyle(e).display !== 'none' && +getComputedStyle(e).opacity > 0.5)
      .map(e => { const r = e.getBoundingClientRect(); return { id: e.id, t: e.textContent.trim(), l: r.left, r: r.right, top: r.top, b: r.bottom }; }));
    for (const x of boxes) {
      const maxR = x.b > SAFE.railY ? SAFE.railX : SAFE.right;
      const ok = x.l >= SAFE.left && x.r <= maxR && x.top >= SAFE.top && x.b <= SAFE.bottom;
      if (!ok) bad++;
      report.push({ f, ...x, ok });
      console.log(`f${f}`.padEnd(5), x.t.padEnd(30), `x ${x.l.toFixed(0)}..${x.r.toFixed(0)} y ${x.top.toFixed(0)}..${x.b.toFixed(0)}`, ok ? 'SAFE' : 'OUTSIDE SAFE ZONE');
    }
  }
  fs.writeFileSync(path.join(__dirname, '..', 'work', 'safezone.json'), JSON.stringify({ SAFE, report, bad }, null, 1));
  const t0 = Date.now();
  for (const f of frames) { await p.evaluate(f => window.renderAt(f), f); await p.screenshot({ path: path.join(OUT, String(f).padStart(4, '0') + '.png'), omitBackground: true }); }
  console.log(`rendered ${frames.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s ; text outside safe zone: ${bad}`);
  await b.close(); if (bad) process.exit(3);
})();
