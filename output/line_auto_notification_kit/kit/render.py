"""Picture for the SmartFlow LINE clip -> work/video.mp4 (1080x1920, 30 fps, no audio).
Per output frame: the source frame nearest in time (the 59.94 fps recording, real time), a uniform zoom whose centre
is locked to tracked content (the chat while the hand holds the phone, the new LINE card from its arrival on, a fixed
push-in on her shots), a light unsharp mask, the green glow + ping around the card (drawn only outside the card, so
nothing on the LINE screen changes), then the text on frosted-glass panels with short fade/slide-up reveals.
Fast zoom moves get a 3-sample shutter blur.  usage: render.py [out.mp4] [--frames a-b|i,j] [--png dir]"""
import json, os, subprocess, sys, time
import numpy as np, cv2
from scipy.ndimage import gaussian_filter1d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec as SP

OW, OH, FPS = SP.OW, SP.OH, SP.FPS
W = SP.W; SRC = os.path.join(SP.ROOT, 'src', 'source.mp4'); PTS = SP.PTS
cv2.setNumThreads(4)
GREEN = np.array([46, 224, 122], np.float32)

# ---------------- easing
def ease(kind, p):
    p = float(np.clip(p, 0, 1))
    if kind == 'out': return 1 - (1 - p) ** 3
    if kind == 'in': return p ** 3
    if kind == 'inout': return 0.5 - 0.5 * np.cos(np.pi * p)
    if kind == 'inout3': return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2
    return p

# ---------------- camera
T = json.load(open(os.path.join(W, 'track.json')))
def _path(d, ks, sigma_frames):
    a = np.array([d[str(k)] for k in ks], np.float64)
    return gaussian_filter1d(a, sigma_frames, axis=0, mode='nearest')
CHAT_K = list(range(0, 456)); CHAT = _path(T['chat'], CHAT_K, 18)                    # ~0.3 s smoothing
CARD_K = list(range(456, 621)); CARD = _path(T['card'], CARD_K, 3).reshape(-1, 4, 2)  # corners, ~0.05 s smoothing
CARD_C = gaussian_filter1d(CARD.mean(1), 9, axis=0, mode='nearest')                  # centre, ~0.15 s smoothing
def at_time(path, ks, t):
    tk = PTS[ks]; i = np.clip(np.searchsorted(tk, t), 1, len(ks) - 1); w = np.clip((t - tk[i - 1]) / (tk[i] - tk[i - 1]), 0, 1)
    return path[i - 1] * (1 - w) + path[i] * w

def zoom_at(t):
    K = SP.ZOOM
    if t <= K[0][0]: return K[0][1]
    for (t0, z0, _), (t1, z1, e) in zip(K, K[1:]):
        if t <= t1: return z0 + (z1 - z0) * ease(e, (t - t0) / max(1e-6, t1 - t0))
    return K[-1][1]

def centre_at(t):
    """(source point, output anchor) of the camera"""
    build = np.array(SP.DRIFT_BUILD) * ease('inout', (t - 0.35) / (7.55 - 0.35))
    chat = (at_time(CHAT, CHAT_K, min(t, 7.55)) + build, np.array(SP.CHAT_ANCHOR, float))
    if t < SP.ARRIVE: return chat
    card = (at_time(CARD_C, CARD_K, min(t, PTS[620])), np.array(SP.CARD_ANCHOR, float))
    w = ease('inout3', (t - SP.ARRIVE) / 0.53)
    c = (chat[0] * (1 - w) + card[0] * w, chat[1] * (1 - w) + card[1] * w)
    if t < 9.95: return c
    w = ease('inout3', (t - 9.95) / 0.60)
    return (c[0] * (1 - w) + np.array(SP.FIXED_C) * w, c[1] * (1 - w) + np.array([OW / 2, OH / 2]) * w)

def matrix(t):
    z = zoom_at(t); c, a = centre_at(t)
    x0 = c[0] - a[0] / z; y0 = c[1] - a[1] / z                     # source window top-left; keep it inside the frame
    x0 = float(np.clip(x0, 0, OW - OW / z)); y0 = float(np.clip(y0, 0, OH - OH / z))
    return np.float32([[z, 0, -x0 * z], [0, z, -y0 * z]])

# ---------------- glow around the LINE card
def card_quad(t):
    if not (PTS[456] - 1e-3 <= t <= PTS[620]): return None
    return at_time(CARD, CARD_K, t)

def draw_glow(img, quad_src, M, t):
    a_in = ease('out', (t - SP.ARRIVE) / 0.25); a_out = 1 - ease('inout', (t - 9.55) / 0.35); s = a_in * a_out
    if s <= 0.01: return
    q = (M[:, :2] @ quad_src.T).T + M[:, 2]; c = q.mean(0)
    grow = lambda d: q + (q - c) / np.linalg.norm(q - c, axis=1, keepdims=True) * d
    x0, y0 = np.maximum(0, q.min(0) - 120).astype(int); x1, y1 = np.minimum([OW, OH], q.max(0) + 120).astype(int)
    reg = img[y0:y1, x0:x1]; off = np.array([x0, y0])
    inside = np.zeros(reg.shape[:2], np.float32)
    cv2.fillConvexPoly(inside, np.round(grow(2) - off).astype(np.int32), 1.0, cv2.LINE_AA)
    outside = 1 - cv2.GaussianBlur(inside, (0, 0), 1.5)                  # never paint over the card itself
    soft = np.zeros_like(inside); cv2.polylines(soft, [np.round(grow(13) - off).astype(np.int32)], True, 1.0, 30, cv2.LINE_AA)
    soft = cv2.GaussianBlur(soft, (0, 0), 15) * 0.85
    line = np.zeros_like(inside); cv2.polylines(line, [np.round(grow(10) - off).astype(np.int32)], True, 1.0, 4, cv2.LINE_AA)
    p = (t - SP.ARRIVE) / 0.75                                            # one "ping" ring going out on arrival
    if 0 <= p <= 1:
        cv2.polylines(line, [np.round(grow(12 + 46 * ease('out', p)) - off).astype(np.int32)], True, 0.7 * (1 - p), 4, cv2.LINE_AA)
    al = (np.maximum(soft, line * 0.95) * outside * s)[..., None]
    reg[:] = reg * (1 - al) + GREEN * al

# ---------------- text on frosted-glass panels
ITEMS = SP.ITEMS; META = json.load(open(os.path.join(W, 'ov', 'meta.json')))
PNG = {}
def png(i):
    if i not in PNG:
        a = cv2.imread(os.path.join(W, 'ov', i + '.png'), cv2.IMREAD_UNCHANGED)
        PNG[i] = (a[..., [2, 1, 0]].astype(np.float32), a[..., 3:4].astype(np.float32) / 255.0)
    return PNG[i]

def layout():
    groups = {}
    for i, g, a, b, *_ in ITEMS: groups.setdefault(g, []).append((i, a, b))
    out = {}
    for g, its in groups.items():
        anchor, cx, _ = SP.GROUPS[g]
        ws = [META[i]['box_w'] for i, *_ in its]; hs = [META[i]['box_h'] for i, *_ in its]
        pw = max(ws) + 2 * SP.PAD_X; ph = sum(hs) + SP.GAP * (len(hs) - 1) + 2 * SP.PAD_Y
        y0 = SP.TOP_Y if anchor == 'top' else SP.BOTTOM_Y - ph; x0 = cx - pw / 2
        boxes, y = [], y0 + SP.PAD_Y
        for (i, a, b), w_, h_ in zip(its, ws, hs): boxes.append((i, a, b, cx - w_ / 2, y, w_, h_)); y += h_ + SP.GAP
        out[g] = dict(rect=(x0, y0, x0 + pw, y0 + ph), t_in=min(a for _, a, _ in its), t_out=max(b for _, _, b in its), boxes=boxes)
    return out
LAYOUT = layout()

def rounded_mask(h, w, x0, y0, x1, y1, r):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    qx, qy = np.abs(xx - cx) - hw, np.abs(yy - cy) - hh
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
    return np.clip(0.5 - d, 0, 1), d

def glass(img, rect, a, dy, r=34):
    x0, y0, x1, y1 = rect; y0 += dy; y1 += dy; P = 46
    X0, Y0, X1, Y1 = int(max(0, x0 - P)), int(max(0, y0 - P)), int(min(OW, x1 + P)), int(min(OH, y1 + P + 16))
    reg = img[Y0:Y1, X0:X1]; h, w = reg.shape[:2]
    m, d = rounded_mask(h, w, x0 - X0, y0 - Y0, x1 - X0, y1 - Y0, r)
    sh = cv2.GaussianBlur(np.roll(m, 12, axis=0), (0, 0), 14) * 0.38 * a          # soft drop shadow
    reg *= (1 - sh)[..., None]
    frost = cv2.GaussianBlur(reg, (0, 0), 20) * 0.46 + np.array([12, 18, 32], np.float32) * 0.54
    shade = 1 + 0.06 * np.clip(1 - (np.mgrid[0:h, 0:w][0] - (y0 - Y0)) / 60.0, 0, 1)  # faint light along the top edge
    mm = (m * a)[..., None]; reg[:] = reg * (1 - mm) + frost * shade[..., None] * mm
    edge = (np.clip(1.6 - np.abs(d + 0.8), 0, 1) * 0.22 * a)[..., None]                # hairline border
    reg[:] = reg * (1 - edge) + 255 * edge

def blend(img, rgb, al, x, y, clip=None):
    h, w = al.shape[:2]; x, y = int(round(x)), int(round(y))
    cx0, cy0, cx1, cy1 = clip if clip else (0, 0, OW, OH)
    x0, y0 = max(x, cx0, 0), max(y, cy0, 0); x1, y1 = min(x + w, cx1, OW), min(y + h, cy1, OH)
    if x1 <= x0 or y1 <= y0: return
    a = al[y0 - y:y1 - y, x0 - x:x1 - x]; img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + rgb[y0 - y:y1 - y, x0 - x:x1 - x] * a

def draw_text(img, t):
    for g, L in LAYOUT.items():
        if not (L['t_in'] <= t <= L['t_out'] + 0.01): continue
        a_in = ease('out', (t - L['t_in']) / 0.18); a_out = 1 - ease('in', (t - (L['t_out'] - 0.16)) / 0.16)
        a = a_in * a_out; dy = 14 * (1 - a_in) - 10 * (1 - a_out)
        if a <= 0.01: continue
        glass(img, L['rect'], a, dy)
        for i, ti, to, bx, by, bw, bh in L['boxes']:
            if t < ti: continue
            ai = ease('out', (t - ti) / 0.24); M_ = META[i]['margin']
            rgb, al = png(i); yy = by + dy + 20 * (1 - ai)                         # slide up inside its own line
            clip = (int(bx - M_), int(by + dy - 8), int(bx + bw + M_), int(by + dy + bh + 10))
            blend(img, rgb, al * (ai * a_out), bx - M_, yy - M_, clip)

# ---------------- source frames
class Reader:
    def __init__(self):
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', SRC, '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                  stdout=subprocess.PIPE, bufsize=OW * OH * 3 * 4)
        self.k = -1; self.cur = None
    def get(self, k):
        while self.k < k:
            b = self.p.stdout.read(OW * OH * 3)
            if len(b) < OW * OH * 3: break
            self.cur = np.frombuffer(b, np.uint8).reshape(OH, OW, 3); self.k += 1
        return self.cur

def frame(n, rd):
    t = n / FPS; k = int(np.argmin(np.abs(PTS - t))); src = rd.get(k)
    dz = abs(zoom_at(t + 1 / 120) - zoom_at(t - 1 / 120)) * 60                 # zoom speed, per second
    ts = (t - 1 / 120, t, t + 1 / 120) if dz > 0.35 else (t,)
    acc = None
    for s in ts:
        w = cv2.warpAffine(src, matrix(s), (OW, OH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        acc = w if acc is None else acc + w
    img = acc / len(ts); z = zoom_at(t)
    s_ = 0.22 + 0.25 * np.clip((z - 1) / 0.6, 0, 1)
    img = cv2.addWeighted(img, 1 + s_, cv2.GaussianBlur(img, (0, 0), 1.0), -s_, 0)
    q = card_quad(t)
    if q is not None: draw_glow(img, q, np.vstack([matrix(t), [0, 0, 1]])[:2].astype(np.float64), t)
    draw_text(img, t)
    return np.clip(img, 0, 255).astype(np.uint8)

def parse(sel, n):
    if not sel: return list(range(n))
    out = []
    for p in sel.split(','):
        if '-' in p: a, b = map(int, p.split('-')); out += list(range(a, b))
        else: out.append(int(p))
    return sorted(out)

if __name__ == '__main__':
    args = sys.argv[1:]; out = args[0] if args and not args[0].startswith('--') else os.path.join(W, 'video.mp4')
    frames = parse(args[args.index('--frames') + 1] if '--frames' in args else '', SP.N)
    pngdir = args[args.index('--png') + 1] if '--png' in args else None
    rd = Reader(); t0 = time.time()
    if pngdir:
        os.makedirs(pngdir, exist_ok=True)
        for n in frames: cv2.imwrite(os.path.join(pngdir, f'{n:04d}.png'), frame(n, rd)[..., ::-1])
    else:
        enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                                '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level:v', '4.1',
                                '-g', '60', '-bf', '2', '-tune', 'film', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                                '-color_range', 'tv', out], stdin=subprocess.PIPE)
        for n in frames:
            enc.stdin.write(frame(n, rd).tobytes())
            if n % 90 == 0: print(f'  frame {n}/{SP.N} ({time.time() - t0:.0f}s)', flush=True)
        enc.stdin.close(); enc.wait()
    print(f'{len(frames)} frames in {time.time() - t0:.0f}s -> {pngdir or out}')
