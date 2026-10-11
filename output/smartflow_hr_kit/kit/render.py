"""Renders the picture plate (1080x1920, 30 fps) from the 4x super-resolved storyboard panels -> lossless FFV1.
Per frame and scene layer: camera (spec.cam) -> affine warp of the SR panel (Lanczos; 2x mip level when zoomed out),
feathered rounded panel edge over a soft-focus extension of the same panel (no black bars, no stretching),
180-degree-shutter motion blur on fast moves, crossfade between scene layers around cuts.
usage: python3 render.py [out.mkv] [frames 0-600 | 10,50] [--png dir]"""
import math, os, subprocess, sys, time
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); WORK = os.path.join(ROOT, 'work')
OW, OH, PAD = S.OW, S.OH, 460            # PAD: extension margin in 1x panel px
cv2.setNumThreads(4)

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

class Panel:
    def __init__(self, k):
        self.k = k
        sr = cv2.imread(os.path.join(WORK, f'sr_p{k}.png'), cv2.IMREAD_COLOR)            # BGR, 4x
        clean = cv2.imread(os.path.join(WORK, f'clean_p{k}.png'), cv2.IMREAD_COLOR)      # BGR, 1x
        self.w1, self.h1 = clean.shape[1], clean.shape[0]
        # rounded-rect alpha (drops the storyboard's white gutter corners), soft edge
        def mask(m):
            a = np.zeros((self.h1 * m, self.w1 * m), np.float32); r = int(9 * m); i = int(1.5 * m)
            x0, y0, x1, y1 = i, i, self.w1 * m - 1 - i, self.h1 * m - 1 - i
            cv2.rectangle(a, (x0 + r, y0), (x1 - r, y1), 1.0, -1); cv2.rectangle(a, (x0, y0 + r), (x1, y1 - r), 1.0, -1)
            for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)): cv2.circle(a, (cx, cy), r, 1.0, -1, cv2.LINE_AA)
            return cv2.GaussianBlur(a, (0, 0), 2.6 * m)
        self.lv = {4: (sr, mask(4)), 2: (cv2.resize(sr, (self.w1 * 2, self.h1 * 2), interpolation=cv2.INTER_AREA), mask(2))}
        # soft-focus extension: reflect-padded panel, blur grows and light falls off with distance from the panel edge
        big = cv2.copyMakeBorder(clean, PAD, PAD, PAD, PAD, cv2.BORDER_REFLECT_101).astype(np.float32)
        near, far = cv2.GaussianBlur(big, (0, 0), 5), cv2.GaussianBlur(big, (0, 0), 34)
        yy, xx = np.mgrid[0:big.shape[0], 0:big.shape[1]].astype(np.float32)
        dx = np.maximum(np.maximum(PAD - xx, xx - (PAD + self.w1 - 1)), 0); dy = np.maximum(np.maximum(PAD - yy, yy - (PAD + self.h1 - 1)), 0)
        d = np.sqrt(dx * dx + dy * dy)[..., None]
        t = smoothstep(0, 55, d)
        ext = near * (1 - t) + far * t
        navy = np.array([44, 16, 8], np.float32)                                       # BGR
        ext = ext * (1 - 0.58 * t) + navy * (0.26 * t)
        self.bg = ext

    def view(self, cam):
        """render this panel through camera (cx, cy, w) -> float32 BGR (OH, OW, 3)"""
        cx, cy, w = cam; h = w * OH / OW; s = OW / w; u, v = cx - w / 2, cy - h / 2
        m = 4 if s / 4 >= 0.8 else 2
        img, alpha = self.lv[m]
        M = np.float32([[s / m, 0, 0.5 * s / m - u * s - 0.5], [0, s / m, 0.5 * s / m - v * s - 0.5]])
        fg = cv2.warpAffine(img, M, (OW, OH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        a = cv2.warpAffine(alpha, M, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)[..., None]
        Mb = np.float32([[s, 0, (0.5 - PAD - u) * s - 0.5], [0, s, (0.5 - PAD - v) * s - 0.5]])
        bg = cv2.warpAffine(self.bg, Mb, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return bg * (1 - a) + fg * a

PANELS = {}
def panel(k):
    if k not in PANELS: PANELS[k] = Panel(k)
    return PANELS[k]

def corners(cam):
    cx, cy, w = cam; h = w * OH / OW
    return np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])

def blur_window(k, f):
    """motion blur only where the brief asks for it: the zoom-through scene changes (+ the hook's fast zoom);
    regular Ken Burns moves stay crisp so the text in the panels is never smeared"""
    if k == 1 and f <= 9: return True
    return any(c - S.OUT_LEN <= f < c + S.IN_LEN for c in S.CUTS)

def layer(k, f):
    """scene k at frame f with motion blur (subframes over a 0.5-frame shutter) inside the transition windows"""
    if not blur_window(k, f): return panel(k).view(S.cam(k, f)), 1
    ca, cb = S.cam(k, f - 0.25), S.cam(k, f + 0.25)
    d = np.abs(corners(ca) - corners(cb)).max() * OW / ((ca[2] + cb[2]) / 2)      # max corner travel in canvas px
    K = int(min(12, max(1, math.ceil(d / 1.6))))
    if K == 1: return panel(k).view(S.cam(k, f)), 1
    acc = np.zeros((OH, OW, 3), np.float32)
    for j in range(K): acc += panel(k).view(S.cam(k, f - 0.25 + 0.5 * j / (K - 1)))
    return acc / K, K

def render(f):
    out = np.zeros((OH, OW, 3), np.float32); ks = []
    for k, a in S.layers(f):
        img, K = layer(k, f); out += img * a; ks.append(K)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8), max(ks)

def parse(sel):
    if not sel: return list(range(S.N))
    r = []
    for p in sel.split(','):
        if '-' in p: a, b = map(int, p.split('-')); r += list(range(a, b))
        else: r.append(int(p))
    return r

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, 'plate.mkv')
    frames = parse(sys.argv[2] if len(sys.argv) > 2 else ''); png = sys.argv[sys.argv.index('--png') + 1] if '--png' in sys.argv else None
    t0 = time.time(); ks = []
    if png:
        os.makedirs(png, exist_ok=True)
        for f in frames: im, K = render(f); ks.append(K); cv2.imwrite(os.path.join(png, f'{f:04d}.png'), im)
    else:
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{OW}x{OH}', '-r', '30', '-i', '-',
                               '-c:v', 'ffv1', '-level', '3', '-g', '1', '-slices', '4', '-pix_fmt', 'gbrp', out], stdin=subprocess.PIPE)
        for n, f in enumerate(frames):
            im, K = render(f); ks.append(K); ff.stdin.write(im.tobytes())
            if n % 60 == 0: print(f'  frame {f} ({time.time() - t0:.0f}s)', flush=True)
        ff.stdin.close(); ff.wait()
        if ff.returncode: sys.exit('ffmpeg failed')
    print(f'plate: {len(frames)} frames in {time.time() - t0:.1f}s, motion-blurred frames {sum(k > 1 for k in ks)} (max {max(ks)} subframes) -> {png or out}')
