"""Re-edit of the LINE-notification demo clip for TikTok (16.5 s, 30 fps, 1080x1920).
Source: work/clean.mkv = uploaded 576x1024 clip, deblocked + denoised + stabilised (vidstab).
Shots (output frames):  A hook (phone, payoff first) | B click "send LINE alert" | C confirm dialog (1.33x) | D success
| E tilt (2x, frame-blended) + phone close-up (camera follows the message card) | F CTA freeze | G cover poster (selectable as TikTok cover)
Run directly to write work/edit.json (overlay + audio cues) or import for the renderer."""
import json, math, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS, N, W, H = 30, 495, 576, 1024
def _io(p): return 0.5 - 0.5 * math.cos(math.pi * p)
EASE = {'lin': lambda p: p, 'io': _io, 'out3': lambda p: 1 - (1 - p) ** 3, 'in2': lambda p: p * p}

# camera keyframes per shot: (frame, (cx, cy, zoom)[, ease]) in source px of the 576x1024 clip; zoom 1 = full frame
SHOTS = [
    {'key': 'A', 'f0': 0,   'f1': 60,  'src': (540, 600), 'grade': 'phone',   'track': True,
     'cam': [(0, (290, 455, 1.10)), (60, (290, 450, 1.18), 'io')]},
    {'key': 'B', 'f0': 60,  'f1': 120, 'src': (30, 90),   'grade': 'monitor',
     'cam': [(60, (262, 372, 1.12)), (104, (178, 452, 1.42), 'io'), (120, (168, 455, 1.52), 'in2')]},
    {'key': 'C', 'f0': 120, 'f1': 195, 'src': (114, 214), 'grade': 'monitor',
     'cam': [(120, (369, 360, 1.27)), (182, (372, 366, 1.37), 'lin'), (195, (430, 468, 1.62), 'io')]},
    {'key': 'D', 'f0': 195, 'f1': 240, 'src': (396, 441), 'grade': 'monitor',
     'cam': [(195, (363, 330, 1.45)), (200, (363, 330, 1.45), 'lin'), (209, (363, 318, 1.62), 'out3'), (240, (363, 316, 1.66), 'lin')]},
    {'key': 'E1', 'f0': 240, 'f1': 270, 'src': (441, 501), 'grade': 'tilt', 'blend': 2,
     'cam': [(240, (288, 470, 1.04)), (270, (290, 452, 1.08), 'lin')]},
    {'key': 'E2', 'f0': 270, 'f1': 369, 'src': (501, 600), 'grade': 'phone', 'track': True,
     'cam': [(270, (290, 440, 1.08)), (369, (290, 432, 1.24), 'io')]},
    {'key': 'F', 'f0': 369, 'f1': 450, 'freeze': 576, 'grade': 'phone', 'track': True,
     'cam': [(369, (290, 432, 1.24)), (450, (290, 426, 1.32), 'lin')]},
    {'key': 'G', 'f0': 450, 'f1': 495, 'poster': True, 'zoom': [(450, 1.07), (458, 1.0, 'out3'), (495, 1.035, 'lin')]},
]
CUTS = [60, 120, 195, 450]          # hard cuts with a short zoom-through (B, C, D entries) ; 240 is the real camera tilt
GRADE = {'monitor': (1.30, 1.28, 1.10), 'phone': (1.32, 1.17, 1.08)}
TRACK = {int(k): v for k, v in json.load(open(os.path.join(ROOT, 'work', 'card_track.json'))).items()}   # card drift vs sf 570

def shot_at(t):
    for s in SHOTS:
        if s['f0'] <= t < s['f1']: return s
    return SHOTS[-1]
def src_frame(t):
    """fractional source frame for output time t (frames)"""
    s = shot_at(t)
    if 'freeze' in s: return float(s['freeze'])
    if 'poster' in s: return None
    a, b = s['src']; p = (t - s['f0']) / (s['f1'] - s['f0'])
    return a + (b - a) * p
def kf(ks, t):
    if t <= ks[0][0]: return ks[0][1]
    for a, b in zip(ks, ks[1:]):
        if a[0] <= t <= b[0]:
            e = EASE[b[2] if len(b) > 2 else 'lin']((t - a[0]) / max(1e-9, b[0] - a[0]))
            if isinstance(a[1], tuple): return tuple(x + (y - x) * e for x, y in zip(a[1], b[1]))
            return a[1] + (b[1] - a[1]) * e
    return ks[-1][1]
def cam(t):
    """crop box (u, v, w, h) in source px"""
    s = shot_at(t); cx, cy, z = kf(s['cam'], t)
    if s.get('track'):
        sf = src_frame(t); k = int(round(min(max(sf, 480), 600))); dx, dy = TRACK.get(k, (0, 0)); cx += dx; cy += dy
    for c in CUTS:                                   # zoom-through: push in before a cut, settle after it
        if c - 3 < t < c: z *= 1 + 0.08 * EASE['in2']((t - (c - 3)) / 3)
        if c <= t < c + 6 and s['key'] != 'G': z *= 1 - 0.07 * (1 - EASE['out3']((t - c) / 6))
    z = max(z, 1.0); w, h = W / z, H / z
    u = min(max(cx - w / 2, 0), W - w); v = min(max(cy - h / 2, 0), H - h)
    return u, v, w, h
def grade_at(t):
    s = shot_at(t)
    if s.get('grade') == 'tilt':
        p = EASE['io']((t - s['f0']) / (s['f1'] - s['f0']))
        return tuple(a + (b - a) * p for a, b in zip(GRADE['monitor'], GRADE['phone']))
    return GRADE.get(s.get('grade'), (1, 1, 1))
def cta_fx(t):
    """dim / blur of the freeze-frame under the CTA"""
    if 369 <= t < 450: q = EASE['out3'](min(1, (t - 369) / 12)); return 0.56 * q, 4.0 * q
    return 0.0, 0.0
def poster_zoom(t):
    z = kf(SHOTS[-1]['zoom'], t)
    return z

# overlay + audio cues (output frames)
CUES = {
    'clicks': [119, 193],            # B: send-LINE click (src 89) ; C: confirm click (src 211 @1.33x)
    'success': 200,                  # D: success dialog pops (src 401)
    'ding': 272,                     # E: message on the phone
    'whoosh': [0, 60, 120, 195, 240, 450],
    'pop': [5, 372],
}
# highlight targets in source px (x, y, w, h), shown [on, off)
RINGS = [
    {'key': 'btn', 'rect': (74, 441, 90, 23), 'on': 76, 'off': 121},
    {'key': 'msg', 'rect': (222, 343, 288, 40), 'on': 132, 'off': 178},
    {'key': 'ok', 'rect': (431, 508, 64, 26), 'on': 178, 'off': 196},
    {'key': 'done', 'rect': (292, 268, 142, 84), 'on': 201, 'off': 240},
    {'key': 'card', 'rect': (157, 290, 267, 279), 'on': 274, 'off': 369, 'track': True},
]
RIPPLES = [{'f': 119, 'x': 152, 'y': 462, 'shot': 'B'}, {'f': 193, 'x': 452, 'y': 526, 'shot': 'C'}]

def export():
    frames = []
    for f in range(N):
        s = shot_at(f); sf = src_frame(f)
        e = {'f': f, 'shot': s['key']}
        if 'poster' not in s:
            u, v, w, h = cam(f); e['cam'] = [round(u, 3), round(v, 3), round(w, 3)]
            k = int(round(min(max(sf, 480), 600))); e['trk'] = TRACK.get(k, (0, 0)) if sf >= 480 else [0, 0]
        frames.append(e)
    shots = [{k: v for k, v in s.items() if k in ('key', 'f0', 'f1')} for s in SHOTS]
    out = {'FPS': FPS, 'N': N, 'W': W, 'H': H, 'shots': shots, 'cues': CUES, 'rings': RINGS, 'ripples': RIPPLES, 'frames': frames}
    json.dump(out, open(os.path.join(ROOT, 'work', 'edit.json'), 'w'))
    print(f'edit: {N} frames ({N / FPS:.1f} s), shots ' + ' '.join(f"{s['key']}:{s['f0']}-{s['f1']}" for s in SHOTS))
if __name__ == '__main__':
    export()
