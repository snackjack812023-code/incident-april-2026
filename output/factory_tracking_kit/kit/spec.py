"""Timeline for the Factory Production Tracking TikTok promo (21.0 s, 30 fps, cuts on a 120 BPM beat grid).
Camera rects are in screenshot px (1920x1080, app area y 88..1032 -> browser bar / taskbar never in frame).
Run directly to write work/spec.json for the overlay + audio scripts."""
import json, math, os

FPS, N = 30, 630
BPM = 120
BEAT = FPS * 60 / BPM                       # 15 frames
CARD = dict(x=70, y=560, w=900, h=800, r=28)
AR = CARD['w'] / CARD['h']
APP = (0, 88, 1920, 1032)                   # usable source area
WMAX = (APP[3] - APP[1]) * AR               # 1062: widest crop that fits the app height

SCENES = [  # key, screenshot, f0, f1
    ('s1', 'dashboard', 0, 60), ('s2', 'dashboard', 60, 150), ('s3', 'calendar', 150, 210), ('s4', 'po', 210, 270),
    ('s5', 'board', 270, 360), ('s6', 'dept', 360, 420), ('s7', 'delivery', 420, 480), ('s8', 'report', 480, 540),
    ('s9', 'dashboard', 540, 630)]
CUTS = [150, 210, 270, 360, 420, 480, 540]  # hard cuts (zoom-through transition); s1->s2 is one continuous shot

def _io(p): return 0.5 - 0.5 * math.cos(math.pi * p)
EASE = {
    'lin': lambda p: p, 'io': _io,
    'out3': lambda p: 1 - (1 - p) ** 3, 'out4': lambda p: 1 - (1 - p) ** 4, 'in2': lambda p: p * p,
    'snap': lambda p: 0.3 * p + 0.7 * _io(p),          # beat-synced KPI hops that never fully stop
}
# camera keyframes: (frame, (cx, cy, w), ease of the segment that ends here)
KF = {   # holds are slow drifts (text stays sharp); quick moves get motion blur
    's1': [(0, (531, 560, 1062), None), (3, (530, 558, 1058), 'lin'), (16, (470, 435, 780), 'io'), (60, (462, 435, 744), 'lin')],
    's2': [(60, (462, 435, 744), None), (68, (480, 560, 960), 'io'), (104, (488, 560, 930), 'lin'),
           (116, (1290, 560, 960), 'io'), (150, (1300, 565, 915), 'lin')],
    's3': [(150, (1240, 560, 1000), None), (172, (1250, 565, 960), 'lin'), (182, (1490, 676, 800), 'io'), (210, (1492, 678, 776), 'lin')],
    's4': [(210, (370, 400, 700), None), (226, (380, 400, 690), 'lin'), (238, (1020, 400, 700), 'io'), (270, (1030, 402, 680), 'lin')],
    's5': [(270, (800, 560, 1040), None), (294, (785, 530, 960), 'lin'), (306, (800, 440, 640), 'io'), (322, (812, 444, 630), 'lin'),
           (334, (1460, 745, 640), 'io'), (360, (1452, 748, 600), 'lin')],
    's6': [(360, (470, 490, 900), None), (394, (482, 490, 876), 'lin'), (404, (1400, 490, 900), 'io'), (420, (1410, 492, 880), 'lin')],
    's7': [(420, (420, 480, 800), None), (440, (430, 482, 780), 'lin'), (450, (1270, 533, 1000), 'io'), (480, (1275, 535, 970), 'lin')],
    's8': [(480, (1505, 470, 760), None), (494, (1508, 470, 748), 'lin'), (512, (1389, 560, 1062), 'io'), (540, (1380, 560, 1040), 'lin')],
    's9': [(540, (620, 430, 760), None), (630, (560, 560, 1062), 'io')],
}
OUT_ZOOM, OUT_LEN = 0.10, 3      # last frames before a cut: push in
IN_ZOOM, IN_LEN = 0.10, 8        # first frames after a cut: start wider, settle (continues the forward motion)

def scene_at(t):
    for i, (k, src, f0, f1) in enumerate(SCENES):
        if f0 <= t < f1: return i
    return len(SCENES) - 1 if t >= N else 0

def clamp_rect(cx, cy, w):
    w = min(w, WMAX); h = w / AR
    cx = min(max(cx, APP[0] + w / 2), APP[2] - w / 2)
    cy = min(max(cy, APP[1] + h / 2), APP[3] - h / 2)
    return cx, cy, w

def cam(t):
    """camera rect (u, v, w) in source px at (fractional) frame t"""
    i = scene_at(t); key, src, f0, f1 = SCENES[i]; ks = KF[key]
    if t <= ks[0][0]: cx, cy, w = ks[0][1]
    elif t >= ks[-1][0]: cx, cy, w = ks[-1][1]
    else:
        for a, b in zip(ks, ks[1:]):
            if a[0] <= t <= b[0]:
                p = (t - a[0]) / (b[0] - a[0]); e = EASE[b[2]](p)
                cx = a[1][0] + (b[1][0] - a[1][0]) * e; cy = a[1][1] + (b[1][1] - a[1][1]) * e
                w = math.exp(math.log(a[1][2]) + (math.log(b[1][2]) - math.log(a[1][2])) * e)   # zoom uniformly
                break
    # zoom-through transitions
    if f1 in CUTS and t > f1 - OUT_LEN: w *= 1 - OUT_ZOOM * EASE['in2']((t - (f1 - OUT_LEN)) / OUT_LEN)
    if f0 in CUTS and t < f0 + IN_LEN: w *= 1 + IN_ZOOM * (1 - EASE['out3']((t - f0) / IN_LEN))
    cx, cy, w = clamp_rect(cx, cy, w)
    return cx - w / 2, cy - w / AR / 2, w

def card_tf(t):
    """card transform: scale about its centre, dim (0..1) and blur px (closing scene)"""
    s, dim, blur = 1.0, 0.0, 0.0
    if t < 12: s = 0.92 + 0.08 * EASE['out3'](t / 12)                       # opening push
    for c in CUTS:
        if c - OUT_LEN < t < c: s *= 1 + 0.03 * EASE['in2']((t - (c - OUT_LEN)) / OUT_LEN)
        if c <= t < c + IN_LEN: s *= 0.94 + 0.06 * EASE['out3']((t - c) / IN_LEN)
    if t >= 540:                                                             # closing: card recedes behind the title
        q = EASE['out3'](min(1, (t - 540) / 16)); dim = 0.64 * q; blur = 5.0 * q
        s *= 1 - 0.04 * EASE['io'](min(1, (t - 540) / 90))
    return s, dim, blur

def bg_at(t):
    """background source + slow zoom; crossfade 4 frames around cuts"""
    i = scene_at(t); key, src, f0, f1 = SCENES[i]
    z = 1.0 + 0.05 * (t - f0) / (f1 - f0)
    mix = None
    for c in CUTS:
        if c - 2 <= t < c + 2 and i > 0:
            j = scene_at(c - 1); k = scene_at(c)
            mix = (SCENES[j][1], SCENES[k][1], (t - (c - 2)) / 4)
    return src, z, mix

# focus highlights (spotlight + ring) in source px: track of (frame_on, rect); each target morphs to the next
FOCUS = [
    {'scene': 's2', 'color': 'cyan', 'dim': 0.34, 'off': 148, 'click': True, 'targets': [
        (68, (24, 416, 296, 137)), (79, (336, 416, 296, 137)), (90, (336, 569, 296, 136)),
        (101, (648, 416, 296, 137)), (120, (960, 416, 297, 137)), (135, (1273, 416, 296, 137))]},
    {'scene': 's3', 'color': 'orange', 'dim': 0.30, 'off': 208, 'click': False, 'targets': [
        (158, (1089, 602, 259, 148)), (182, (1622, 783, 256, 140))]},
    {'scene': 's4', 'color': 'cyan', 'dim': 0.28, 'off': 268, 'click': False, 'targets': [
        (214, (26, 266, 150, 350)), (236, (832, 266, 232, 350))]},
    {'scene': 's5', 'color': 'cyan', 'dim': 0.36, 'off': 358, 'click': True, 'targets': [
        (306, (665, 455, 77, 38)), (335, (1290, 799, 76, 38)), (343, (1370, 799, 63, 38)), (351, (1545, 799, 84, 38))]},
    {'scene': 's6', 'color': 'cyan', 'dim': 0.30, 'off': 418, 'click': False, 'targets': [
        (363, (24, 223, 303, 80)), (374, (335, 223, 303, 80)), (385, (646, 223, 302, 80)), (405, (1267, 223, 303, 80))]},
    {'scene': 's7', 'color': 'cyan', 'dim': 0.26, 'off': 478, 'click': False, 'targets': [
        (424, (148, 350, 360, 255)), (451, (773, 350, 360, 255)), (464, (1397, 350, 360, 255))]},
    {'scene': 's8', 'color': 'green', 'dim': 0.34, 'off': 514, 'click': True, 'targets': [
        (484, (1542, 166, 341, 44))]},
]

def export():
    frames = []
    for f in range(N):
        u, v, w = cam(f); s, dim, blur = card_tf(f); src, z, mix = bg_at(f)
        frames.append({'f': f, 'scene': SCENES[scene_at(f)][0], 'cam': [round(u, 3), round(v, 3), round(w, 3)],
                       'card': [round(s, 5), round(dim, 4), round(blur, 3)]})
    # sound events (frames) for the mixer: whoosh on every page change, clicks on KPI/button focus, pops on key text
    sfx = [{'f': 0, 'name': 'whoosh', 'peak': -17}]
    sfx += [{'f': c, 'name': 'whoosh', 'peak': -17, 'off': -0.10} for c in CUTS]
    for fo in FOCUS:
        if fo['click']: sfx += [{'f': t, 'name': 'click', 'peak': -21} for t, _ in fo['targets']]
    sfx += [{'f': 4, 'name': 'pop', 'peak': -19}, {'f': 546, 'name': 'pop', 'peak': -18}, {'f': 586, 'name': 'pop', 'peak': -17}]
    spec = {'FPS': FPS, 'N': N, 'BPM': BPM, 'CARD': CARD, 'scenes': SCENES, 'cuts': CUTS, 'focus': FOCUS, 'sfx': sfx, 'frames': frames}
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'spec.json')
    json.dump(spec, open(out, 'w'))
    sc = [CARD['w'] / fr['cam'][2] for fr in frames]
    print(f'spec: {N} frames ({N / FPS:.2f} s), beat {BEAT:.0f} f; card scale range {min(sc):.2f}..{max(sc):.2f}x; sfx {len(sfx)}')

if __name__ == '__main__':
    export()
