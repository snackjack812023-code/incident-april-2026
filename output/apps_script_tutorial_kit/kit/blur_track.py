"""Per-frame privacy-blur lines -> work/blur_track.json  {clip: {source_frame: [[xL, yL, xR, yR, h], ...]}}
Every BLUR key (a text line verified on its frame) is tracked frame by frame through the frames its clip shows: phase
correlation of the band's surroundings predicts the motion, the joint whole-line fit (linefit) snaps both ends back
onto the text. Between two keys the forward track of the first and the backward track of the second are blended
(they must agree; the largest disagreement is printed), then lightly smoothed in time."""
import json, os, sys, subprocess
import numpy as np, cv2
from scipy.ndimage import gaussian_filter1d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl, timeline as TL, linefit as LF

FPS = TL.FPS; SRC = os.path.join(TL.W, 'src30.mp4')

def read_gray(k0, n):
    raw = subprocess.run(['ffmpeg', '-v', 'quiet', '-ss', f'{(k0 - 0.5) / FPS:.4f}', '-i', SRC, '-frames:v', str(n),
                          '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 1920, 1080).astype(np.float32)

def shown_frames(c):
    ks = set()
    for f in range(c['f0'], c['f1']):
        t = TL.src_time(c, f); t = min(t, c['hold']) if c.get('hold') else t
        ks.add(int(round(t * FPS)))
    return sorted(ks)

def local_shift(g0, g1, ln, pad=70):
    xL, yL, xR, yR = ln
    x0, x1 = int(max(0, min(xL, xR) - pad)), int(min(1080, max(xL, xR) + pad))
    y0, y1 = int(max(0, min(yL, yR) - pad)), int(min(1920, max(yL, yR) + pad))
    a, b = g0[y0:y1, x0:x1], g1[y0:y1, x0:x1]
    if a.shape[0] < 16 or a.shape[1] < 16: return 0.0, 0.0
    (dx, dy), resp = cv2.phaseCorrelate(a, b, cv2.createHanningWindow((a.shape[1], a.shape[0]), cv2.CV_32F))
    if resp < 0.03 or abs(dx) > 80 or abs(dy) > 80: return 0.0, 0.0
    return dx, dy

def track(G, E, k_seed, ln, s_ref, k_to, kmin):
    """follow line ln from frame k_seed to k_to (either direction); returns {k: (xL, yL, xR, yR, score)}"""
    out = {k_seed: (*ln, s_ref)}; step = 1 if k_to > k_seed else -1; k = k_seed
    while k != k_to:
        n = k + step; dx, dy = local_shift(G[k - kmin], G[n - kmin], ln)
        p = (ln[0] + dx, ln[1] + dy, ln[2] + dx, ln[3] + dy)
        yL, yR, s = LF.fit(E[n - kmin], p[0], p[1], p[2], p[3], win=8)
        if s < 0.45 * s_ref: yL, yR = p[1], p[3]                  # motion-blurred frame: trust the prediction
        ln = (p[0], yL, p[2], yR); out[n] = (*ln, s); k = n
    return out

def segments(cid, keys):
    if cid == 'R1':
        s0, s1 = edl.BLUR_SWING
        return [[k for k in keys if k[0] < s0], [k for k in keys if k[0] > s1]], (s0, s1)
    return [keys], None

if __name__ == '__main__':
    result = {}
    for cid, keys in edl.BLUR.items():
        c = TL.BY_ID[cid]; ks = shown_frames(c); kmin, kmax = ks[0], ks[-1]
        G = read_gray(kmin, kmax - kmin + 1); assert len(G) == kmax - kmin + 1, (cid, len(G))
        E = [LF.energy(g) for g in G]
        segs, swing = segments(cid, keys); table = {}
        for si, seg in enumerate(segs):
            if swing:
                lo = kmin if si == 0 else int(np.ceil(swing[1] * FPS)); hi = int(np.floor(swing[0] * FPS)) if si == 0 else kmax
            else: lo, hi = kmin, kmax
            times = sorted({k[0] for k in seg}); groups = [[k for k in seg if k[0] == t] for t in times]
            nlines = len(groups[0]); assert all(len(g) == nlines for g in groups), cid
            for li in range(nlines):
                seeds = []
                for g in groups:
                    t, xL, yL, xR, yR, h = g[li]; kk = int(round(t * FPS))
                    for _ in range(3):                               # snap the key onto the text (re-centred search)
                        nL, nR, s = LF.fit(E[kk - kmin], xL, yL, xR, yR, win=12)
                        if abs(nL - yL) < 0.5 and abs(nR - yR) < 0.5: break
                        if abs(nL - yL) > 0.5 or abs(nR - yR) > 0.5: print(f'      key {cid} {t} line{li}: {yL:.0f},{yR:.0f} -> {nL:.0f},{nR:.0f} (score {s:.0f})')
                        yL, yR = nL, nR
                    oL, oR = xL <= 5, xR >= 1070                     # the text runs on past the frame edge: open end
                    k_ = (yR - yL) / (xR - xL)
                    if oL: yL, xL = yL + k_ * (-900 - xL), -900
                    if oR: yR, xR = yR + k_ * (1980 - xR), 1980
                    seeds.append((kk, (xL, yL, xR, yR), s, h, (oL, oR)))
                rows = {}
                for i, (kk, ln, s, h, op) in enumerate(seeds):
                    a = seeds[i - 1][0] if i > 0 else lo; b = seeds[i + 1][0] if i + 1 < len(seeds) else hi
                    fw, bw = track(G, E, kk, ln, s, b, kmin), track(G, E, kk, ln, s, a, kmin)
                    for k, v in {**bw, **fw}.items(): rows.setdefault(k, []).append((kk, v, h, op))
                kk_all = sorted(rows); dis = 0.0; lines = []
                for k in kk_all:
                    cand = rows[k]
                    if len(cand) == 1: v = np.array(cand[0][1][:4]); h = cand[0][2]
                    else:
                        (ka, va, ha, opa), (kb, vb, hb, opb) = sorted(cand, key=lambda r: r[0])[:2]
                        w = (k - ka) / max(1, kb - ka); va, vb = np.array(va[:4]), np.array(vb[:4])
                        h = (1 - w) * ha + w * hb
                        # compare / blend the lines where both are on screen, then take each end from a key that saw
                        # that end of the text (a closed end) rather than from one where it ran past the frame edge
                        xa_, xb_ = max(0.0, max(va[0], vb[0])), min(1079.0, min(va[2], vb[2]))
                        ya = lambda q, x: q[1] + (q[3] - q[1]) * (x - q[0]) / (q[2] - q[0])
                        if xb_ - xa_ > 40:
                            dis = max(dis, abs(ya(va, xa_) - ya(vb, xa_)), abs(ya(va, xb_) - ya(vb, xb_)))
                        xs = []
                        for e in (0, 1):
                            ia, ib = va[2 * e], vb[2 * e]
                            if opa[e] == opb[e]: xs.append((1 - w) * ia + w * ib)
                            else: xs.append(ia if not opa[e] else ib)
                        yl = (1 - w) * ya(va, xs[0]) + w * ya(vb, xs[0]); yr = (1 - w) * ya(va, xs[1]) + w * ya(vb, xs[1])
                        v = np.array([xs[0], yl, xs[1], yr])
                    lines.append((k, v, h))
                arr = np.array([v for _, v, _ in lines]); arr = gaussian_filter1d(arr, 1.0, axis=0, mode='nearest')
                for (k, _, h), v in zip(lines, arr):
                    table.setdefault(str(k), []).append([round(float(x), 1) for x in v] + [round(float(h), 1)])
                sc = [rows[k][0][1][4] for k in kk_all]
                print(f'{cid:5s} seg{si} line{li}: frames {kk_all[0]}-{kk_all[-1]}  seed scores {[round(s[2]) for s in seeds]}  '
                      f'min/median score {min(sc):.0f}/{np.median(sc):.0f}  max fwd/bwd disagreement {dis:.1f}px')
        result[cid] = table
    json.dump(result, open(os.path.join(TL.W, 'blur_track.json'), 'w'))
    print('frames with bands:', sum(len(v) for v in result.values()))
