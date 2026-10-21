"""Renders the background plate (1080x1920 RGB per frame) for the Factory Tracking promo:
blurred navy-tinted screenshot background + floating card with sub-pixel Lanczos camera crops of the real screenshots,
temporal-supersampled motion blur on fast moves, procedural shadow / border / glow. Pipes to FFV1 (lossless).
usage: python3 render_plate.py [out.mkv] [frames: 0-630 | 10,50] [--png dir]"""
import math, os, subprocess, sys, time
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = {k: Image.open(os.path.join(ROOT, 'src', k + '.png')).convert('RGB') for k in {s[1] for s in S.SCENES}}
W, H = 1080, 1920
NAVY = np.array([8, 16, 44], np.float32)
CX0, CY0 = S.CARD['x'] + S.CARD['w'] / 2, S.CARD['y'] + S.CARD['h'] / 2

# ---------------- background: slightly blurred screenshot (same page), navy tint for text contrast
def tint_alpha():
    ys = np.array([0, 520, 960, 1400, 1920], np.float32); a = np.array([0.86, 0.70, 0.60, 0.72, 0.90], np.float32)
    return np.interp(np.arange(H, dtype=np.float32), ys, a)[:, None, None]
TA = tint_alpha()
def make_bg(scene_idx):
    key, src, f0, f1 = S.SCENES[scene_idx]
    cx = float(np.mean([S.cam(t)[0] + S.cam(t)[2] / 2 for t in range(f0, f1)]))
    ah = S.APP[3] - S.APP[1]; aw = ah * W / H
    x0 = min(max(cx - aw / 2, 0), 1920 - aw)
    im = SRC[src].resize((W // 2, H // 2), Image.BOX, box=(x0, S.APP[1], x0 + aw, S.APP[3]))
    im = im.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BICUBIC)
    a = np.asarray(im).astype(np.float32) * np.array([0.86, 0.95, 1.12], np.float32)
    return np.clip(a * (1 - TA) + NAVY * TA, 0, 255)
BG = {}
def bg_scene(i):
    if i not in BG: BG[i] = make_bg(i)
    return BG[i]
def bg_zoomed(j, z):
    b = bg_scene(j); cw, ch = W / z, H / z
    return np.asarray(Image.fromarray(b.astype(np.uint8)).resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))).astype(np.float32)
def bg_frame(t):
    i = S.scene_at(t); src, z, mix = S.bg_at(t)
    out = bg_zoomed(i, z)
    if mix:                                   # 4-frame crossfade centred on the cut
        cut = min(S.CUTS, key=lambda c: abs(c - t)); prev_i, next_i = S.scene_at(cut - 1), S.scene_at(cut); m = mix[2]
        if i == prev_i: out = out * (1 - m) + bg_zoomed(next_i, 1.0) * m
        else: out = bg_zoomed(prev_i, 1.05) * (1 - m) + out * m
    return out

# ---------------- ambient glow (static)
def glow_layer():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    def radial(cx, cy, r, col, a):
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        al = np.clip(1 - d, 0, 1) ** 2 * a
        return np.concatenate([np.broadcast_to(np.array(col, np.float32), (H, W, 3)), al[..., None]], axis=2)
    return [radial(520, 980, 950, (37, 99, 235), 0.38), radial(930, 230, 650, (34, 211, 238), 0.15)]
GLOWS = glow_layer()
def over(dst, rgba):
    a = rgba[..., 3:4]; dst *= (1 - a); dst += rgba[..., :3] * a; return dst

# ---------------- card chrome (procedural, cached per integer card size)
def rrect_mask(w, h, r, ss=4):
    im = Image.new('L', (w * ss, h * ss), 0); ImageDraw.Draw(im).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius=r * ss, fill=255)
    return im.resize((w, h), Image.BOX)
@lru_cache(maxsize=64)
def chrome(w, h):
    r = max(6, round(S.CARD['r'] * w / S.CARD['w']))
    m = rrect_mask(w, h, r); M = 160                        # margin for shadow / glow
    big = Image.new('L', (w + 2 * M, h + 2 * M), 0)
    def blurred(dx, dy, sig):
        c = big.copy(); c.paste(m, (M + dx, M + dy)); return np.asarray(c.filter(ImageFilter.GaussianBlur(sig))).astype(np.float32) / 255
    a1, a2 = blurred(0, 40, 36) * 0.58, blurred(0, 10, 10) * 0.36
    shadow = 1 - (1 - a1) * (1 - a2)
    full = big.copy(); full.paste(m, (M, M)); fm = np.asarray(full).astype(np.float32) / 255
    ring = np.asarray(full.filter(ImageFilter.MaxFilter(5))).astype(np.float32) / 255 - fm
    glow = np.asarray(Image.fromarray((np.clip(ring, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(16))).astype(np.float32) / 255
    glow = np.clip(glow * 4.0, 0, 1) * 0.30 * (1 - fm)
    inner = fm - np.asarray(full.filter(ImageFilter.MinFilter(3))).astype(np.float32) / 255
    return {'mask': np.asarray(m).astype(np.float32)[..., None] / 255, 'M': M,
            'shadow': (shadow * (1 - fm))[..., None], 'glow': glow[..., None], 'inner': np.clip(inner, 0, 1)[..., None] * 0.30}

# ---------------- card content with motion blur
def crop_render(src, t, w, h):
    u, v, cw = S.cam(t); ch = cw * h / w
    res = Image.LANCZOS
    return np.asarray(SRC[src].resize((w, h), res, box=(u, v, u + cw, v + ch))).astype(np.float32)
def card_content(f, w, h):
    i = S.scene_at(f); f0, f1 = S.SCENES[i][2], S.SCENES[i][3]; src = S.SCENES[i][1]
    ta, tb = max(f - 0.25, f0), min(f + 0.25, f1 - 1e-3)
    ra, rb = S.cam(ta), S.cam(tb); k = w / ((ra[2] + rb[2]) / 2)
    d = max(abs(ra[0] - rb[0]), abs(ra[1] - rb[1]), abs(ra[0] + ra[2] - rb[0] - rb[2]), abs(ra[1] + ra[2] / S.AR - rb[1] - rb[2] / S.AR)) * k
    K = int(min(16, max(1, math.ceil(d / 1.2))))
    if K == 1: return crop_render(src, f, w, h), 1
    acc = np.zeros((h, w, 3), np.float32)
    for j in range(K): acc += crop_render(src, ta + (tb - ta) * j / (K - 1), w, h)
    return acc / K, K

def render(f):
    out = bg_frame(f)
    for g in GLOWS: over(out, g)
    s, dim, blur = S.card_tf(f)
    w, h = round(S.CARD['w'] * s), round(S.CARD['h'] * s)
    x, y = round(CX0 - w / 2), round(CY0 - h / 2)
    c = chrome(w, h); M = c['M']
    # shadow + glow (outside the card)
    y0, y1, x0, x1 = y - M, y + h + M, x - M, x + w + M
    sy0, sx0 = max(0, -y0), max(0, -x0); cy0, cx0 = max(0, y0), max(0, x0); cy1, cx1 = min(H, y1), min(W, x1)
    reg = out[cy0:cy1, cx0:cx1]
    sh = c['shadow'][sy0:sy0 + cy1 - cy0, sx0:sx0 + cx1 - cx0]; gl = c['glow'][sy0:sy0 + cy1 - cy0, sx0:sx0 + cx1 - cx0]
    reg *= (1 - sh); reg += np.array([0, 5, 28], np.float32) * sh
    reg *= (1 - gl); reg += np.array([34, 211, 238], np.float32) * gl
    content, K = card_content(f, w, h)
    if blur > 0.05: content = np.asarray(Image.fromarray(np.clip(content, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))).astype(np.float32)
    if dim > 0: content = content * (1 - dim) + NAVY * dim
    m = c['mask']; dst = out[y:y + h, x:x + w]
    dst *= (1 - m); dst += content * m
    inner = c['inner'][M:M + h, M:M + w]; dst *= (1 - inner); dst += 255 * inner
    return np.clip(out + 0.5, 0, 255).astype(np.uint8), K

def parse_frames(s):
    if not s: return list(range(S.N))
    r = []
    for p in s.split(','):
        if '-' in p: a, b = map(int, p.split('-')); r += list(range(a, b))
        else: r.append(int(p))
    return r

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'plate.mkv')
    frames = parse_frames(sys.argv[2] if len(sys.argv) > 2 else '')
    pngdir = sys.argv[sys.argv.index('--png') + 1] if '--png' in sys.argv else None
    t0 = time.time(); ks = []
    if pngdir:
        os.makedirs(pngdir, exist_ok=True)
        for f in frames:
            im, K = render(f); ks.append(K); Image.fromarray(im).save(os.path.join(pngdir, f'{f:04d}.png'))
    else:
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '30', '-i', '-',
                               '-c:v', 'ffv1', '-level', '3', '-g', '1', '-slices', '4', '-pix_fmt', 'gbrp', out], stdin=subprocess.PIPE)
        for n, f in enumerate(frames):
            im, K = render(f); ks.append(K); ff.stdin.write(im.tobytes())
            if n % 60 == 0: print(f'  frame {f} ({time.time() - t0:.0f}s)', flush=True)
        ff.stdin.close(); ff.wait()
        if ff.returncode: sys.exit('ffmpeg failed')
    print(f'plate: {len(frames)} frames in {time.time() - t0:.1f}s, motion-blurred frames {sum(k > 1 for k in ks)} (max {max(ks)} subframes) -> {pngdir or out}')
