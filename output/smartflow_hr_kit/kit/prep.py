"""Stage 0: storyboard (1024x1536) -> 9 clean panels -> 4x super-resolved panels.
- panels are cut at the white gutters (x 340 / 683-685, y 110 / 594-595 / 1032-1033)
- the storyboard annotation badge (blue scene number + "0:00 - 0:02" time pill, top-left of every panel) is not part of the
  scene artwork: it is masked (headline pixels protected) and inpainted (OpenCV Telea) before upscaling
- 4x Real-ESRGAN general-x4v3 (kit/sr.py, NumPy) -> work/sr_p{1..9}.png ; also writes an/badge_check.png for review"""
import os, sys
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, W = os.path.join(ROOT, 'src'), os.path.join(ROOT, 'work'); os.makedirs(W, exist_ok=True); os.makedirs(os.path.join(ROOT, 'an'), exist_ok=True)
COLS = [(0, 340), (341, 683), (686, 1024)]; ROWS = [(111, 594), (596, 1032), (1034, 1536)]

def badge_mask(a):
    h, w, _ = a.shape; R, G, B = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    m = np.zeros((h, w), np.uint8)
    # blue number square
    blue = (B > 180) & (R < 110) & (G > 60) & (G < 175); blue[60:, :] = False; blue[:, 70:] = False
    ys, xs = np.where(blue); bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    cv2.rectangle(m, (max(0, bx0 - 6), max(0, by0 - 6)), (bx1 + 5, by1 + 5), 255, -1)   # incl. anti-aliased fringe
    # time pill: bbox of the white time label right of the square, expanded to the pill outline
    reg = np.zeros((h, w), bool); reg[12:38, bx1 + 8:166] = True       # the time label always sits in this band
    white = (np.minimum(np.minimum(R, G), B) > 165) & reg
    ys, xs = np.where(white); tx0, tx1, ty0, ty1 = xs.min(), xs.max(), ys.min(), ys.max()
    px0, px1, py0, py1 = bx1 - 4, tx1 + 20, max(0, ty0 - 13), ty1 + 12     # incl. the pill's soft edge/shadow
    cv2.rectangle(m, (px0, py0), (px1, py1), 255, -1)
    # protect headline / logo pixels (bright or saturated) that are outside the time label
    bright = (np.minimum(np.minimum(R, G), B) > 150) | ((R > 180) & (G > 150) & (B < 90)) | ((G > 150) & (R < 120) & (B < 140))
    protect = bright.copy(); protect[:ty1 + 4, :] = False                  # headlines only ever start below the time label
    protect[by0:by1 + 1, bx0:bx1 + 1] = False
    protect = cv2.dilate(protect.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    m[protect] = 0
    return m, (bx0, by0, bx1, by1), (tx0, ty0, tx1, ty1), (px0, py0, px1, py1)

def main():
    sb = Image.open(os.path.join(SRC, 'storyboard.png')).convert('RGB')
    checks = []
    for k in range(9):
        r, c = ROWS[k // 3], COLS[k % 3]
        p = np.asarray(sb.crop((c[0], r[0], c[1], r[1])))
        m, bsq, txt, pill = badge_mask(p)
        bgr = cv2.cvtColor(p, cv2.COLOR_RGB2BGR)
        fill = cv2.inpaint(bgr, m, 6, cv2.INPAINT_TELEA)
        soft = cv2.GaussianBlur(fill, (0, 0), 2.2)                 # bokeh background: no hard inpaint streaks
        mm = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 1.2)[..., None]
        out = cv2.cvtColor((bgr * (1 - mm) + soft * mm).astype(np.uint8), cv2.COLOR_BGR2RGB)
        Image.fromarray(out).save(os.path.join(W, f'clean_p{k + 1}.png'))
        print(f'p{k + 1}: {p.shape[1]}x{p.shape[0]} square {bsq} time-text {txt} pill {pill} masked px {int((m > 0).sum())}')
        before = Image.fromarray(p).crop((0, 0, 210, 80)).resize((630, 240), Image.NEAREST)
        after = Image.fromarray(out).crop((0, 0, 210, 80)).resize((630, 240), Image.NEAREST)
        t = Image.new('RGB', (1270, 240), (255, 0, 255)); t.paste(before, (0, 0)); t.paste(after, (640, 0)); checks.append(t)
    sheet = Image.new('RGB', (1270, 250 * 9), (30, 30, 30))
    for i, t in enumerate(checks): sheet.paste(t, (0, i * 250))
    sheet.save(os.path.join(ROOT, 'an', 'badge_check.png'))
    if '--no-sr' in sys.argv: return
    for k in range(1, 10):
        img = np.asarray(Image.open(os.path.join(W, f'clean_p{k}.png')).convert('RGB'))
        Image.fromarray(sr.upscale4(img)).save(os.path.join(W, f'sr_p{k}.png')); print(f'sr p{k} done', flush=True)

if __name__ == '__main__':
    main()
