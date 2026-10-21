// Renders the overlay (keyword tags, focus rings) as transparent 1080x1920 PNGs and checks every visible tag against the
// TikTok safe zone (spec.safe: below the top tabs, above the caption area, clear of the right action rail).
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const spec = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'work', 'spec.json'), 'utf8'));
const OUT = process.env.OV_DIR || path.join(__dirname, 'ov'); fs.mkdirSync(OUT, { recursive: true });
let frames = [];
if (process.env.FRAMES) { for (const p of process.env.FRAMES.split(',')) { if (p.includes('-')) { const [a, b] = p.split('-').map(Number); for (let i = a; i < b; i++) frames.push(i); } else frames.push(+p); } }
else for (let i = 0; i < spec.N; i++) frames.push(i);
const SAFE = spec.safe;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.addInitScript((s) => { window.__SPEC = s; }, spec);
  await p.goto('file://' + path.join(__dirname, 'overlay.html'));
  await p.waitForFunction(() => window.ready === true);
  let bad = 0, n = 0; const report = [];
  for (let f = 0; f < spec.N; f++) {                       // every frame: each visible tag must be inside the safe zone
    await p.evaluate(f => window.renderAt(f), f);
    const boxes = await p.evaluate(() => [...document.querySelectorAll('.tag')].filter(e => getComputedStyle(e).display !== 'none' && +getComputedStyle(e).opacity > 0.3)
      .map(e => { const r = e.getBoundingClientRect(); return { t: e.textContent.trim(), l: r.left, r: r.right, top: r.top, b: r.bottom }; }));
    for (const x of boxes) {
      n++; const maxR = x.b > SAFE.rail_y ? SAFE.rail_x : SAFE.right;
      const ok = x.l >= SAFE.left && x.r <= maxR && x.top >= SAFE.top && x.b <= SAFE.bottom;
      if (!ok) { bad++; if (bad < 10) console.log(`f${f}`, x.t, `x ${x.l.toFixed(0)}..${x.r.toFixed(0)} y ${x.top.toFixed(0)}..${x.b.toFixed(0)} OUTSIDE SAFE ZONE`); }
      if (!report.find(q => q.t === x.t)) { report.push({ f, ...x, ok }); console.log(`f${f}`.padEnd(5), x.t.padEnd(22), `x ${x.l.toFixed(0)}..${x.r.toFixed(0)} y ${x.top.toFixed(0)}..${x.b.toFixed(0)}`, ok ? 'SAFE' : 'OUTSIDE'); }
    }
  }
  fs.writeFileSync(path.join(__dirname, '..', 'work', 'safezone.json'), JSON.stringify({ SAFE, checked: n, bad, first: report }, null, 1));
  const t0 = Date.now();
  for (const f of frames) { await p.evaluate(f => window.renderAt(f), f); await p.screenshot({ path: path.join(OUT, String(f).padStart(4, '0') + '.png'), omitBackground: true }); }
  console.log(`rendered ${frames.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s ; tag boxes checked ${n}, outside safe zone: ${bad}`);
  await b.close(); if (bad) process.exit(3);
})();
