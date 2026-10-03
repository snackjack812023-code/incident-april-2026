const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const spec = require('../kit/spec.js');
const OUT = process.env.OUT || 'ov'; fs.mkdirSync(OUT, { recursive: true });
let frames = [];
if (process.env.FRAMES) { for (const p of process.env.FRAMES.split(',')) { if (p.includes('-')) { const [a, b] = p.split('-').map(Number); for (let i = a; i < b; i++) frames.push(i); } else frames.push(+p); } }
else for (let i = 0; i < spec.N; i++) frames.push(i);
// events in R coords + frames
const EV = { cust: [968, 489, 328, 27], item: [662, 820, 256, 46], price: [1060, 817, 84, 33], total: [1188, 819, 76, 28],
  pdf: [1226, 227, 61, 37], pdfC: [1256.5, 245.5], btn1: [1079, 245], bubble: [1520, 85, 323, 67],
  click1F: 200, holdF: 219, clickF: 228, bubbleF: 256, keyFrames: [135, 144, 151] };
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.addInitScript(({ shots, ev }) => { window.__SHOTS = shots; window.__EV = ev; }, { shots: spec.shots, ev: EV });
  await p.goto('file://' + path.join(process.cwd(), 'overlay.html'));
  await p.evaluate(() => document.fonts.ready); await p.waitForFunction(() => window.ready === true);
  const info = await p.evaluate(() => ({ fits: [...document.querySelectorAll('[data-fit]')].map(e => [e.id, e.dataset.fit]) }));
  console.log('fitted font sizes:', JSON.stringify(info.fits));
  // text bounds report at representative frames
  const probes = [[0, ['s1a', 's1b']], [100, ['steps', 'cap2']], [240, ['act3']], [290, ['s4a', 's4b']], [400, ['s5a', 's5b', 's5brand']]];
  let bad = 0;
  for (const [f, ids] of probes) {
    await p.evaluate(f => window.renderAt(f), f);
    for (const id of ids) {
      const r = await p.evaluate(id => { const el = document.getElementById(id); let rect; if (id === 's5brand' || id === 's1a' || id === 's1b' || id === 's4a' || id === 's4b' || id === 's5a' || id === 's5b') { const rg = document.createRange(); rg.selectNodeContents(el); rect = rg.getBoundingClientRect(); } else { const c = el.firstElementChild && id !== 'steps' ? el.firstElementChild : el; rect = id === 'steps' ? (() => { const k = [...el.children]; const a = k[0].getBoundingClientRect(), z = k[k.length - 1].getBoundingClientRect(); return { left: a.left, right: z.right, top: a.top, bottom: a.bottom, width: z.right - a.left, height: a.height }; })() : c.getBoundingClientRect(); } return { l: rect.left, r: rect.right, t: rect.top, b: rect.bottom, w: rect.width }; }, id);
      const ok = r.l >= 60 - 0.5 && r.r <= 1020 + 0.5; if (!ok) bad++;
      console.log(`f${f} ${id}`.padEnd(14), `x ${r.l.toFixed(0)}..${r.r.toFixed(0)} (w ${r.w.toFixed(0)})  y ${r.t.toFixed(0)}..${r.b.toFixed(0)}`, ok ? 'OK' : 'OUT OF SAFE AREA');
    }
  }
  const t0 = Date.now();
  for (const f of frames) {
    await p.evaluate(f => window.renderAt(f), f);
    await p.screenshot({ path: path.join(OUT, String(f).padStart(4, '0') + '.png'), omitBackground: true, type: 'png' });
  }
  console.log(`rendered ${frames.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s ; unsafe text boxes: ${bad}`);
  await b.close();
})();
