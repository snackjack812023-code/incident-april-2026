"""Renders the picture (1080x1920, 30 fps) from the 4x super-resolved storyboard images -> lossless FFV1.
Per frame and scene layer: camera (spec.cam) -> affine warp (Lanczos) from a mip level picked so the source is only ever
mildly reduced (no aliasing on zoomed-out frames, no upscaling blur on zoomed-in frames). Where the camera shows area outside
the image, an extension of the same image is used: 'seamless' (mirrored, lightly blurred: continues the bokeh background)
or 'card' (soft-focus backdrop with a shadow: end-card look). Motion blur (0.5-frame shutter, up to 12 sub-frames) only on the
zoom-through transitions and the opening crash zoom, so text is never smeared during the reading holds.
usage: python3 render.py [out.mkv] [frames 0-600 | 10,50] [--png dir]"""
import math, os, subprocess, sys, time
from collections import OrderedDict
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); WORK = os.path.join(ROOT, 'work')
OW, OH, PAD = S.OW, S.OH, 560
LEVELS = (0.95, 1.27, 1.69, 2.25, 3.0)
cv2.setNumThreads(4)

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

class Image:
    def __init__(self, k):
        sr = cv2.imread(os.path.join(WORK, f'sr_s{k}.png'), cv2.IMREAD_COLOR)            # BGR, 4x
        clean = cv2.imread(os.path.join(WORK, f'clean_s{k}.png'), cv2.IMREAD_COLOR)      # BGR, 1x
        self.h1, self.w1 = clean.shape[:2]
        self.lv = {L: cv2.resize(sr, (round(self.w1 * L), round(self.h1 * L)), interpolation=cv2.INTER_AREA) for L in LEVELS}
        del sr
        style = S.EXT_STYLE.get(k, 'seamless')
        x = cv2.copyMakeBorder(clean, 0, 0, PAD, PAD, cv2.BORDER_REFLECT_101)
        top = cv2.copyMakeBorder(x, PAD, 0, 0, 0, cv2.BORDER_REFLECT_101)[:PAD]
        bot = np.repeat(x[-1:], PAD, axis=0)                     # bottom: replicate (no mirrored logos / captions)
        big = np.concatenate([top, x, bot]).astype(np.float32)
        yy, xx = np.mgrid[0:big.shape[0], 0:big.shape[1]].astype(np.float32)
        dx = np.maximum(np.maximum(PAD - xx, xx - (PAD + self.w1 - 1)), 0); dy = np.maximum(np.maximum(PAD - yy, yy - (PAD + self.h1 - 1)), 0)
        d = np.sqrt(dx * dx + dy * dy)[..., None]
        if style == 'seamless':
            b1, b2, b3 = (cv2.GaussianBlur(big, (0, 0), s) for s in (2.5, 8, 22))
            t1, t2 = smoothstep(0, 40, d), smoothstep(60, 200, d)
            ext = b1 * (1 - t1) + b2 * t1; ext = ext * (1 - t2) + b3 * t2
            ext = ext * (1 - 0.22 * t2) + np.array([40, 16, 8], np.float32) * 0.10 * t2
        else:   # 'card': soft-focus backdrop, darker, with a contact shadow along the image edge
            b2, b3 = cv2.GaussianBlur(big, (0, 0), 16), cv2.GaussianBlur(big, (0, 0), 34)
            t = smoothstep(0, 140, d); ext = b2 * (1 - t) + b3 * t
            shadow = 0.42 * np.exp(-d / 46.0)
            ext = ext * (1 - 0.40) * (1 - shadow) + np.array([46, 18, 8], np.float32) * 0.16
        self.ext = ext.astype(np.float32); self.style = style

    def view(self, cam):
        cx, cy, w = cam; h = w * OH / OW; s = OW / w; u, v = cx - w / 2, cy - h / 2
        L = next((L for L in LEVELS if L >= s - 1e-6), LEVELS[-1])
        M = np.float32([[s / L, 0, 0.5 * s / L - u * s - 0.5], [0, s / L, 0.5 * s / L - v * s - 0.5]])
        fg = cv2.warpAffine(self.lv[L], M, (OW, OH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT_101).astype(np.float32)
        inside = u >= -1e-3 and v >= -1e-3 and u + w <= self.w1 + 1e-3 and v + h <= self.h1 + 1e-3
        if inside: return fg
        Mb = np.float32([[s, 0, (0.5 - PAD - u) * s - 0.5], [0, s, (0.5 - PAD - v) * s - 0.5]])
        bg = cv2.warpAffine(self.ext, Mb, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        # coverage of the real image per canvas pixel (feathered edge)
        X = (np.arange(OW, dtype=np.float32) + 0.5) / s + u; Y = (np.arange(OH, dtype=np.float32) + 0.5) / s + v
        fe = 1.6 / s if self.style == 'seamless' else 0.9 / s
        ax = np.clip(np.minimum(X - 0, self.w1 - X) / fe + 0.5, 0, 1); ay = np.clip(np.minimum(Y - 0, self.h1 - Y) / fe + 0.5, 0, 1)
        a = (ay[:, None] * ax[None, :])[..., None]
        return bg * (1 - a) + fg * a

CACHE = OrderedDict()
def image(k):
    if k in CACHE: CACHE.move_to_end(k); return CACHE[k]
    CACHE[k] = Image(k)
    while len(CACHE) > 3: CACHE.popitem(last=False)
    return CACHE[k]

def corners(c):
    cx, cy, w = c; h = w * OH / OW; return np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])

def blur_window(k, f):
    if k == 1 and f <= 9: return True                                   # opening crash zoom
    return any(c - S.OUT_LEN <= f < c + S.IN_LEN for c in S.CUTS)      # zoom-through transitions

def layer(k, f):
    if not blur_window(k, f): return image(k).view(S.cam(k, f)), 1
    ca, cb = S.cam(k, f - 0.25), S.cam(k, f + 0.25)
    d = np.abs(corners(ca) - corners(cb)).max() * OW / ((ca[2] + cb[2]) / 2)
    K = int(min(12, max(1, math.ceil(d / 1.6))))
    if K == 1: return image(k).view(S.cam(k, f)), 1
    acc = np.zeros((OH, OW, 3), np.float32)
    for j in range(K): acc += image(k).view(S.cam(k, f - 0.25 + 0.5 * j / (K - 1)))
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
