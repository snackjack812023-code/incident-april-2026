// Builds the "plate" filter graph: blurred BG (from the footage) + perspective-corrected screen card with smooth zoom.
const { N, cam, K } = require('./spec.js');
const A_ = K.CARD;

function quadSeries() {
  const ser = Array.from({ length: 8 }, () => new Array(N));
  for (let f = 0; f < N; f++) { const q = K.quadOf(cam(f)); for (let i = 0; i < 8; i++) ser[i][f] = q[i]; }
  return ser;
}
function perspectiveFilter(startFrame = 0) {
  const ser = quadSeries();
  const knots = K.adaptiveKnots(ser, N, 0.03, 30);
  const v = `(in-1+${startFrame})`;   // perspective's 'in' counter is 1-based
  const names = ['x0', 'y0', 'x1', 'y1', 'x2', 'y2', 'x3', 'y3'];
  const parts = names.map((n, i) => `${n}='${K.pwlExpr(ser[i], knots, v)}'`);
  return { str: `perspective=${parts.join(':')}:eval=frame:interpolation=cubic:sense=source`, knots: knots.length };
}
// BG recipe (tunable)
const BG = process.env.BG_RECIPE || "eq=brightness=-0.10:contrast=1.0,format=gbrp,curves=all='0/0.03 0.5/0.24 1/0.50',lutrgb=r='val*0.42':g='val*0.74':b='val*1.22'";
function graph({ startFrame = 0, out = 'plate' } = {}) {
  const p = perspectiveFilter(startFrame);
  const g = [
    `[0:v]setpts=N/(30*TB),format=yuv420p,split=2[bgsrc][cardsrc0]`,
    // privacy: blur the Apps Script web-app URL (deployment id) while the browser bar is still in frame (first ~1 s)
    `[cardsrc0]split=2[ca][cb]`,
    `[cb]gblur=sigma=7:steps=2[cbl]`,
    `[4:v]format=gray[um]`,
    `[cbl][um]alphamerge[cbm]`,
    `[ca][cbm]overlay=0:0:format=yuv420:enable='lt(n+${startFrame},32)'[cardsrc]`,
    `[bgsrc]scale=-2:1920:flags=bicubic,crop=1080:1920:(in_w-1080)/2:0,scale=270:480:flags=area,gblur=sigma=16:steps=3,scale=1080:1920:flags=bicubic,${BG},format=gbrp[bg]`,
    `[cardsrc]delogo=x=1014:y=519:w=34:h=34:enable='gte(n+${startFrame},${require('./spec.js').F.s4c.f0})',hqdn3d=1:1:4:3,smartblur=lr=2.5:ls=1:lt=10:cr=1:cs=0:ct=0,pad=1920:1344:0:0:black,${p.str},scale=${A_.w}:${A_.h}:flags=lanczos+accurate_rnd,format=rgba,colorlevels=rimax=0.865:gimax=0.865:bimax=0.915,cas=strength=0.8,format=rgba[c1]`,
    `[1:v]format=gray[m]`,
    `[c1][m]alphamerge[card]`,
    `[bg][2:v]overlay=0:0:format=gbrp:shortest=0[b1]`,
    `[b1][card]overlay=${A_.x}:${A_.y}:format=gbrp[b2]`,
    `[b2][3:v]overlay=0:0:format=gbrp[b3]`,
    `[b3]scale=out_color_matrix=bt709:out_range=tv:flags=bicubic+accurate_rnd,format=yuv420p[${out}]`,
  ];
  return { text: g.join(';\n'), knots: p.knots };
}
module.exports = { graph, perspectiveFilter };
if (require.main === module) { const r = graph(); console.log(r.text.length, 'chars; knots', r.knots); }
