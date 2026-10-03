// Shared math for the SmartFlow TikTok build kit (runs in Node and in the browser overlay page).
(function (root) {
  const FPS = 30;
  // Measured screen corners in the camera frame (source px): TL, TR, BL, BR  (inset 3px so no bezel slivers)
  const SCREEN_SRC = [[182, 91], [1731, 155], [288, 903], [1586, 878]];
  const RW = 1920, RH = 1080;           // "rectified screen" coordinate system (R coords)
  const CARD = { x: 40, y: 560, w: 1000, h: 700, r: 30 };   // video card on the 1080x1920 canvas
  const ASPECT = CARD.w / CARD.h;

  function inset(q, d) {
    const cx = q.reduce((s, p) => s + p[0], 0) / 4, cy = q.reduce((s, p) => s + p[1], 0) / 4;
    return q.map(([x, y]) => { const vx = cx - x, vy = cy - y, l = Math.hypot(vx, vy); return [x + vx / l * d, y + vy / l * d]; });
  }
  function solve(A, b) {           // gaussian elimination, n x n
    const n = b.length; const M = A.map((r, i) => r.concat([b[i]]));
    for (let c = 0; c < n; c++) {
      let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
      [M[c], M[p]] = [M[p], M[c]];
      for (let r = c + 1; r < n; r++) { const f = M[r][c] / M[c][c]; for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
    }
    const x = new Array(n).fill(0);
    for (let r = n - 1; r >= 0; r--) { let s = M[r][n]; for (let k = r + 1; k < n; k++) s -= M[r][k] * x[k]; x[r] = s / M[r][r]; }
    return x;
  }
  function homography(src, dst) {  // maps src[i] -> dst[i]
    const A = [], b = [];
    for (let i = 0; i < 4; i++) {
      const [u, v] = src[i], [x, y] = dst[i];
      A.push([u, v, 1, 0, 0, 0, -u * x, -v * x]); b.push(x);
      A.push([0, 0, 0, u, v, 1, -u * y, -v * y]); b.push(y);
    }
    const h = solve(A, b); return [h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1];
  }
  const H = homography([[0, 0], [RW, 0], [0, RH], [RW, RH]], inset(SCREEN_SRC, 3));   // R -> camera source
  function apply(h, u, v) { const w = h[6] * u + h[7] * v + 1; return [(h[0] * u + h[1] * v + h[2]) / w, (h[3] * u + h[4] * v + h[5]) / w]; }
  const toSrc = (u, v) => apply(H, u, v);

  // rect in R coords: {u, v, w}  (h derived from card aspect)
  const rectH = (r) => r.w / ASPECT;
  const rectC = (cx, cy, w) => ({ u: cx - w / 2, v: cy - w / ASPECT / 2, w });
  const lerp = (a, b, t) => a + (b - a) * t;
  const lerpRect = (a, b, t) => ({ u: lerp(a.u, b.u, t), v: lerp(a.v, b.v, t), w: lerp(a.w, b.w, t) });
  const EASE = {
    lin: (p) => p,
    io: (p) => 0.5 - 0.5 * Math.cos(Math.PI * p),
    out3: (p) => 1 - Math.pow(1 - p, 3),
    out4: (p) => 1 - Math.pow(1 - p, 4),
    in3: (p) => p * p * p,
    iocubic: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
  };
  // shots: [{f0, f1, a:{u,v,w}, b:{u,v,w}, ease}]  (f1 exclusive).  rectAt(frame) -> rect
  function makeCam(shots) {
    return function rectAt(f) {
      let s = shots.find((s) => f >= s.f0 && f < s.f1);
      if (!s) s = f < shots[0].f0 ? shots[0] : shots[shots.length - 1];
      const len = Math.max(1, s.f1 - 1 - s.f0);
      let p = Math.min(1, Math.max(0, (f - s.f0) / len));
      return lerpRect(s.a, s.b, (EASE[s.ease || 'lin'])(p));
    };
  }
  // quad (8 numbers in camera-source px) for an R-rect: TL, TR, BL, BR
  function quadOf(r) {
    const h = rectH(r);
    const tl = toSrc(r.u, r.v), tr = toSrc(r.u + r.w, r.v), bl = toSrc(r.u, r.v + h), br = toSrc(r.u + r.w, r.v + h);
    return [tl[0], tl[1], tr[0], tr[1], bl[0], bl[1], br[0], br[1]];
  }
  // R-coords -> card px at frame f
  function toCard(rectAt, f, u, v) { const r = rectAt(f); const s = CARD.w / r.w; return [CARD.x + (u - r.u) * s, CARD.y + (v - r.u * 0 - r.v) * s]; }

  // piecewise-linear ffmpeg expression for series y[0..N-1] with knots; balanced binary tree
  // (ffmpeg's expression parser limits nesting depth to ~100, so a linear if-chain is not allowed)
  function pwlExpr(y, knots, v = 'in') {
    const fmt = (x) => (Math.abs(x) < 1e-9 ? '0' : x.toFixed(4).replace(/\.?0+$/, ''));
    const segs = [];
    for (let i = 0; i < knots.length - 1; i++) {
      const s = knots[i], e = knots[i + 1];
      const d = y[e] - y[s];
      segs.push({ s, e, x: Math.abs(d) < 1e-9 ? fmt(y[s]) : `${fmt(y[s])}+(${fmt(d)})*(${v}-${s})/${e - s}` });
    }
    const build = (lo, hi) => {
      if (lo === hi) return segs[lo].x;
      const mid = (lo + hi) >> 1;
      return `if(lt(${v},${segs[mid + 1].s}),${build(lo, mid)},${build(mid + 1, hi)})`;
    };
    return build(0, segs.length - 1);
  }
  // choose knots adaptively so max error <= tol px (also at every change of static/anim state)
  function adaptiveKnots(series, N, tol = 0.04, maxK = 12) {
    const knots = [0];
    let s = 0;
    while (s < N - 1) {
      let e = Math.min(N - 1, s + maxK);
      while (e > s + 1) {
        let ok = true;
        for (let i = s + 1; i < e; i++) {
          const t = (i - s) / (e - s);
          for (const ys of series) { if (Math.abs(ys[s] + (ys[e] - ys[s]) * t - ys[i]) > tol) { ok = false; break; } }
          if (!ok) break;
        }
        if (ok) break; e--;
      }
      knots.push(e); s = e;
    }
    return knots;
  }
  const api = { FPS, RW, RH, CARD, ASPECT, H, toSrc, rectH, rectC, lerpRect, EASE, makeCam, quadOf, toCard, pwlExpr, adaptiveKnots, SCREEN_SRC };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.KIT = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
