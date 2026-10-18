"""Text-line fit used by the privacy blur: the straight line (yL at xL, yR at xR) near a prediction along which the
horizontal-gradient energy (text strokes) is highest, searched jointly over both ends, so a short neighbouring line
(a label above, a button below) can't pull one end away the way a per-segment maximum does. Lines may run past the
frame edge (an URL cut by the edge): only the visible part is scored and the result is extended back along the line."""
import numpy as np, cv2

def energy(gray):
    g = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
    return cv2.boxFilter(g, -1, (9, 5))                      # stroke energy smoothed over ~ a character cell

def fit(E, xL, yL, xR, yR, win=24, step=1):
    H, Wd = E.shape
    y_at = lambda x: yL + (yR - yL) * (x - xL) / max(1e-6, xR - xL)
    xa, xb = max(0.0, float(xL)), min(Wd - 1.0, float(xR))
    if xb - xa < 40: return float(yL), float(yR), 0.0          # (almost) nothing of the line on screen
    ya, yb = y_at(xa), y_at(xb)
    xs = np.arange(xa, xb + 1, 3, dtype=np.float32); u = (xs - xa) / (xb - xa)
    d = np.arange(-win, win + 1, step, dtype=np.float32)
    Y = (ya + d[:, None, None]) * (1 - u) + (yb + d[None, :, None]) * u    # (nd, nd, nx)
    Yi = np.clip(np.round(Y).astype(np.int32), 0, H - 1)
    vals = E[Yi, xs.astype(np.int32)[None, None, :]]
    # a text line is energetic along its whole length: use a low percentile so empty stretches cost, plus the mean
    score = 0.5 * vals.mean(-1) + 0.5 * np.percentile(vals, 30, axis=-1)
    i, j = np.unravel_index(np.argmax(score), score.shape)
    na, nb = ya + d[i], yb + d[j]; k = (nb - na) / (xb - xa)
    return float(na + k * (xL - xa)), float(na + k * (xR - xa)), float(score[i, j])
