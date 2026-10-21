// Renders the v7 overlay (texts, step pills, cursor, rings, ripples) as transparent PNGs 1080x1920, one per frame.
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const spec = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'work', 'spec7.json'), 'utf8'));
// overlay folder comes from OV_DIR (not OUT: build.sh uses OUT for the final MP4)
const OUT = process.env.OV_DIR || path.join(__dirname, 'ov'); fs.mkdirSync(OUT, { recursive: true });
let frames = [];
if (process.env.FRAMES) { for (const p of process.env.FRAMES.split(',')) { if (p.includes('-')) { const [a, b] = p.split('-').map(Number); for (let i = a; i < b; i++) frames.push(i); } else frames.push(+p); } }
else for (let i = 0; i < spec.N; i++) frames.push(i);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.addInitScript((s) => { window.__SPEC = s; }, spec);
  await p.goto('file://' + path.join(__dirname, 'overlay7.html'));
  await p.waitForFunction(() => window.ready === true);
  const fits = await p.evaluate(() => [...document.querySelectorAll('[data-fit]')].map(e => [e.id, e.dataset.fit]));
  console.log('fitted font sizes:', JSON.stringify(fits));
  // safe-area report: every text block must stay inside x 60..1020 and must not overlap the card/paper
  const S = spec.scene;
  const probes = [[10, ['s1a', 's1b'], 'A'], [120, ['steps', 'cap2'], 'A'], [220, ['act3'], 'A'], [300, ['s4a', 's4b'], 'B'], [420, ['s5a', 's5b', 's5brand'], 'B']];
  let bad = 0;
  for (const [f, ids, plate] of probes) {
    await p.evaluate(f => window.renderAt(f), f);
    for (const id of ids) {
      const r = await p.evaluate(id => {
        const el = document.getElementById(id); let rect;
        if (id === 'steps') { const k = [...el.children]; const a = k[0].getBoundingClientRect(), z = k[k.length - 1].getBoundingClientRect(); rect = { left: a.left, right: z.right, top: a.top, bottom: a.bottom }; }
        else if (el.classList.contains('cap') || el.classList.contains('act')) rect = el.firstElementChild.getBoundingClientRect();
        else { const rg = document.createRange(); rg.selectNodeContents(el); rect = rg.getBoundingClientRect(); }
        return { l: rect.left, r: rect.right, t: rect.top, b: rect.bottom };
      }, id);
      const box = plate === 'A' ? { t: 560, b: 1260 } : { t: 546, b: 1363 };
      const inX = r.l >= 59.5 && r.r <= 1020.5, clear = r.b <= box.t + 0.5 || r.t >= box.b - 0.5;
      if (!inX || !clear) bad++;
      console.log(`f${f} ${id}`.padEnd(13), `x ${r.l.toFixed(0)}..${r.r.toFixed(0)}  y ${r.t.toFixed(0)}..${r.b.toFixed(0)}`, inX ? '' : 'OUT-OF-SAFE-X', clear ? 'OK' : 'OVERLAPS-UI');
    }
  }
  const t0 = Date.now();
  for (const f of frames) {
    await p.evaluate(f => window.renderAt(f), f);
    await p.screenshot({ path: path.join(OUT, String(f).padStart(4, '0') + '.png'), omitBackground: true, type: 'png' });
  }
  console.log(`rendered ${frames.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s ; text layout problems: ${bad}`);
  await b.close(); if (bad) process.exit(3);
})();
