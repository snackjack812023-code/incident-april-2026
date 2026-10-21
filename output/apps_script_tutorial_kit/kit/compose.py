"""Renders the edited picture (1080x1920, 30 fps) -> work/video.mp4 (no audio).
Per output frame: the source frame from the CFR working copy, a light stabilisation (high-frequency hand shake removed,
deliberate camera moves kept), the clip's zoom/pan (never stretched: uniform scale only), a mild unsharp mask for the
on-screen text, highlight rings/boxes on the button being clicked (they follow the camera), then the pre-rendered
overlays (subtitles, STEP pills, tips, hook/result/CTA text) with short fades/pops.
usage: compose.py [out.mp4] [--frames a-b] [--png dir]"""
import json, os, subprocess, sys, time
import numpy as np, cv2
from scipy.ndimage import gaussian_filter1d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl, timeline as TL

FPS, OW, OH = TL.FPS, 1080, 1920
W = TL.W; SRC = os.path.join(W, 'src30.mp4')
cv2.setNumThreads(4)

# ---------------- stabilisation (content path from per-frame phase correlation of the original recording)
def stab_path():
    m = np.load(os.path.join(W, 'motion.npz'))['m']
    pts = np.array([float(l.strip().strip(',')) for l in open(os.path.join(W, 'pts.txt')) if l.strip()])
    n = min(len(m), len(pts)); m, pts = m[:n], pts[:n]
    d = m[:, :2].astype(np.float64) * 4                      # quarter-res -> full-res px / frame (content shift)
    mag = np.hypot(d[:, 0], d[:, 1]); jump = mag > 40          # pause/resume cuts and whip pans: not shake
    d[jump] = 0; d = np.clip(d, -25, 25)
    P = np.cumsum(d, axis=0)
    t30 = np.arange(int(pts[-1] * FPS) + 2) / FPS
    P30 = np.stack([np.interp(t30, pts, P[:, i]) for i in range(2)], 1)
    jt = pts[jump]; seg = np.searchsorted(jt, t30)              # smooth each uninterrupted stretch on its own
    Ps = np.empty_like(P30)
    for s in np.unique(seg):
        i = seg == s; Ps[i] = gaussian_filter1d(P30[i], sigma=12, axis=0, mode='nearest') if i.sum() > 3 else P30[i]
    return P30, np.clip(Ps - P30, -45, 45)
P30, CORR = stab_path()

def content_shift(t_from, t_to):
    a, b = int(round(t_from * FPS)), int(round(t_to * FPS)); a = min(max(a, 0), len(P30) - 1); b = min(max(b, 0), len(P30) - 1)
    return P30[b] - P30[a]

def transform(c, f, t_src):
    """2x3 matrix source px -> output px (uniform scale only)"""
    z, cx, cy = TL.zoom_at(c, f)
    k = min(max(int(round(t_src * FPS)), 0), len(CORR) - 1)
    cx, cy = cx - CORR[k, 0], cy - CORR[k, 1]
    cx = min(max(cx, 540 / z), 1080 - 540 / z); cy = min(max(cy, 960 / z), 1920 - 960 / z)
    return np.float32([[z, 0, 540 - cx * z], [0, z, 960 - cy * z]])

# ---------------- overlays
ITEMS = json.load(open(os.path.join(W, 'ov', 'items.json')))
META = json.load(open(os.path.join(W, 'ov', 'meta.json')))
PNG = {}
def png(i):
    if i not in PNG:
        a = cv2.imread(os.path.join(W, 'ov', i + '.png'), cv2.IMREAD_UNCHANGED)
        PNG[i] = (a[..., [2, 1, 0]].astype(np.float32), a[..., 3:4].astype(np.float32) / 255.0)
    return PNG[i]

def ease_out_back(p, s=1.6): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2

def blend(dst, rgb, al, x, y):
    h, w = al.shape[:2]; x0, y0 = max(0, x), max(0, y); x1, y1 = min(OW, x + w), min(OH, y + h)
    if x0 >= x1 or y0 >= y1: return
    s = dst[y0:y1, x0:x1]; a = al[y0 - y:y1 - y, x0 - x:x1 - x]
    dst[y0:y1, x0:x1] = s * (1 - a) + rgb[y0 - y:y1 - y, x0 - x:x1 - x] * a

def draw_items(img, f):
    for it in ITEMS:
        if not (it['f0'] <= f < it['f1']): continue
        rgb, al = png(it['id']); m = META[it['id']]; M = m['margin']
        k_in, k_out = f - it['f0'], it['f1'] - 1 - f
        op = min(1.0, (k_in + 1) / 5.0, (k_out + 1) / 5.0); sc = 1.0; dx = 0
        if it['anim'] == 'pop': sc = 0.86 + 0.14 * ease_out_back(min(1.0, (k_in + 1) / 9.0))
        if it['anim'] == 'slide': dx = int(-50 * (1 - min(1.0, (k_in + 1) / 8.0)) ** 2)
        if it['anim'] == 'sub': op = min(1.0, (k_in + 1) / 3.0, (k_out + 1) / 3.0)
        if sc != 1.0:
            rgb_s = cv2.resize(rgb, None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR)
            al_s = cv2.resize(al, None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR)[..., None]
        else: rgb_s, al_s = rgb, al
        h, w = al_s.shape[:2]; bw, bh = m['box_w'] * sc, m['box_h'] * sc; Ms = M * sc
        if it['anchor'] == 'bottom': x, y = it['x'] - w / 2, it['y'] - bh - Ms
        elif it['anchor'] == 'top': x, y = it['x'] - w / 2, it['y'] - Ms
        elif it['anchor'] == 'center': x, y = it['x'] - w / 2, it['y'] - h / 2
        else: x, y = it['x'] - Ms + dx, it['y'] - Ms
        blend(img, rgb_s, al_s * op, int(round(x)), int(round(y)))

AMBER = np.array([255, 205, 60], np.float32)
def draw_rings(img, c, f, t_src, Mx, t_vis=None):
    """t_vis: source time of the picture (differs from t_src while a hold freezes the picture)"""
    if not c['ring'] and not c['box']: return
    t_vis = t_src if t_vis is None else t_vis
    t0a = edl.ANCHOR_T.get(c['id'], t_vis)
    sh = content_shift(t0a, t_vis)
    layer = np.zeros((OH, OW), np.float32); edge = np.zeros((OH, OW), np.float32)
    for (r0, r1, x, y) in c['ring']:
        if not (r0 <= t_src <= r1): continue
        p = Mx @ np.array([x + sh[0], y + sh[1], 1.0]); age = t_src - r0; left = r1 - t_src
        a = min(1.0, age / 0.18, left / 0.15); rad = int(round(46 + 7 * np.sin(2 * np.pi * 1.4 * age) * min(1, age / 0.3)))
        rad = int(rad * (0.7 + 0.3 * min(1.0, age / 0.2)))
        cv2.circle(edge, (int(p[0]), int(p[1])), rad, a, 13, cv2.LINE_AA)
        cv2.circle(layer, (int(p[0]), int(p[1])), rad, a, 6, cv2.LINE_AA)
    for (r0, r1, x0, y0, x1, y1) in c['box']:
        if not (r0 <= t_src <= r1): continue
        q0 = Mx @ np.array([x0 + sh[0], y0 + sh[1], 1.0]); q1 = Mx @ np.array([x1 + sh[0], y1 + sh[1], 1.0])
        a = min(1.0, (t_src - r0) / 0.18, (r1 - t_src) / 0.15); pad = 10
        cv2.rectangle(edge, (int(q0[0]) - pad, int(q0[1]) - pad), (int(q1[0]) + pad, int(q1[1]) + pad), a, 13, cv2.LINE_AA)
        cv2.rectangle(layer, (int(q0[0]) - pad, int(q0[1]) - pad), (int(q1[0]) + pad, int(q1[1]) + pad), a, 6, cv2.LINE_AA)
    if layer.max() <= 0: return
    e = cv2.GaussianBlur(edge, (0, 0), 3)[..., None] * 0.45
    img *= (1 - e)                                                             # soft dark halo for contrast
    l = layer[..., None]; img[:] = img * (1 - l) + AMBER * l

# ---------------- privacy blur (Web App URL / deployment ID)
TRACK_PATH = os.path.join(W, 'blur_track.json')
TRACK = json.load(open(TRACK_PATH)) if os.path.exists(TRACK_PATH) else {}
def blur_bands(c, t_vis):
    """[(L, R, h)] text centre lines in source px for this picture time, from the per-frame tracking of the BLUR keys
    (kit/blur_track.py); frames outside the table (R1's whip pan) get none"""
    rows = TRACK.get(c['id'], {}).get(str(int(round(t_vis * FPS))), [])
    return [(np.array(r[0:2], float), np.array(r[2:4], float), float(r[4])) for r in rows]

def draw_blur(img, c, t_vis, Mx):
    """soft privacy blur inside each band only: a normalised blur over the band's own pixels, so the dark editor or
    bezel next to a dialog edge is not smeared into it; feathered edge"""
    for L, R, h in blur_bands(c, t_vis):
        d = (R - L) / max(1e-6, np.linalg.norm(R - L)); n = np.array([-d[1], d[0]]); h = h + 4    # margin for descenders
        quad = np.array([L - 14 * d - h * n, R + 14 * d - h * n, R + 14 * d + h * n, L - 14 * d + h * n])
        q = (Mx[:, :2] @ quad.T).T + Mx[:, 2]
        X0, Y0 = int(max(0, q[:, 0].min() - 40)), int(max(0, q[:, 1].min() - 40))
        X1, Y1 = int(min(OW, q[:, 0].max() + 40)), int(min(OH, q[:, 1].max() + 40))
        if X1 - X0 < 8 or Y1 - Y0 < 8: continue
        region = img[Y0:Y1, X0:X1]
        m = np.zeros(region.shape[:2], np.float32)
        cv2.fillConvexPoly(m, np.round(q - [X0, Y0]).astype(np.int32), 1.0, cv2.LINE_AA)
        num = cv2.GaussianBlur(region * m[..., None], (0, 0), 13); den = cv2.GaussianBlur(m, (0, 0), 13)[..., None]
        bl = num / np.maximum(den, 1e-3)
        mf = cv2.GaussianBlur(m, (0, 0), 3)[..., None]
        img[Y0:Y1, X0:X1] = region * (1 - mf) + bl * mf

# ---------------- source frames
class Reader:
    def __init__(self): self.p = None; self.k = None
    def open(self, k0):
        if self.p: self.p.kill(); self.p.stdout.close(); self.p.wait()        # jumping to another part of the source
        # seek half a frame early: ffmpeg keeps frames with pts >= ss, so frame k0 is always the first one out
        self.p = subprocess.Popen(['ffmpeg', '-v', 'quiet', '-ss', f'{(k0 - 0.5) / FPS:.4f}', '-i', SRC, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=OW * OH * 3 * 4)
        self.k = k0; self.cur = None
    def get(self, k):
        if self.p is None or k < self.k - 1 or k > self.k + 90: self.open(k)
        while self.cur is None or self.k <= k:
            b = self.p.stdout.read(OW * OH * 3)
            if len(b) < OW * OH * 3: break
            self.cur = np.frombuffer(b, np.uint8).reshape(OH, OW, 3); self.k += 1
        return self.cur

FREEZE = {}
def frame(f, rd):
    c = TL.clip_at(f); t = TL.src_time(c, f)
    if c['freeze'] is not None:
        if c['id'] not in FREEZE:
            k = int(round(c['freeze'] * FPS)); src = rd.get(k).astype(np.float32)
            Mx = transform(c, c['f0'], c['freeze'])
            img = cv2.warpAffine(src, Mx, (OW, OH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
            FREEZE[c['id']] = cv2.GaussianBlur(img, (0, 0), 5) * 0.42
        img = FREEZE[c['id']].copy()
        p = min(1.0, (f - c['f0'] + 1) / 6.0)                               # ease into the dimmed still
        if p < 1.0:
            k = int(round(c['freeze'] * FPS)); src = rd.get(k).astype(np.float32)
            sharp = cv2.warpAffine(src, transform(c, f, c['freeze']), (OW, OH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
            img = sharp * (1 - p) + img * p
    else:
        tv = min(t, c['hold']) if c.get('hold') else t                       # picture time (holds still after `hold`)
        k = int(round(tv * FPS)); src = rd.get(k)
        Mx = transform(c, f, tv)
        img = cv2.warpAffine(src, Mx, (OW, OH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        img = cv2.addWeighted(img, 1.35, cv2.GaussianBlur(img, (0, 0), 1.1), -0.35, 0)     # text crispness after the zoom
        draw_blur(img, c, tv, np.vstack([Mx, [0, 0, 1]]).astype(np.float64)[:2])
        draw_rings(img, c, f, t, np.vstack([Mx, [0, 0, 1]]).astype(np.float64)[:2], tv)
    draw_items(img, f)
    return np.clip(img, 0, 255).astype(np.uint8)

def parse(sel):
    if not sel: return list(range(TL.N))
    out = []
    for p in sel.split(','):
        if '-' in p: a, b = map(int, p.split('-')); out += list(range(a, b))
        else: out.append(int(p))
    return out

if __name__ == '__main__':
    args = sys.argv[1:]; out = args[0] if args and not args[0].startswith('--') else os.path.join(W, 'video.mp4')
    frames = parse(args[args.index('--frames') + 1]) if '--frames' in args else parse('')
    pngdir = args[args.index('--png') + 1] if '--png' in args else None
    rd = Reader(); t0 = time.time()
    if pngdir:
        os.makedirs(pngdir, exist_ok=True)
        for f in frames: cv2.imwrite(os.path.join(pngdir, f'{f:05d}.png'), frame(f, rd)[..., ::-1])
    else:
        enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                                '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level:v', '4.1',
                                '-g', '60', '-bf', '2', '-tune', 'film', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                                '-color_range', 'tv', out], stdin=subprocess.PIPE)
        for n, f in enumerate(frames):
            enc.stdin.write(frame(f, rd).tobytes())
            if n % 300 == 0: print(f'  frame {f}/{TL.N} ({time.time() - t0:.0f}s)', flush=True)
        enc.stdin.close(); enc.wait()
    print(f'{len(frames)} frames in {time.time() - t0:.0f}s -> {pngdir or out}')
