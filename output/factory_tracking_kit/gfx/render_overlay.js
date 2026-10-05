// Renders the overlay (headlines, spotlight rings, chips, closing title + CTA) as transparent 1080x1920 PNGs, one per frame.
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const spec = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'work', 'spec.json'), 'utf8'));
const OUT = process.env.OV_DIR || path.join(__dirname, 'ov'); fs.mkdirSync(OUT, { recursive: true });
let frames = [];
if (process.env.FRAMES) { for (const p of process.env.FRAMES.split(',')) { if (p.includes('-')) { const [a, b] = p.split('-').map(Number); for (let i = a; i < b; i++) frames.push(i); } else frames.push(+p); } }
else for (let i = 0; i < spec.N; i++) frames.push(i);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.addInitScript((s) => { window.__SPEC = s; }, spec);
  await p.goto('file://' + path.join(__dirname, 'overlay.html'));
  await p.waitForFunction(() => window.ready === true);
  console.log('fitted font sizes:', JSON.stringify(await p.evaluate(() => [...document.querySelectorAll('[data-fit]')].map(e => e.dataset.fit + ':' + e.textContent.slice(0, 18)))));
  // safe-area check: every text line inside x 70..970 (TikTok right rail kept clear), y 230..1520, never over the card (except s9 end card)
  const probes = [[20, 's1'], [100, 's2'], [190, 's3'], [250, 's4'], [320, 's5'], [400, 's6'], [460, 's7'], [520, 's8'], [560, 's9'], [625, 's9']];
  let bad = 0;
  for (const [f, k] of probes) {
    await p.evaluate(f => window.renderAt(f), f);
    const boxes = await p.evaluate(k => [...document.querySelectorAll(`#${k} .ln`)].filter(e => getComputedStyle(e).opacity > 0.5).map(e => {
      const r = document.createRange(); r.selectNodeContents(e); const b = (e.id === 'chips' || e.id === 'cta2' || e.id === 'ft2') ? e.getBoundingClientRect() : r.getBoundingClientRect();
      const kids = (e.id === 'chips' || e.id === 'cta2' || e.id === 'ft2') ? [...e.children].map(c => c.getBoundingClientRect()) : [b];
      const l = Math.min(...kids.map(x => x.left)), rr = Math.max(...kids.map(x => x.right));
      return { t: e.textContent.trim().slice(0, 22), l, r: rr, top: b.top, bot: b.bottom };
    }), k);
    for (const x of boxes) {
      const okX = x.l >= 69.5 && x.r <= 970.5, okY = x.top >= 230 && x.bot <= 1520, overCard = k !== 's9' && x.bot > 560.5;
      if (!okX || !okY || overCard) bad++;
      console.log(`f${f} ${k}`.padEnd(9), x.t.padEnd(24), `x ${x.l.toFixed(0)}..${x.r.toFixed(0)} y ${x.top.toFixed(0)}..${x.bot.toFixed(0)}`, okX && okY && !overCard ? 'OK' : 'CHECK');
    }
  }
  const t0 = Date.now();
  for (const f of frames) {
    await p.evaluate(f => window.renderAt(f), f);
    await p.screenshot({ path: path.join(OUT, String(f).padStart(4, '0') + '.png'), omitBackground: true, type: 'png' });
  }
  console.log(`rendered ${frames.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s ; layout problems: ${bad}`);
  await b.close(); if (bad) process.exit(3);
})();
