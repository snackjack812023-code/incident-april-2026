"""Timeline for SmartFlow HR & Time Attendance TikTok (storyboard scenes 01-09, 20.0 s, 30 fps, cuts on a 120 BPM grid).
All geometry is in 1x storyboard-panel px (the renderer samples the 4x super-resolved panels).
Camera = (cx, cy, w); the 9:16 window is w wide and w*16/9 tall. Writes work/spec.json for overlay/audio/renderer."""
import json, math, os

FPS, N = 30, 600
OW, OH = 1080, 1920
ASP = OH / OW
PANEL = {1: (340, 483), 2: (342, 483), 3: (338, 483), 4: (340, 436), 5: (342, 436), 6: (338, 436), 7: (340, 502), 8: (342, 502), 9: (338, 502)}
# scene k uses storyboard panel k; frame ranges from the brief (0-2, 2-4, 4-6, 6-8, 8-11, 11-13, 13-16, 16-18, 18-20 s)
SCENES = [(1, 0, 60), (2, 60, 120), (3, 120, 180), (4, 180, 240), (5, 240, 330), (6, 330, 390), (7, 390, 480), (8, 480, 540), (9, 540, 600)]
CUTS = [s[1] for s in SCENES[1:]]
OUT_LEN, IN_LEN, XF = 4, 6, 2          # zoom-through: 4 frames push-in before a cut, 6 frames settle after, 2+2 frames crossfade

def _io(p): return 0.5 - 0.5 * math.cos(math.pi * p)
EASE = {'lin': lambda p: p, 'io': _io, 'out3': lambda p: 1 - (1 - p) ** 3, 'in2': lambda p: p * p, 'in3': lambda p: p ** 3,
        'iocubic': lambda p: 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2}

# camera keyframes (frame, (cx, cy, w), ease-of-segment-ending-here)
# Each scene: short hold on the storyboard headline -> dive into the UI -> slow drift. In the zoomed part the first UI row
# (UI_TOP) sits at canvas y >= 362, below the keyword tag (y 250-346), so the tag never covers UI text: cy <= fit_cy(UI_TOP, 372, w).
def fit_cy(panel_y, canvas_y, w): return panel_y - canvas_y * w / OW + w * ASP / 2
KF = {
    1: [(0, (170, 246, 400), None), (8, (168, 300, 298), 'out3'), (56, (168, 302, 286), 'lin')],
    2: [(60, (171, 230, 342), None), (72, (171, 232, 336), 'lin'), (100, (214, 323, 260), 'io'), (120, (214, 321, 254), 'lin')],
    3: [(120, (169, 228, 338), None), (130, (169, 230, 332), 'lin'), (156, (116, 290, 200), 'io'), (180, (116, 296, 192), 'lin')],
    4: [(180, (170, 205, 320), None), (190, (170, 207, 314), 'lin'), (208, (200, 277, 230), 'io'), (226, (232, 269.5, 216), 'io'), (240, (235, 266, 210), 'lin')],
    5: [(240, (171, 206, 322), None), (252, (171, 208, 316), 'lin'), (274, (240, 261.5, 196), 'io'), (300, (248, 256, 186), 'io'), (330, (249, 254, 182), 'lin')],
    6: [(330, (169, 205, 320), None), (340, (169, 207, 314), 'lin'), (362, (230, 263.5, 200), 'io'), (390, (232, 260.5, 194), 'lin')],
    7: [(390, (170, 203, 320), None), (400, (170, 205, 314), 'lin'), (416, (113, 283, 232), 'io'), (480, (113, 280, 226), 'lin')],
    8: [(480, (171, 203, 320), None), (490, (171, 205, 314), 'lin'), (508, (200, 264, 236), 'io'), (528, (180, 253, 214), 'io'), (540, (179, 251, 210), 'lin')],
    9: [(540, (169, 300, 560), None), (600, (169, 296, 520), 'io')],     # card: panel top y~345, bottom y~1388 at the end
}
BEAT_PUNCH = [15, 30, 45]               # hook: small zoom bumps on the kick (beats 2-4 of bar 1)
# per scene: storyboard headline bottom (panel y), first protected UI row (panel y), last protected row (panel y)
HEADLINE_BOTTOM = {2: 126, 3: 120, 4: 110, 5: 117, 6: 122, 7: 107, 8: 101}
UI_ROWS = {2: (182, 229), 3: (198, 376), 4: (152, 337), 5: (155, 342), 6: (155, 340), 7: (157, 385), 8: (137, 356)}
TAG_BOX = (250, 346)                    # keyword tag, canvas y

# highlight rings: (scene, (x0, y0, x1, y1) in panel px, on, off)
RINGS = [
    (2, (107, 184, 328, 227), 98, 118),      # KPI tiles
    (3, (64, 196, 162, 346), 150, 178),      # time 08:30 + QR code
    (4, (266, 219, 321, 337), 222, 238),     # leave status column (รออนุมัติ / อนุมัติแล้ว)
    (5, (286, 220, 322, 342), 282, 328),     # OT (ชม.) column (the tab label above is garbled in the AI storyboard: not highlighted)
    (6, (226, 219, 263, 340), 366, 388),     # รวม (net pay) column
    (7, (25, 156, 202, 274), 418, 446),      # LINE notification 1
    (7, (25, 281, 202, 395), 450, 478),      # LINE notification 2
    (8, (86, 326, 246, 356), 518, 538),      # Export Excel / Export PDF
]
# short text overlays from the brief (tag at the top of the safe zone), CTA on the end card
TAGS = [(2, 'จัดการ HR ง่ายขึ้น', 'users'), (3, 'ลงเวลา', 'clock'), (4, 'ลา', 'calendar'), (5, 'OT', 'timer'), (6, 'เงินเดือน', 'coins'),
        (7, 'แจ้งเตือน LINE', 'bell'), (8, 'Report', 'chart'), (9, 'ครบในระบบเดียว', 'check')]
CTA = {'text': 'SmartFlow | LINE: @smartflow', 'on': 556}

def scene_of(t):
    for s in SCENES:
        if s[1] <= t < s[2]: return s
    return SCENES[-1] if t >= N else SCENES[0]

def cam_base(k, t):
    ks = KF[k]
    if t <= ks[0][0]: return ks[0][1]
    for a, b in zip(ks, ks[1:]):
        if a[0] <= t <= b[0]:
            e = EASE[b[2]]((t - a[0]) / (b[0] - a[0]))
            cx = a[1][0] + (b[1][0] - a[1][0]) * e; cy = a[1][1] + (b[1][1] - a[1][1]) * e
            w = math.exp(math.log(a[1][2]) + (math.log(b[1][2]) - math.log(a[1][2])) * e)     # uniform zoom speed
            return cx, cy, w
    return ks[-1][1]

def cam(k, t):
    """camera of scene k at (fractional) frame t, including hook punches and zoom-through transitions"""
    f0, f1 = next((s[1], s[2]) for s in SCENES if s[0] == k)
    cx, cy, w = cam_base(k, min(max(t, f0), f1))
    if k == 1:
        for b in BEAT_PUNCH:
            if b <= t < b + 7: w *= 1 - 0.022 * math.sin(math.pi * (t - b) / 7) * (1 - (t - b) / 7)
    if f1 in CUTS and t > f1 - OUT_LEN:                        # push in before the cut (accelerating)
        w *= 1 - 0.20 * EASE['in2'](min(1.0, (t - (f1 - OUT_LEN)) / OUT_LEN))
    if f0 in CUTS and t < f0 + IN_LEN:                         # arrive zoomed-in, settle (decelerating)
        w *= 1 - 0.18 * (1 - EASE['out3'](max(0.0, (t - f0) / IN_LEN)))
    return cx, cy, w

def layers(t):
    """[(scene k, weight)] contributing to frame t (crossfade around cuts)"""
    s = scene_of(t)
    for c in CUTS:
        if c - XF <= t < c + XF:
            a = (t - (c - XF) + 0.5) / (2 * XF)               # 0..1 across the 4 crossfade frames
            prev = scene_of(c - 1)[0]; nxt = scene_of(c)[0]
            return [(prev, 1 - a), (nxt, a)]
    return [(s[0], 1.0)]

def rect_canvas(k, t, box):
    cx, cy, w = cam(k, t); h = w * ASP; s = OW / w
    x0, y0, x1, y1 = box
    return [(x0 - (cx - w / 2)) * s, (y0 - (cy - h / 2)) * s, (x1 - x0) * s, (y1 - y0) * s]

def canvas_y(k, t, panel_y):
    cx, cy, w = cam(k, t); return (panel_y - (cy - w * ASP / 2)) * OW / w

def tag_window(k):
    """tag appears once the camera has carried the baked headline clear of the tag zone; leaves 3 frames before the cut"""
    f0, f1 = next((s[1], s[2]) for s in SCENES if s[0] == k)
    if k not in HEADLINE_BOTTOM: return f0 + 2, N + 10
    on = next(f for f in range(f0 + 6, f1) if canvas_y(k, f, HEADLINE_BOTTOM[k]) < TAG_BOX[0] - 20)
    return on, f1 - 3

def validate():
    """layout report: while a tag is up, the headline is clear of it and the protected UI rows are below it and above y 1500"""
    rep, ok = [], True
    for k, _, _ in TAGS:
        on, off = tag_window(k)
        if k not in UI_ROWS: rep.append((k, on, off, None, None, None, True)); continue
        f1 = next(s[2] for s in SCENES if s[0] == k)
        fr = range(on, min(off, f1 - OUT_LEN))
        head = max(canvas_y(k, f, HEADLINE_BOTTOM[k]) for f in fr)
        top = min(canvas_y(k, f, UI_ROWS[k][0]) for f in fr)
        bot = max(canvas_y(k, f, UI_ROWS[k][1]) for f in fr)
        good = head <= TAG_BOX[0] - 10 and top >= TAG_BOX[1] + 14 and bot <= 1500
        ok &= good; rep.append((k, on, off, round(head), round(top), round(bot), good))
    return ok, rep

# sound cues (frames): whoosh into every cut, click as the function switches, pop on every highlight (ding for the LINE
# notifications), soft digital blip when a keyword tag appears, scan beep on the QR
SFX = ([{'f': 0, 'name': 'whoosh', 'peak': -17, 'off': 0.0}] +
       [{'f': c, 'name': 'whoosh', 'peak': -18, 'off': -0.10} for c in CUTS] +
       [{'f': c + 3, 'name': 'click', 'peak': -22} for c in CUTS] +
       [{'f': r[2], 'name': 'pop', 'peak': -21} for r in RINGS if r[0] != 7] +
       [{'f': r[2], 'name': 'ding', 'peak': -19} for r in RINGS if r[0] == 7] +
       [{'f': tag_window(k)[0], 'name': 'blip', 'peak': -28} for k, _, _ in TAGS] +
       [{'f': 160, 'name': 'beep', 'peak': -24}, {'f': CTA['on'], 'name': 'pop', 'peak': -19}])

def export():
    frames = []
    for f in range(N):
        L = layers(f)
        frames.append({'f': f, 'layers': [{'k': k, 'a': round(a, 4), 'cam': [round(v, 3) for v in cam(k, f)]} for k, a in L]})
    rings = [{'k': k, 'box': box, 'on': on, 'off': off} for k, box, on, off in RINGS]
    spec = {'FPS': FPS, 'N': N, 'OW': OW, 'OH': OH, 'PANEL': PANEL, 'scenes': SCENES, 'cuts': CUTS, 'rings': rings,
            'tags': [{'k': k, 'text': t, 'icon': i, 'on': tag_window(k)[0], 'off': tag_window(k)[1]} for k, t, i in TAGS], 'cta': CTA, 'sfx': SFX, 'frames': frames}
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'spec.json')
    json.dump(spec, open(out, 'w'), ensure_ascii=False)
    sc = [OW / l['cam'][2] / 4 for fr in frames for l in fr['layers']]   # canvas px per SR px
    ok, rep = validate(); spec_layout = {'ok': ok, 'rows': rep}
    json.dump(spec_layout, open(out.replace('spec.json', 'layout.json'), 'w'))
    print(f'spec: {N} frames ({N / FPS:.2f} s), cuts {CUTS}; SR sampling scale {min(sc):.2f}..{max(sc):.2f}x; sfx {len(SFX)}')
    for k, on, off, head, top, bot, good in rep:
        print(f'  S{k} tag f{on}-{off}' + ('' if head is None else f': headline bottom <= {head}, UI rows {top}..{bot}') + ('  OK' if good else '  CHECK'))

if __name__ == '__main__':
    export()
