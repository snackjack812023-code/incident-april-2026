// Timeline spec: reel segments (footage selection / pacing) + camera shots (R-coords) + events.
const K = require('./lib.js');
const FPS = 30, N = 449;                         // 14.967 s  (<= 15 s)

// ---- reel segments: n frames each; src time t0; speed; hold (freeze) ; reverse (play backwards)
const segments = [
  // S1 hook (0-2.0s): clean wide view of the system, B 0.00-2.00
  { id: 's1',  scene: 1, src: 'B', t0: 0.00, speed: 1,   n: 60 },
  // S2 (2.0-6.0s): customer -> item -> price typing (real typing at B 4.95/5.20/5.47), cut before the stray extra "0" at 6.07
  { id: 's2a', scene: 2, src: 'B', t0: 2.45, speed: 1,   n: 33 },
  { id: 's2b', scene: 2, src: 'B', t0: 3.55, speed: 1,   n: 33 },
  { id: 's2c', scene: 2, src: 'B', t0: 4.65, speed: 1,   n: 39 },
  { id: 's2d', scene: 2, src: 'B', t0: 5.9167, hold: true, n: 15 },
  // S3 (6.0-9.0s): cursor -> finish editing click (B 11.05) -> travel to PDF (1.2x) -> 0.30s beat -> PDF click (B 12.2) -> saved -> download bubble (B 13.15)
  { id: 's3a', scene: 3, src: 'B', t0: 10.35, speed: 1,   n: 21 },
  { id: 's3b', scene: 3, src: 'B', t0: 11.05, speed: 1.2, n: 18 },
  { id: 's3c', scene: 3, src: 'B', t0: 11.80, hold: true,  n: 6 },
  { id: 's3d', scene: 3, src: 'B', t0: 12.10, speed: 1, n: 45 },
  // S4 (9.0-12.0s): result opens in viewer (C 4.82) -> real viewer zoom 22%->36% (C 6.62-7.62 @1.25x) -> cut-in to crisp top view (window A)
  { id: 's4a', scene: 4, src: 'C', t0: 4.82, speed: 1,    n: 18 },
  { id: 's4b', scene: 4, src: 'C', t0: 6.62, speed: 1.25, n: 24 },
  { id: 's4c', scene: 4, src: 'C', t0: 8.60, speed: 1,    n: 26 },                 // window A fwd  (k=0..25)
  { id: 's4d', scene: 4, src: 'C', t0: 9.40, reverse: true, n: 22 },               // k=24..3
  // S5 (12.0-14.97s): end card = crisp top view; ping-pong inside window A (C 8.60-9.43, hand static -> removed by delogo)
  { id: 's5a', scene: 5, src: 'C', t0: 8.6667, reverse: true, n: 3 },              // k=2..0
  { id: 's5b', scene: 5, src: 'C', t0: 8.6333, speed: 1, n: 25 },                  // k=1..25
  { id: 's5c', scene: 5, src: 'C', t0: 9.40, reverse: true, n: 25 },               // k=24..0
  { id: 's5d', scene: 5, src: 'C', t0: 8.6333, speed: 1, n: 25 },                  // k=1..25
  { id: 's5e', scene: 5, src: 'C', t0: 9.40, reverse: true, n: 11 },               // k=24..14
];
let acc = 0; segments.forEach(s => { s.f0 = acc; acc += s.n; s.f1 = acc; });
if (acc !== N) throw new Error('segments sum ' + acc + ' != ' + N);
const F = Object.fromEntries(segments.map(s => [s.id, s]));
const scene = { 1: [0, 60], 2: [60, 180], 3: [180, 270], 4: [270, 360], 5: [360, 449] };

// ---- camera shots (R coords; rect = {u,v,w}) ----
const C = K.rectC;
const shots = [
  // S1: gentle push-in from wide system view to the modal
  { f0: 0,   f1: 60,  a: { u: 10, v: 8, w: 1520 }, b: C(963, 590, 1180), ease: 'io' },
  // S2: three framings with slow push (ease-out) -- v6: crops kept wide enough that the source is upscaled <= ~1.6x
  { f0: 60,  f1: 93,  a: C(1040, 560, 860), b: C(1040, 560, 820), ease: 'out3' },        // 1 customer (TO block)
  { f0: 93,  f1: 126, a: C(960, 700, 860),  b: C(960, 710, 820), ease: 'out3' },         // 2 item row
  { f0: 126, f1: 180, a: C(1100, 740, 800), b: C(1100, 740, 760), ease: 'out3' },        // 3 price typing
  // S3: toolbar wide -> anticipation push -> PUNCH to PDF -> hold -> pan to download bubble (crops stay below the URL bar)
  { f0: 180, f1: 219, a: C(1190, 410, 860), b: C(1190, 410, 840), ease: 'lin' },
  { f0: 219, f1: 228, a: C(1190, 410, 840), b: C(1235, 370, 780), ease: 'in3' },         // anticipation (the ~0.3s beat)
  { f0: 228, f1: 237, a: C(1235, 370, 780), b: C(1250, 340, 660), ease: 'out4' },        // punch zoom at click (B 12.2)
  { f0: 237, f1: 245, a: C(1250, 340, 660), b: C(1252, 340, 650), ease: 'lin' },         // slow drift
  { f0: 245, f1: 256, a: C(1252, 340, 650), b: { u: 1180, v: 20, w: 740 }, ease: 'io' }, // pan to buttons + download bubble
  { f0: 256, f1: 270, a: { u: 1180, v: 20, w: 740 }, b: { u: 1186, v: 22, w: 728 }, ease: 'lin' },
  // S4/S5: document viewer (clean crop, no viewer chrome)
  { f0: 270, f1: 360, a: C(853, 510, 966), b: C(853, 510, 936), ease: 'lin' },
  { f0: 360, f1: 449, a: C(853, 510, 936), b: C(855, 495, 800), ease: 'io' },
];
const cam = K.makeCam(shots);
// ---- sound events: frame, sfx name, target peak dBFS (original audio is muted; SFX only, no BGM: no licensed music file was provided)
const LEAD = 0.02;   // seconds: audio slightly ahead of the picture so it feels in sync
const sfxEvents = [
  { f: 60,  name: 'whoosh_soft',  peak: -22, off: -0.12 },   // cut into the demo
  { f: 93,  name: 'tick',         peak: -28 },   // step 2
  { f: 126, name: 'tick',         peak: -28 },   // step 3
  { f: 135, name: 'key',          peak: -22 },   // typed digits (B 4.95 / 5.20 / 5.47)
  { f: 144, name: 'key',          peak: -22 },
  { f: 151, name: 'key',          peak: -22 },
  { f: 200, name: 'click_soft',   peak: -21 },   // finish-editing click (B 11.05)
  { f: 228, name: 'click_main',   peak: -12 },   // hero click on PDF (B 12.2) + punch zoom
  { f: 228, name: 'whoosh_punch', peak: -21 },
  { f: 256, name: 'pop_soft',     peak: -27 },   // download bubble appears
  { f: 270, name: 'success',      peak: -7  },   // result appears
  { f: 360, name: 'whoosh_soft',  peak: -23, off: -0.12 },   // end card text
];
module.exports = { FPS, N, segments, F, scene, shots, cam, K, sfxEvents, LEAD };
