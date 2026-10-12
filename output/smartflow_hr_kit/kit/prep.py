"""Stage 0: 9 storyboard images (~941x1672, 9:16) -> badge-free images -> 4x super-resolved images.
- the storyboard annotation badge (blue scene number + "0:00 - 0:02" time pill, top-left) is not part of the scene artwork:
  it is masked and filled from the surrounding bokeh (inpaint at 1/4 resolution -> smooth, no streaks), headline pixels protected
- 4x Real-ESRGAN general-x4v3 (kit/sr.py, NumPy, whole image -> no tile seams) -> work/sr_s{k}.png
usage: python3 prep.py [--no-sr] [--only 1,2,...]"""
import os, sys, time
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, W, AN = (os.path.join(ROOT, d) for d in ('src', 'work', 'an'))
for d in (W, AN): os.makedirs(d, exist_ok=True)

def badge_mask(a):
    """badge = blue number square (detected: largest solid blue blob top-left, thin outlines removed by an opening)
    + time pill (same template in every panel: from the square to x~480, y~50-145, with a soft glow)"""
    h, w, _ = a.shape; R, G, B = (a[..., i].astype(int) for i in range(3))
    blue = ((B > 200) & (R < 90) & (G > 80) & (G < 180)).astype(np.uint8); blue[230:, :] = 0; blue[:, 300:] = 0
    op = cv2.morphologyEx(blue, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(op); i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, bw, bh = (int(v) for v in st[i, :4]); bx0, by0, bx1, by1 = x, y, x + bw - 1, y + bh - 1
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (max(0, bx0 - 14), max(0, by0 - 14)), (bx1 + 14, by1 + 14), 255, -1)    # square + glow
    cv2.rectangle(m, (bx1 - 10, 36), (500, 162), 255, -1)                                      # time pill + outline glow
    # never touch the scene's own headline/artwork below the badge
    bright = (np.minimum(np.minimum(R, G), B) > 170) | ((R > 200) & (G > 160) & (B < 90))
    protect = bright.copy(); protect[:by1 + 16, :] = False
    protect = cv2.dilate(protect.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    m[protect] = 0
    return m, (bx0, by0, bx1, by1), (bx1 - 10, 36, 500, 162)

def fill(img, m, k=4):
    """inpaint at 1/k resolution (bokeh background is low-frequency), upsample, feathered composite"""
    h, w = m.shape; small = cv2.resize(img, (w // k, h // k), interpolation=cv2.INTER_AREA)
    ms = (cv2.resize(m, (w // k, h // k), interpolation=cv2.INTER_AREA) > 0).astype(np.uint8) * 255
    ms = cv2.dilate(ms, np.ones((3, 3), np.uint8))
    f = cv2.inpaint(small, ms, 9, cv2.INPAINT_TELEA)
    f = cv2.GaussianBlur(f, (0, 0), 1.6)
    up = cv2.resize(f, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    a = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 4.0)[..., None]
    # keep a little of the original fine texture statistics: add soft noise matched to the surround
    rng = np.random.default_rng(5); noise = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 0.8)[..., None] * 1.6
    return np.clip(img.astype(np.float32) * (1 - a) + (up + noise) * a + 0.5, 0, 255).astype(np.uint8)

def main():
    if '--sr-only' in sys.argv: return run_sr([int(x) for x in sys.argv[sys.argv.index('--sr-only') + 1].split(',')])
    only = [int(x) for x in sys.argv[sys.argv.index('--only') + 1].split(',')] if '--only' in sys.argv else list(range(1, 10))
    checks = []
    for k in only:
        bgr = cv2.imread(os.path.join(SRC, f's{k}.png'), cv2.IMREAD_COLOR); rgb = bgr[..., ::-1]
        m, sq, tx = badge_mask(rgb)
        out = fill(bgr, m)
        cv2.imwrite(os.path.join(W, f'clean_s{k}.png'), out)
        print(f's{k}: {bgr.shape[1]}x{bgr.shape[0]} square {sq} pill {tx} masked {int((m > 0).sum())} px', flush=True)
        t = np.concatenate([bgr[:300, :620], np.full((300, 8, 3), (255, 0, 255), np.uint8), out[:300, :620]], axis=1); checks.append(t)
    cv2.imwrite(os.path.join(AN, 'badge_check.png'), np.concatenate([np.pad(c, ((0, 6), (0, 0), (0, 0))) for c in checks], axis=0))
    if '--no-sr' in sys.argv: return
    run_sr(only)

def run_sr(only):
    import sr
    for k in only:
        t0 = time.time(); img = cv2.imread(os.path.join(W, f'clean_s{k}.png'), cv2.IMREAD_COLOR)[..., ::-1]
        up = sr.upscale4(np.ascontiguousarray(img))
        cv2.imwrite(os.path.join(W, f'sr_s{k}.png'), up[..., ::-1]); print(f'sr s{k}: {up.shape[1]}x{up.shape[0]} in {time.time() - t0:.0f}s', flush=True)

if __name__ == '__main__':
    main()
