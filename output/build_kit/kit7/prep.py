"""v7 source prep: privacy redaction (tax ID, bank account), blank form states, blurred backgrounds.
Inputs (src/): s4.png s5.png (URL already blurred), doc_top.png (PDF page image, top part)
Outputs (work/): s4r.png s5r.png docr.png  s4_blank.png s5_blank.png  bg_s4.png bg_s5.png  fields.json"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
V7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, W = os.path.join(V7, 'src'), os.path.join(V7, 'work')
os.makedirs(W, exist_ok=True)

def make_sources():
    """stage 0: user inputs -> src/s4.png + src/s5.png (browser URL blurred) and src/doc_top.png (PDF page image on white, top
    1707 px only: the bank details further down the page never enter the pipeline)"""
    os.makedirs(SRC, exist_ok=True)
    for env, name in (('SHOT_ITEMS', 's4'), ('SHOT_HEADER', 's5')):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.environ[env], '-filter_complex',
                        '[0]format=rgb24,split[a][b];[b]crop=830:34:145:46,gblur=sigma=6:steps=3[bl];[a][bl]overlay=145:46,format=rgb24',
                        '-frames:v', '1', os.path.join(SRC, name + '.png')], check=True)
    tmp = os.path.join(SRC, 'pdfimg')
    subprocess.run(['pdfimages', '-png', '-f', '1', '-l', '1', os.environ['PDF'], tmp], check=True)
    rgb = np.asarray(Image.open(tmp + '-000.png').convert('RGB')).astype(float)
    a = np.asarray(Image.open(tmp + '-001.png').convert('L')).astype(float)[..., None] / 255   # soft mask
    doc = np.clip(rgb * a + 255 * (1 - a) + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(doc[:1707]).save(os.path.join(SRC, 'doc_top.png'))
if os.environ.get('SHOT_ITEMS'): make_sources()

def redact(img, box, k, feather=2):
    """privacy smudge: heavy downsample (k px cells) -> smooth upsample -> gaussian; unreadable but keeps the layout"""
    x0, y0, x1, y1 = box
    pad = 2 * k
    crop = img.crop((x0 - pad, y0 - pad, x1 + pad, y1 + pad))
    w, h = crop.size
    sm = crop.resize((max(1, w // k), max(1, h // k)), Image.BOX).resize((w, h), Image.BICUBIC)
    sm = sm.filter(ImageFilter.GaussianBlur(k * 0.6))
    m = Image.new('L', crop.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((pad, pad, pad + (x1 - x0), pad + (y1 - y0)), radius=min(6, (y1 - y0) // 2), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(feather))
    img.paste(Image.composite(sm, crop, m), (x0 - pad, y0 - pad))

s4 = Image.open(os.path.join(SRC, 's4.png')).convert('RGB')
s5 = Image.open(os.path.join(SRC, 's5.png')).convert('RGB')
doc = Image.open(os.path.join(SRC, 'doc_top.png')).convert('RGB')
# --- privacy: personal tax ID (= national ID for an individual) and bank account number
redact(s5, (770, 473, 875, 488), 7)      # header tax id
redact(s5, (724, 913, 838, 928), 7)      # FROM block tax id
redact(s4, (739, 678, 823, 693), 7)      # bank account number
redact(doc, (328, 356, 532, 382), 13)     # doc header tax id
redact(doc, (105, 1154, 326, 1182), 13)   # doc FROM tax id
s4.save(os.path.join(W, 's4r.png')); s5.save(os.path.join(W, 's5r.png')); doc.save(os.path.join(W, 'docr.png'))

# --- form fields (source px). text = ink bbox (+1px), fill = area blanked before typing, align = input alignment
FIELDS = {
  'to':    {'img': 's5', 'text': [1099, 678, 1164, 690], 'fill': [1095, 675, 1168, 693], 'align': 'center', 'str': 'Smart Flow',        'caret': [676, 692]},
  'item':  {'img': 's4', 'text': [744, 358, 858, 373],   'fill': [740, 355, 862, 374],   'align': 'center', 'str': 'Smart Flow System', 'caret': [356, 373]},
  'price': {'img': 's4', 'text': [1131, 359, 1160, 370], 'fill': [1127, 356, 1164, 374], 'align': 'right',  'str': '3000',              'caret': [356, 373]},
}
# auto-calculated outputs (hidden until the price is entered)
TOTALS = [
  {'fill': [1230, 356, 1293, 373], 'mode': 'solid'},     # line total 3,000.00
  {'fill': [1228, 431, 1291, 448], 'mode': 'solid'},     # sum 3,000.00
  {'fill': [1192, 505, 1292, 532], 'mode': 'hinterp'},   # blue gradient box: B 3,000.00
  {'fill': [739, 457, 853, 478],   'mode': 'solid'},     # words: (Thai) three thousand baht
]
def bg_of(a, box):
    x0, y0, x1, y1 = box
    vals, cnt = np.unique(a[y0:y1, x0:x1].reshape(-1, 3), axis=0, return_counts=True)
    return vals[cnt.argmax()]
def blank(img, box, mode='solid'):
    a = np.asarray(img).copy(); x0, y0, x1, y1 = box
    if mode == 'solid':
        a[y0:y1, x0:x1] = bg_of(a, box)
    else:   # per-row linear interpolation between the columns just outside the box (gradient backgrounds)
        L = a[y0:y1, x0 - 1].astype(float); R = a[y0:y1, x1].astype(float)
        t = (np.arange(x1 - x0) + 1) / (x1 - x0 + 1)
        a[y0:y1, x0:x1] = np.clip(L[:, None, :] * (1 - t[None, :, None]) + R[:, None, :] * t[None, :, None] + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(a)
s5b = blank(s5, FIELDS['to']['fill'])
s4b = s4
for k in ('item', 'price'): s4b = blank(s4b, FIELDS[k]['fill'])
s4t = s4b.copy()   # item+price blank, totals still visible (not used) ; now hide totals
for t in TOTALS: s4b = blank(s4b, t['fill'], t['mode'])
s5b.save(os.path.join(W, 's5_blank.png')); s4b.save(os.path.join(W, 's4_blank.png'))
# field background colour (for the caret-only/blank states we paste strips onto the blank image)
for k, f in FIELDS.items():
    a = np.asarray(s5 if f['img'] == 's5' else s4)
    f['bg'] = [int(x) for x in bg_of(a, f['fill'])]
# character cut positions inside the final text strip (advance-width model snapped to low-ink columns)
ADV = {'S': 667, 'm': 833, 'a': 556, 'r': 333, 't': 278, ' ': 278, 'F': 611, 'l': 222, 'o': 556, 'w': 722, 'y': 500, 'e': 556, 's': 500, '3': 556, '0': 556}
for k, f in FIELDS.items():
    a = np.asarray(s5 if f['img'] == 's5' else s4).astype(int)
    x0, y0, x1, y1 = f['text']
    reg = a[y0:y1, x0:x1]; ink = (np.abs(reg - np.array(f['bg'])).sum(axis=2)).sum(axis=0)
    adv = np.cumsum([ADV[c] for c in f['str']]); adv = adv / adv[-1] * (x1 - x0)
    cuts = []
    for i, c in enumerate(adv):
        c = int(round(c))
        if i == len(adv) - 1: cuts.append(x1 - x0); break
        lo, hi = max(1, c - 2), min(x1 - x0 - 1, c + 2)
        best = min(range(lo, hi + 1), key=lambda j: (ink[j], abs(j - c)))
        cuts.append(best)
    f['cuts'] = cuts
MANUAL = {'to': [8, 19, 25, 29, 34, 38, 45, 47, 53, 65], 'item': [10, 21, 27, 31, 36, 40, 46, 49, 55, 66, 70, 76, 83, 88, 93, 99, 114], 'price': [8, 14, 21, 29]}
for k in FIELDS: FIELDS[k]['cuts'] = MANUAL[k]
json.dump({'fields': FIELDS, 'totals': TOTALS}, open(os.path.join(W, 'fields.json'), 'w'), indent=1)
print('fields:', {k: v['cuts'] for k, v in FIELDS.items()})

# --- blurred, tinted backgrounds (same recipe as v6)
BG = "eq=brightness=-0.10:contrast=1.0,format=gbrp,curves=all='0/0.03 0.5/0.24 1/0.50',lutrgb=r='val*0.42':g='val*0.74':b='val*1.22'"
for name in ('s4r', 's5r'):
    vf = f"scale=-2:1920:flags=bicubic,crop=1080:1920:(in_w-1080)/2:0,scale=270:480:flags=area,gblur=sigma=16:steps=3,scale=1188:2112:flags=bicubic,{BG},format=rgb24"
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(W, name + '.png'), '-vf', vf, '-frames:v', '1', os.path.join(W, 'bg_' + name[:2] + '.png')])
    if r.returncode: sys.exit('bg failed')
print('prep done')
