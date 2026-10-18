"""Output timeline from the EDL: snapped cut points, clip placement, and every overlay mapped to output frames."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl

FPS = 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, 'work')
SR = 48000
_V = None
def voice():
    global _V
    if _V is None: _V = np.load(os.path.join(W, 'voice_proc.npy')).astype(np.float32)
    return _V

def snap(t, win=0.08):
    """move a cut to the quietest 10 ms inside +-win (never into a word)"""
    v = voice(); h = int(0.005 * SR); best, bt = 1e9, t
    for c in np.arange(t - win, t + win + 1e-9, 0.005):
        i = int(c * SR); seg = v[max(0, i - h):i + h]
        e = float(np.mean(seg * seg)) if len(seg) else 1e9
        if e < best - 1e-12: best, bt = e, c
    return round(float(bt), 3)

def env20(t):
    v = voice(); i = int(t * SR); h = int(0.01 * SR); seg = v[max(0, i - h):i + h]
    return 10 * np.log10(float(np.mean(seg * seg)) + 1e-12) if len(seg) else -120.0

def quiet_run(t, direction, quiet_db=-45.0, step=0.005, limit=0.4):
    """first quiet run (>= 40 ms below quiet_db) at/after t (direction +1) or at/before t (-1): (start, end)"""
    ts = np.arange(t, t + direction * limit, direction * step)
    q = np.array([env20(x) < quiet_db for x in ts])
    need = int(0.04 / step)
    for i in range(len(q) - need):
        if q[i:i + need].all():
            j = i
            while j < len(q) and q[j]: j += 1
            a, b = ts[i], ts[j - 1]
            return (min(a, b), max(a, b))
    return None

def snap_out(b):
    """end a clip only after the last syllable has died away (Thai tones keep sounding after the word timing ends)"""
    r = quiet_run(b - 0.02, +1)
    return round(r[0] + min(0.03, (r[1] - r[0]) / 2), 3) if r else snap(b)

def snap_in(a):
    """start a clip inside the silence just before the first syllable"""
    r = quiet_run(a + 0.02, -1)
    return round(r[1] - min(0.02, (r[1] - r[0]) / 2), 3) if r else snap(a)

def build():
    clips = [dict(c) for c in edl.C]
    talk = lambda c: c['freeze'] is None and c['audio'] == 'voice' and c['speed'] == 1.0
    for i, c in enumerate(clips):
        if not talk(c): continue
        cont_prev = i > 0 and talk(clips[i - 1]) and abs(edl.C[i - 1]['b'] - edl.C[i]['a']) < 1e-6
        cont_next = i + 1 < len(clips) and talk(clips[i + 1]) and abs(edl.C[i]['b'] - edl.C[i + 1]['a']) < 1e-6
        c['a'] = clips[i - 1]['b'] if cont_prev else max(0.0, snap_in(c['a']))
        c['b'] = snap(c['b']) if cont_next else snap_out(c['b'])
    for i, c in enumerate(clips):                       # silent ramps butt exactly against their snapped neighbours
        if c['freeze'] is None and c['audio'] == 'mute':   # (compared on the EDL times: a neighbour's word-safe snap
            # can move its edge > 0.15 s, which would otherwise replay a few frames of picture at the cut)
            if i > 0 and abs(edl.C[i - 1]['b'] - edl.C[i]['a']) < 0.15: c['a'] = clips[i - 1]['b']
            if i + 1 < len(clips) and abs(edl.C[i + 1]['a'] - edl.C[i]['b']) < 0.15: c['b'] = clips[i + 1]['a']
    t_out = 0
    for c in clips:
        n = int(round((c['dur'] if c['freeze'] is not None else (c['b'] - c['a']) / c['speed']) * FPS))
        c['f0'], c['f1'] = t_out, t_out + n; t_out += n
    return clips

CLIPS = build()
N = CLIPS[-1]['f1']
BY_ID = {c['id']: c for c in CLIPS}

def src_time(c, f):
    """source time shown at output frame f of clip c"""
    if c['freeze'] is not None: return c['freeze']
    return c['a'] + (f - c['f0']) / FPS * c['speed']

def out_frame(c, t_src):
    return c['f0'] + (t_src - c['a']) / c['speed'] * FPS

def clip_at(f):
    for c in CLIPS:
        if c['f0'] <= f < c['f1']: return c
    return CLIPS[-1]

def subs():
    """[(f0, f1, text)] in output frames; consecutive subs never overlap"""
    out = []
    for c in CLIPS:
        for a, b, txt in c['subs']:
            f0 = max(c['f0'], out_frame(c, max(a, c['a']))); f1 = min(c['f1'], out_frame(c, min(b, c['b'])))
            if f1 - f0 >= 6: out.append([int(round(f0)), int(round(f1)), txt])
    for i in range(len(out) - 1):
        if out[i][1] > out[i + 1][0]: out[i][1] = out[i + 1][0]
    return [tuple(s) for s in out]

def sections():
    """[(section, f0, f1)] contiguous runs of the same section"""
    out = []
    for c in CLIPS:
        if out and out[-1][0] == c['sec']: out[-1][2] = c['f1']
        else: out.append([c['sec'], c['f0'], c['f1']])
    return [tuple(s) for s in out]

def zoom_at(c, f):
    """(z, cx, cy) for output frame f of clip c; smooth (ease in-out) between keys"""
    t = (f - c['f0']) / FPS; ks = c['zoom']
    if t <= ks[0][0] or len(ks) == 1: return ks[0][1:]
    for (t0, *a), (t1, *b) in zip(ks[:-1], ks[1:]):
        if t0 <= t <= t1:
            p = (t - t0) / max(1e-6, t1 - t0); p = 0.5 - 0.5 * np.cos(np.pi * p)
            return tuple(x + (y - x) * p for x, y in zip(a, b))
    return ks[-1][1:]

if __name__ == '__main__':
    tot = 0
    for c in CLIPS:
        d = (c['f1'] - c['f0']) / FPS; tot += d
        print(f"{c['id']:5s} {c['sec']:7s} src {c['a']:7.3f}-{c['b']:7.3f} x{c['speed']:<3} -> out {c['f0'] / FPS:6.2f}-{c['f1'] / FPS:6.2f} ({d:5.2f}s)")
    print(f'total {N / FPS:.2f} s ({N} frames)')
    for s, f0, f1 in sections(): print(f'  {s:7s} {f0 / FPS:6.2f}-{f1 / FPS:6.2f}  ({(f1 - f0) / FPS:5.2f}s)')
