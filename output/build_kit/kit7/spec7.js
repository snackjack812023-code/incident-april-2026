// v7 timeline: everything is built from crisp sources (screenshots 1920x1080 + PDF page image).
// Writes work/spec7.json (per-frame camera, cursor, paper offset, events) used by the plate renderer, overlay and SFX mixer.
const fs = require('fs'), path = require('path');
const FPS = 30, N = 449;                                   // 14.967 s
const CARD = { x: 40, y: 560, w: 1000, h: 700, r: 30 };     // plate A: screenshot card
const PAPER = { x: 160, y: 546, w: 760, h: 817, r: 14 };    // plate B: PDF paper
const AA = CARD.w / CARD.h, PA = PAPER.w / PAPER.h;
const scene = { 1: [0, 60], 2: [60, 189], 3: [189, 244], 4: [244, 360], 5: [360, 449] };
const step = { 1: [60, 102], 2: [102, 142], 3: [142, 189] };

const EASE = {
  lin: p => p, io: p => 0.5 - 0.5 * Math.cos(Math.PI * p), out3: p => 1 - Math.pow(1 - p, 3), out4: p => 1 - Math.pow(1 - p, 4),
  in3: p => p * p * p, iocubic: p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
};
const lerp = (a, b, t) => a + (b - a) * t;
const C = (cx, cy, w) => ({ u: cx - w / 2, v: cy - w / AA / 2, w });       // screenshot coords (card aspect)
const CP = (cx, cy, w) => ({ u: cx - w / 2, v: cy - w / PA / 2, w });      // PDF page coords (paper aspect)
function track(shots) {   // shots: [f0, f1, a, b, ease] (f1 exclusive) -> per-frame rect
  return f => {
    let s = shots.find(s => f >= s[0] && f < s[1]); if (!s) s = f < shots[0][0] ? shots[0] : shots[shots.length - 1];
    const p = Math.min(1, Math.max(0, (f - s[0]) / Math.max(1, s[1] - 1 - s[0]))), e = EASE[s[4]](p);
    return { u: lerp(s[2].u, s[3].u, e), v: lerp(s[2].v, s[3].v, e), w: lerp(s[2].w, s[3].w, e) };
  };
}
// ---- plate A camera (screenshot px). Crops stay >= ~750 px wide (source upscaled <= 1.33x) except the short punch zoom (1.5x).
const camA = track([
  [0, 60, C(960, 578, 1240), C(960, 581, 1080), 'io'],             // S1 gentle push-in to the whole quotation editor
  [60, 70, C(960, 581, 1080), C(1110, 655, 800), 'out3'],          // S2-1 quick zoom to customer (TO) block
  [70, 102, C(1110, 655, 800), C(1112, 657, 770), 'lin'],
  [102, 142, C(905, 402, 800), C(905, 404, 770), 'lin'],           // S2-2 (cut) item row
  [142, 151, C(905, 404, 770), C(1105, 404, 780), 'io'],           // S2-3 pan to price + totals
  [151, 189, C(1105, 404, 780), C(1108, 406, 752), 'lin'],
  [189, 205, C(1108, 406, 752), C(1224, 440, 800), 'io'],          // S3 reframe on toolbar (below the browser URL bar / app header)
  [205, 213, C(1224, 440, 800), C(1226, 438, 792), 'lin'],
  [213, 221, C(1226, 438, 792), C(1238, 424, 756), 'in3'],         // 0.27 s hover beat (anticipation)
  [221, 230, C(1238, 424, 756), C(1250, 392, 660), 'out4'],        // PUNCH zoom on click
  [230, 244, C(1250, 392, 660), C(1251, 392, 648), 'lin'],
]);
// ---- plate B camera (PDF page px, doc 1588 x 1707 visible part; bank details below y=1707 never enter the frame)
const FULL = { u: 0.05, v: 0, w: 1587.9 };
const camB = track([
  [244, 252, FULL, FULL, 'lin'],
  [252, 332, FULL, CP(1060, 1201, 940), 'io'],                      // S4 zoom in: customer, line item, grand total
  [332, 360, CP(1060, 1201, 940), CP(1062, 1203, 920), 'lin'],
  [360, 392, CP(1062, 1203, 920), { u: 30, v: 30, w: 1528 }, 'io'], // S5 back out to the whole quotation
  [392, 449, { u: 30, v: 30, w: 1528 }, { u: 57, v: 80, w: 1474 }, 'lin'],
]);
// ---- typing (frames of each keystroke) + clicks
const typing = {
  to:    { click: 68,  keys: [71, 72, 73, 75, 76, 77, 79, 80, 81, 83] },
  item:  { click: 109, keys: [112, 113, 114, 115, 117, 118, 119, 120, 121, 123, 124, 125, 126, 127, 129, 130, 131] },
  price: { click: 150, keys: [153, 156, 158, 161] },
};
const totalsAt = 164;                       // auto-calculated totals appear right after the last digit
const hover = [213, 221], press = [221, 225], clickF = 221;
// ---- cursor path (screenshot px)
const P = {
  rest: [1395, 818], to: [1213, 687], item: [884, 366], price: [1112, 366], pdf: [1270, 249],
};
const moves = [   // [f0, f1, from, to, ease, bend]
  [50, 66, P.rest, P.to, 'io', 0.10],
  [102, 108, P.to, P.item, 'io', 0.06],
  [142, 149, P.item, P.price, 'io', -0.08],
  [193, 212, P.price, P.pdf, 'iocubic', 0.16],
];
function cursorAt(f) {
  let pos = P.rest;
  for (const [f0, f1, a, b, e, bend] of moves) {
    if (f >= f1) pos = b;
    else if (f >= f0) {
      const t = EASE[e]((f - f0) / (f1 - f0));
      const dx = b[0] - a[0], dy = b[1] - a[1];                     // quadratic bezier with a perpendicular bend
      const cx = (a[0] + b[0]) / 2 - dy * bend, cy = (a[1] + b[1]) / 2 + dx * bend;
      pos = [(1 - t) * (1 - t) * a[0] + 2 * (1 - t) * t * cx + t * t * b[0], (1 - t) * (1 - t) * a[1] + 2 * (1 - t) * t * cy + t * t * b[1]];
      break;
    }
  }
  const img = f < 102 ? 's5' : 's4';
  const inR = (r) => pos[0] >= r[0] && pos[0] <= r[2] && pos[1] >= r[1] && pos[1] <= r[3];
  const fields = img === 's5' ? [[966, 673, 1295, 697]] : [[657, 352, 944, 376], [1095, 352, 1176, 376]];
  const buttons = img === 's5' ? [] : [[1224, 223, 1289, 260]];
  const type = buttons.some(inR) ? 'hand' : fields.some(inR) ? 'ibeam' : 'arrow';
  const clicks = [typing.to.click, typing.item.click, typing.price.click, clickF];
  const pressed = clicks.some(c => f >= c && f < c + 4);
  return { x: +pos[0].toFixed(2), y: +pos[1].toFixed(2), type, pressed };
}
// ---- overlay highlight events (source px)
const rings = [
  { key: 'to',    plate: 'A', rect: [966, 673, 330, 24], on: 62,  off: 102, pad: 8 },
  { key: 'item',  plate: 'A', rect: [657, 352, 287, 24], on: 104, off: 142, pad: 8 },
  { key: 'price', plate: 'A', rect: [1095, 352, 81, 24], on: 146, off: 189, pad: 7 },
  { key: 'total', plate: 'A', rect: [999, 493, 301, 48], on: totalsAt, off: 189, pad: 7, flashAt: [totalsAt] },
  { key: 'pdf',   plate: 'A', rect: [1224, 223, 65, 37], on: hover[0], off: clickF + 14, pad: 8, cls: 'cy2' },
  { key: 'docTotal', plate: 'B', rect: [880, 1548, 600, 97], on: 300, off: 356, pad: 12 },
];
const ripples = [
  { key: 'r1', f: typing.to.click, x: 1213, y: 687, size: 0.55 },
  { key: 'r2', f: typing.item.click, x: 884, y: 366, size: 0.55 },
  { key: 'r3', f: typing.price.click, x: 1112, y: 366, size: 0.55 },
  { key: 'r4', f: clickF, x: 1270, y: 249, size: 1.0 },
  { key: 'r5', f: clickF, x: 1270, y: 249, size: 1.35, delay: 4 },
];
// ---- SFX (original audio not used; SFX synthesised; no BGM unless a licensed file is provided)
const LEAD = 0.02;
const keyEv = (keys, peak) => keys.filter((_, i) => i % 3 === 0).map(f => ({ f, name: 'key', peak }));
const sfxEvents = [
  { f: 60, name: 'whoosh_soft', peak: -24, off: -0.12 },
  { f: typing.to.click, name: 'click_soft', peak: -24 },
  ...keyEv(typing.to.keys, -29),
  { f: 102, name: 'tick', peak: -28 },
  { f: typing.item.click, name: 'click_soft', peak: -24 },
  ...keyEv(typing.item.keys, -29),
  { f: 142, name: 'tick', peak: -28 },
  { f: typing.price.click, name: 'click_soft', peak: -24 },
  ...typing.price.keys.map(f => ({ f, name: 'key', peak: -25 })),
  { f: totalsAt, name: 'pop_soft', peak: -25 },
  { f: clickF, name: 'click_main', peak: -12 },
  { f: clickF, name: 'whoosh_punch', peak: -22 },
  { f: 244, name: 'success', peak: -7 },
  { f: 360, name: 'whoosh_soft', peak: -23, off: -0.12 },
];
// ---- per-frame arrays
const frames = [];
for (let f = 0; f < N; f++) {
  const plate = f < scene[4][0] ? 'A' : 'B';
  const fr = { f, plate };
  if (plate === 'A') { fr.cam = camA(f); fr.img = f < 102 ? 's5' : 's4'; fr.cursor = cursorAt(f); fr.hover = f >= hover[0] && f < press[1]; fr.pressed = f >= press[0] && f < press[1]; }
  else { fr.cam = camB(f); const p = Math.min(1, (f - 244) / 9); fr.dy = Math.round(70 * (1 - EASE.out3(p))); }
  fr.cam = { u: +fr.cam.u.toFixed(3), v: +fr.cam.v.toFixed(3), w: +fr.cam.w.toFixed(3) };
  fr.bg = f < 102 ? 's5' : 's4'; fr.bgZoom = +(1 + 0.06 * f / (N - 1)).toFixed(5);
  frames.push(fr);
}
// sanity: crops inside sources
for (const fr of frames) {
  const r = fr.cam, h = r.w / (fr.plate === 'A' ? AA : PA), W = fr.plate === 'A' ? 1920 : 1588, H = fr.plate === 'A' ? 1080 : 1707;
  if (r.u < -0.01 || r.v < -0.01 || r.u + r.w > W + 0.01 || r.v + h > H + 0.2) throw new Error(`crop out of source at f${fr.f}: ${JSON.stringify(r)} h=${h.toFixed(1)}`);
}
const out = { FPS, N, CARD, PAPER, scene, step, typing, totalsAt, hover, press, clickF, rings, ripples, sfxEvents, LEAD, frames };
fs.writeFileSync(path.join(__dirname, '..', 'work', 'spec7.json'), JSON.stringify(out));
const ups = frames.filter(f => f.plate === 'A').map(f => 1000 / f.cam.w), upsB = frames.filter(f => f.plate === 'B').map(f => 760 / f.cam.w);
console.log(`spec7: ${N} frames (${(N / FPS).toFixed(3)} s); A scale ${Math.min(...ups).toFixed(2)}..${Math.max(...ups).toFixed(2)}x, B scale ${Math.min(...upsB).toFixed(2)}..${Math.max(...upsB).toFixed(2)}x; sfx ${sfxEvents.length}`);
module.exports = out;
