"""Renders the re-edited picture (1080x1920, 30 fps) to lossless FFV1: per-shot grade (white balance for the blue monitor,
soft highlight roll-off, gentle contrast/saturation), single-pass Lanczos crop+upscale from the cleaned 576x1024 source,
frame blending on the 2x tilt, supersampled motion blur on zoom-through cuts, mild unsharp mask, CTA dim/blur, cover poster.
usage: python3 render.py [out.mkv] [frames 0-495 | 10,50] [--png dir]"""
import math, os, subprocess, sys, time
import numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edit as E

ROOT = E.ROOT; OW, OH = 1080, 1920
NAVY = np.array([6, 14, 30], np.float32)
def load_source():
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(ROOT, 'work', 'clean.mkv'), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, E.H, E.W, 3)
SRC = load_source()
POSTER = Image.open(os.path.join(ROOT, 'src', 'cover.png')).convert('RGB')

def grade(arr, gains):
    x = arr.astype(np.float32) / 255 * np.array(gains, np.float32)
    knee = 0.78
    x = np.where(x < knee, x, knee + (1 - knee) * np.tanh((x - knee) / (1 - knee)))
    Y = (0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2])[..., None]
    x = Y + (x - Y) * 1.08
    x = 0.5 + (x - 0.5) * 1.05
    return Image.fromarray(np.clip(x * 255 + 0.5, 0, 255).astype(np.uint8))

def source_image(f):
    s = E.shot_at(f); sf = E.src_frame(f)
    if s.get('blend'):                                   # 2x speed: average the 2 source frames of this output frame
        a = int(math.floor(sf)); fr = SRC[a:a + s['blend']].astype(np.float32).mean(axis=0)
    else:
        fr = SRC[int(round(min(sf, len(SRC) - 1)))]
    return grade(fr, E.grade_at(f))

def crop(img, box): u, v, w, h = box; return np.asarray(img.resize((OW, OH), Image.LANCZOS, box=(u, v, u + w, v + h))).astype(np.float32)
def render(f):
    s = E.shot_at(f)
    if s.get('poster'):
        z = E.poster_zoom(f); w0, h0 = 1672 * OW / OH, 1672.0; w, h = w0 / z, h0 / z
        u, v = (POSTER.width - w) / 2, (POSTER.height - h) / 2
        out = np.asarray(POSTER.resize((OW, OH), Image.LANCZOS, box=(u, v, u + w, v + h))).astype(np.float32); K = 1
    else:
        img = source_image(f)
        ta, tb = max(f - 0.25, s['f0']), min(f + 0.25, s['f1'] - 1e-3)
        ba, bb = E.cam(ta), E.cam(tb); k = OW / ((ba[2] + bb[2]) / 2)
        d = max(abs(ba[0] - bb[0]), abs(ba[1] - bb[1]), abs(ba[0] + ba[2] - bb[0] - bb[2]), abs(ba[1] + ba[3] - bb[1] - bb[3])) * k
        K = int(min(12, max(1, math.ceil(d / 1.5))))
        if K == 1: out = crop(img, E.cam(f))
        else: out = sum(crop(img, E.cam(ta + (tb - ta) * j / (K - 1))) for j in range(K)) / K
        dim, blur = E.cta_fx(f)
        im = Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))
        if blur > 0.05: im = im.filter(ImageFilter.GaussianBlur(blur))
        else: im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=50, threshold=2))
        out = np.asarray(im).astype(np.float32)
        if dim > 0: out = out * (1 - dim) + NAVY * dim
    return np.clip(out + 0.5, 0, 255).astype(np.uint8), K

def parse(sel):
    if not sel: return list(range(E.N))
    r = []
    for p in sel.split(','):
        if '-' in p: a, b = map(int, p.split('-')); r += list(range(a, b))
        else: r.append(int(p))
    return r
if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'plate.mkv')
    frames = parse(sys.argv[2] if len(sys.argv) > 2 else ''); png = sys.argv[sys.argv.index('--png') + 1] if '--png' in sys.argv else None
    t0 = time.time(); ks = []
    if png:
        os.makedirs(png, exist_ok=True)
        for f in frames: im, K = render(f); ks.append(K); Image.fromarray(im).save(os.path.join(png, f'{f:04d}.png'))
    else:
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', '30', '-i', '-',
                               '-c:v', 'ffv1', '-level', '3', '-g', '1', '-slices', '4', '-pix_fmt', 'gbrp', out], stdin=subprocess.PIPE)
        for n, f in enumerate(frames):
            im, K = render(f); ks.append(K); ff.stdin.write(im.tobytes())
            if n % 60 == 0: print(f'  frame {f} ({time.time() - t0:.0f}s)', flush=True)
        ff.stdin.close(); ff.wait()
        if ff.returncode: sys.exit('ffmpeg failed')
    print(f'plate: {len(frames)} frames in {time.time() - t0:.1f}s, zoom-blurred frames {sum(k > 1 for k in ks)} -> {png or out}')
