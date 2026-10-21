"""Renders the v7 background plate (1080x1920 RGB per frame) from crisp sources and pipes it to FFV1 (lossless).
Plate A (S1-S3): screenshot card with typing states, caret, button hover; Plate B (S4-S5): PDF paper.
usage: python3 render_plate.py [out.mkv] [frames e.g. 0-449 or 10,50,200] [--png dir]"""
import json, os, sys, subprocess, time
import numpy as np
from PIL import Image, ImageDraw
V7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, G = os.path.join(V7, 'work'), os.path.join(V7, 'gfx7')
spec = json.load(open(os.path.join(W, 'spec7.json')))
FLD = json.load(open(os.path.join(W, 'fields.json')))
CARD, PAPER = spec['CARD'], spec['PAPER']
RES_UP = getattr(Image, os.environ.get('RES_UP', 'LANCZOS'))       # resampler when the source is enlarged
RES_DN = Image.LANCZOS                                             # resampler when reduced

def rgb(p): return Image.open(os.path.join(W, p)).convert('RGB')
src = {'s5': rgb('s5r.png'), 's4': rgb('s4r.png')}
blank = {'s5': rgb('s5_blank.png'), 's4': rgb('s4_blank.png')}
doc = rgb('docr.png')
bgs = {k: np.asarray(rgb(f'bg_{k}.png')) for k in ('s4', 's5')}
def rgba(p): return np.asarray(Image.open(os.path.join(G, p)).convert('RGBA')).astype(np.float32) / 255.0
def lum(p): return np.asarray(Image.open(os.path.join(G, p)).convert('L')).astype(np.float32)[..., None] / 255.0
L = {k: rgba(f'c7_{k}.png') for k in ('bgfx', 'ashadow', 'aborder', 'pshadow', 'pborder')}
M = {'a': lum('c7_amask.png'), 'p': lum('c7_pmask.png')}

def over(dst, layer, dy=0):
    a = layer[..., 3:4]; c = layer[..., :3] * 255.0
    if dy:
        a = np.roll(a, dy, axis=0); c = np.roll(c, dy, axis=0)
        a[:dy] = 0
    dst *= (1 - a); dst += c * a
    return dst

def bg_frame(key, z):
    b = bgs[key]; H, Wd = b.shape[:2]
    cw, ch = Wd / z, H / z; x0, y0 = (Wd - cw) / 2, (H - ch) / 2
    im = Image.fromarray(b).resize((1080, 1920), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    return np.asarray(im).astype(np.float32)

def keys_done(keys, f): return sum(1 for k in keys if k <= f)
def caret_on(f, t_start, last_key):
    idle = f - max(t_start, last_key if last_key is not None else t_start)
    return idle < 10 or ((idle - 10) // 16) % 2 == 1

def state_image(fr):
    f, key = fr['f'], fr['img']; T = spec['typing']
    if key == 's5':
        k = keys_done(T['to']['keys'], f)
        im = src['s5'].copy() if k == len(T['to']['keys']) else blank['s5'].copy()
        typed = [('to', k, f >= T['to']['click'])]
    else:
        ki, kp = keys_done(T['item']['keys'], f), keys_done(T['price']['keys'], f)
        totals = f >= spec['totalsAt']
        im = src['s4'].copy() if (ki == len(T['item']['keys']) and kp == len(T['price']['keys']) and totals) else blank['s4'].copy()
        if im is not None and not (ki == len(T['item']['keys']) and kp == len(T['price']['keys']) and totals):
            if totals:   # paste the auto-calculated totals from the original
                for t in FLD['totals']:
                    x0, y0, x1, y1 = t['fill']; im.paste(src['s4'].crop((x0, y0, x1, y1)), (x0, y0))
        typed = [('item', ki, T['item']['click'] <= f < T['price']['click']), ('price', kp, T['price']['click'] <= f < spec['clickF'])]
    d = ImageDraw.Draw(im)
    for name, k, active in typed:
        fd = FLD['fields'][name]; x0, y0, x1, y1 = fd['text']; Wt = x1 - x0; n = len(fd['str'])
        c = fd['cuts'][k - 1] if k > 0 else 0
        if 0 < k < n:   # partial text: strip of the final rendering, re-positioned like a live input (centered / right aligned)
            strip = src[fd['img']].crop((x0, y0, x0 + c, y1))
            off = (Wt - c) // 2 if fd['align'] == 'center' else (Wt - c)
            im.paste(strip, (x0 + off, y0))
        if active:
            keys = T[name]['keys']; last = max([kk for kk in keys if kk <= f], default=None)
            if caret_on(f, T[name]['click'], last):
                if fd['align'] == 'center':
                    cx = x0 + (Wt - c) // 2 + c if k < n else x1
                    if k == 0: cx = x0 + Wt // 2
                else: cx = x1 + 1
                d.line([(cx, fd['caret'][0]), (cx, fd['caret'][1])], fill=(30, 41, 59), width=1)
    if key == 's4' and (fr.get('hover') or fr.get('pressed')):   # PDF button hover / pressed state
        k = 0.80 if fr.get('pressed') else 0.88
        box = (1224, 224, 1288, 260)
        reg = np.asarray(im.crop(box)).astype(np.float32)
        m = Image.new('L', (box[2] - box[0], box[3] - box[1]), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, box[2] - box[0] - 1, box[3] - box[1] - 1), radius=6, fill=255)
        mm = np.asarray(m).astype(np.float32)[..., None] / 255
        im.paste(Image.fromarray(np.clip(reg * (1 - mm) + reg * k * mm, 0, 255).astype(np.uint8)), box[:2])
    return im

def crop(im, cam, w, h):
    box = (cam['u'], cam['v'], cam['u'] + cam['w'], cam['v'] + cam['w'] * h / w)
    res = RES_UP if cam['w'] < w else RES_DN
    return np.asarray(im.resize((w, h), res, box=box)).astype(np.float32)

def render(fr):
    out = bg_frame(fr['bg'], fr['bgZoom'])
    over(out, L['bgfx'])
    if fr['plate'] == 'A':
        over(out, L['ashadow'])
        card = crop(state_image(fr), fr['cam'], CARD['w'], CARD['h'])
        x, y, m = CARD['x'], CARD['y'], M['a']
        out[y:y + CARD['h'], x:x + CARD['w']] = card * m + out[y:y + CARD['h'], x:x + CARD['w']] * (1 - m)
        over(out, L['aborder'])
    else:
        dy = fr['dy']
        over(out, L['pshadow'], dy)
        paper = crop(doc, fr['cam'], PAPER['w'], PAPER['h'])
        x, y, m = PAPER['x'], PAPER['y'] + dy, M['p']
        out[y:y + PAPER['h'], x:x + PAPER['w']] = paper * m + out[y:y + PAPER['h'], x:x + PAPER['w']] * (1 - m)
        over(out, L['pborder'], dy)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)

def parse_frames(s, N):
    if not s: return list(range(N))
    r = []
    for p in s.split(','):
        if '-' in p: a, b = map(int, p.split('-')); r += list(range(a, b))
        else: r.append(int(p))
    return r

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(W, 'plate7.mkv')
    frames = parse_frames(sys.argv[2] if len(sys.argv) > 2 else '', spec['N'])
    pngdir = sys.argv[sys.argv.index('--png') + 1] if '--png' in sys.argv else None
    t0 = time.time()
    if pngdir:
        os.makedirs(pngdir, exist_ok=True)
        for f in frames: Image.fromarray(render(spec['frames'][f])).save(os.path.join(pngdir, f'{f:04d}.png'))
    else:
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1080x1920', '-r', '30', '-i', '-',
                               '-c:v', 'ffv1', '-level', '3', '-g', '1', '-slices', '4', '-pix_fmt', 'gbrp', out], stdin=subprocess.PIPE)
        for i, f in enumerate(frames):
            ff.stdin.write(render(spec['frames'][f]).tobytes())
            if i % 50 == 0: print(f'  frame {f} ({time.time() - t0:.1f}s)', flush=True)
        ff.stdin.close(); ff.wait()
        if ff.returncode: sys.exit('ffmpeg failed')
    print(f'plate: {len(frames)} frames in {time.time() - t0:.1f}s -> {pngdir or out}')
