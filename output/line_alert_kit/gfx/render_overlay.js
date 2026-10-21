// Renders the overlay (hook title, step captions, rings, ripples, "new message" badge, CTA) as transparent PNGs.
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const spec = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'work', 'edit.json'), 'utf8'));
const OUT = process.env.OV_DIR || path.join(__dirname, 'ov'); fs.mkdirSync(OUT, { recursive: true });
let frames = [];
if (process.env.FRAMES) { for (const p of process.env.FRAMES.split(',')) { if (p.includes('-')) { const [a, b] = p.split('-').map(Number); for (let i = a; i < b; i++) frames.push(i); } else frames.push(+p); } }
else for (let i = 0; i < spec.N; i++) frames.push(i);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.addInitScript((s) => { window.__SPEC = s; }, spec);
  await p.goto('file://' + path.join(__dirname, 'overlay.html'));
  await p.waitForFunction(() => window.ready === true);
  // safe-area check: text inside x 40..1040 above y 820, inside x 40..960 below (TikTok right rail), and above y 1500
  let bad = 0;
  for (const [f, sel] of [[30, '#hook .ttl, #hook .chip'], [90, '#cap .cap'], [160, '#cap .cap'], [220, '#cap .cap'], [300, '#cap .cap'], [430, '#cta .ttl, #cta .pill, #cta .tag, #c4']]) {
    await p.evaluate(f => window.renderAt(f), f);
    const boxes = await p.evaluate(sel => [...document.querySelectorAll(sel)].map(e => { const r = e.getBoundingClientRect(); return { t: e.textContent.trim().slice(0, 26), l: r.left, r: r.right, top: r.top, b: r.bottom }; }), sel);
    for (const x of boxes) {
      const maxR = x.b > 820 ? 960.5 : 1040.5, ok = x.l >= 39.5 && x.r <= maxR && x.b <= 1500 && x.top >= 140;
      if (!ok) bad++;
      console.log(`f${f}`.padEnd(5), x.t.padEnd(28), `x ${x.l.toFixed(0)}..${x.r.toFixed(0)} y ${x.top.toFixed(0)}..${x.b.toFixed(0)}`, ok ? 'OK' : 'CHECK');
    }
  }
  const t0 = Date.now();
  for (const f of frames) { await p.evaluate(f => window.renderAt(f), f); await p.screenshot({ path: path.join(OUT, String(f).padStart(4, '0') + '.png'), omitBackground: true }); }
  console.log(`rendered ${frames.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s ; layout problems: ${bad}`);
  await b.close(); if (bad) process.exit(3);
})();
