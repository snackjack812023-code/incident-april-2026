"""Timeline for SmartFlow HR & Time Attendance TikTok v2 (9 storyboard images, 20.0 s, 30 fps, cuts on a 120 BPM grid).
Geometry in 1x image px (each image ~941x1672, already 9:16); the renderer samples 4x super-resolved images.
Camera = (cx, cy, w): the 9:16 window is w wide and w*16/9 tall. Writes work/spec.json + work/layout.json."""
import json, math, os

FPS, N = 30, 600
OW, OH = 1080, 1920
ASP = OH / OW
IMG = {k: (941, 1672) for k in range(1, 10)}
SCENES = [(1, 0, 60), (2, 60, 120), (3, 120, 180), (4, 180, 240), (5, 240, 330), (6, 330, 390), (7, 390, 480), (8, 480, 540), (9, 540, 600)]
CUTS = [s[1] for s in SCENES[1:]]
OUT_LEN, IN_LEN, XF = 4, 6, 2          # zoom-through: 4 frames push-in before a cut, 6 frames settle after, 2+2 frames crossfade
SAFE = dict(top=220, bottom=1500, left=40, right=1040, rail_x=960, rail_y=950)   # TikTok UI-free zone used by the checks
TAG_Y = (250, 346)                     # keyword tag band (canvas y)

def _io(p): return 0.5 - 0.5 * math.cos(math.pi * p)
EASE = {'lin': lambda p: p, 'io': _io, 'out3': lambda p: 1 - (1 - p) ** 3, 'in2': lambda p: p * p}
def C(u, v, w): return (u + w / 2, v + w * ASP / 2, w)          # camera from its top-left corner
FULL = 941.0

# per scene: headline box (x0, y0, x1, y1) and the protected UI block (x0, y0, x1, y1) in image px
HEAD = {1: (55, 955, 895, 1325), 2: (59, 196, 901, 437), 3: (120, 167, 914, 423), 4: (30, 195, 905, 487), 5: (30, 164, 870, 452),
        6: (30, 181, 870, 447), 7: (38, 144, 914, 425), 8: (70, 161, 858, 419), 9: (57, 96, 914, 436)}
UI = {2: (329, 560, 878, 849), 3: (210, 620, 545, 1068), 4: (314, 606, 905, 1100), 5: (298, 589, 892, 1038), 6: (286, 573, 848, 1012),
      7: (60, 555, 594, 1198), 8: (250, 511, 860, 1030), 9: (47, 1127, 906, 1515)}

# opening framing of scenes 2-8: full width, shifted down so the headline clears TikTok's top tabs (headline top >= 228 px)
def opening(k):
    v = min(0.0, HEAD[k][1] - 228 / (OW / FULL))
    return C(0, v, FULL)

KF = {
    # S1 hook: crash zoom from an end-card size straight onto the problem headline, then beat punches
    1: [(0, C(-104.5, -186.2, 1150), None), (8, C(30, 1672 - 890 * ASP, 890), 'out3'), (56, C(40, 1672 - 870 * ASP, 870), 'lin')],
    2: [(60, opening(2), None), (72, C(8, opening(2)[1] - 836.4 + 4, 925), 'lin'),
        (94, C(303.5, 356, 600), 'io'), (120, C(305.5, 361, 596), 'lin')],
    3: [(120, opening(3), None), (132, C(8, opening(3)[1] - 836.4 + 4, 925), 'lin'),
        (150, C(117, 440, 520), 'io'), (180, C(132, 458, 480), 'lin')],
    4: [(180, opening(4), None), (192, C(8, opening(4)[1] - 836.4 + 4, 925), 'lin'),
        (210, C(300, 420, 520), 'io'), (228, C(460, 426.2, 515), 'io'), (240, C(466, 436, 505), 'lin')],
    5: [(240, opening(5), None), (254, C(8, opening(5)[1] - 836.4 + 4, 925), 'lin'),
        (274, C(297, 380, 600), 'io'), (300, C(478, 422, 480), 'io'), (330, C(488, 432, 470), 'lin')],
    6: [(330, opening(6), None), (342, C(8, opening(6)[1] - 836.4 + 4, 925), 'lin'),
        (360, C(270, 380, 560), 'io'), (390, C(283.5, 391, 545), 'lin')],
    7: [(390, opening(7), None), (402, C(8, opening(7)[1] - 836.4 + 4, 925), 'lin'),
        (420, C(50, 350, 620), 'io'), (480, C(56, 353, 610), 'lin')],
    8: [(480, opening(8), None), (492, C(8, opening(8)[1] - 836.4 + 4, 925), 'lin'),
        (510, C(232, 288, 640), 'io'), (540, C(232, 302, 600), 'lin')],
    # S9 closing: the whole end card (headline + features + LINE CTA) inside the safe zone, slow zoom in
    9: [(540, C(470.5 - 620, 1515 - 1475 / (OW / 1240), 1240), None), (600, C(470.5 - 575, 1515 - 1490 / (OW / 1150), 1150), 'lin')],
}
BEAT_PUNCH = [15, 30, 45]               # hook: small zoom bumps on the kick (beats 2-4 of bar 1)
EXT_STYLE = {1: 'card', 9: 'card'}      # how the area outside the image looks when the camera shows it (default 'seamless')

# highlight rings: (scene, (x0, y0, x1, y1), on, off, colour)
RINGS = [
    (2, (329, 628, 878, 738), 97, 118, 'yellow'),      # KPI: พนักงานทั้งหมด / เข้างานวันนี้ / ลาวันนี้
    (3, (210, 620, 545, 760), 150, 163, 'yellow'),     # time 08:30 + date
    (3, (220, 790, 485, 1068), 165, 178, 'yellow'),    # QR code
    (4, (762, 795, 906, 1095), 227, 238, 'yellow'),    # leave status column (รออนุมัติ / อนุมัติแล้ว / ไม่อนุมัติ)
    (5, (484, 587, 670, 650), 272, 292, 'yellow'),     # "คำนวณอัตโนมัติ" tab
    (5, (768, 684, 892, 1038), 300, 328, 'yellow'),    # OT (ชม.) column
    (6, (452, 573, 615, 630), 356, 368, 'yellow'),     # "สรุปเงินเดือน" tab
    (6, (630, 665, 725, 1012), 368, 388, 'yellow'),    # รวม (net pay) column
    (7, (104, 630, 591, 908), 420, 444, 'yellow'),     # LINE notification: check-in
    (7, (116, 924, 594, 1198), 450, 478, 'yellow'),    # LINE notification: leave request
    (8, (256, 964, 660, 1030), 520, 538, 'yellow'),    # Export Excel / Export PDF
    (9, (45, 1337, 902, 1517), 574, 610, 'green'),     # CTA: ทักเลยที่ LINE : @smartflow
]
# keyword overlays from the brief; 'anchor' pins a tag to an image point (scene 9: on the laptop base, clear of the phone)
TAGS = [(2, 'จัดการ HR ง่ายขึ้น', 'users', None), (3, 'ลงเวลา', 'clock', None), (4, 'ลา', 'calendar', None), (5, 'OT', 'timer', None),
        (6, 'เงินเดือน', 'coins', None), (7, 'แจ้งเตือน LINE', 'bell', None), (8, 'Report', 'chart', None),
        (9, 'ครบในระบบเดียว', 'check', (318, 1062))]

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
    """camera of scene k at (fractional) frame t, incl. hook punches and zoom-through transitions"""
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
            a = (t - (c - XF) + 0.5) / (2 * XF)
            return [(scene_of(c - 1)[0], 1 - a), (scene_of(c)[0], a)]
    return [(s[0], 1.0)]

def to_canvas(k, t, x, y):
    cx, cy, w = cam(k, t); s = OW / w
    return (x - (cx - w / 2)) * s, (y - (cy - w * ASP / 2)) * s

def box_canvas(k, t, b):
    x0, y0 = to_canvas(k, t, b[0], b[1]); x1, y1 = to_canvas(k, t, b[2], b[3]); return x0, y0, x1, y1

def tag_window(k):
    """top tags appear once the camera has carried the baked headline clear of the tag band; leave 3 frames before the cut"""
    f0, f1 = next((s[1], s[2]) for s in SCENES if s[0] == k)
    anchored = next(t[3] for t in TAGS if t[0] == k) is not None
    if anchored: return f0 + 8, N + 10
    on = next(f for f in range(f0 + IN_LEN, f1) if box_canvas(k, f, HEAD[k])[3] < TAG_Y[0] - 16)
    return on, f1 - 3

def validate():
    """per scene: tag clear of the headline; UI block below the tag and inside the safe zone while the tag is up;
    every highlighted element inside the safe zone (incl. TikTok's right action rail) while its ring is on"""
    rows, ok = [], True
    for k, text, icon, anchor in TAGS:
        on, off = tag_window(k); f1 = next(s[2] for s in SCENES if s[0] == k)
        fr = range(on, min(off, f1 - OUT_LEN))
        if anchor is None:
            head = max(box_canvas(k, f, HEAD[k])[3] for f in fr)
            ui = [box_canvas(k, f, UI[k]) for f in fr]
            top, bot = min(b[1] for b in ui), max(b[3] for b in ui)
            good = head <= TAG_Y[0] - 10 and top >= TAG_Y[1] + 10 and bot <= SAFE['bottom']
            rows.append({'scene': k, 'tag': text, 'on': on, 'off': off, 'headline_bottom': round(head), 'ui_top': round(top), 'ui_bottom': round(bot), 'ok': good})
        else:
            good = True; rows.append({'scene': k, 'tag': text, 'on': on, 'off': off, 'anchored': anchor, 'ok': True})
        ok &= good
    rings = []
    for k, b, on, off, col in RINGS:
        f1 = next(s[2] for s in SCENES if s[0] == k); worst = []
        for f in range(on, min(off, f1 - OUT_LEN)):
            x0, y0, x1, y1 = box_canvas(k, f, b)
            right_lim = SAFE['rail_x'] if y1 > SAFE['rail_y'] else SAFE['right']
            worst.append(max(0, SAFE['left'] - x0, x1 - right_lim, SAFE['top'] - y0, y1 - SAFE['bottom']))
        w_ = max(worst) if worst else 0; good = w_ <= 6
        ok &= good; rings.append({'scene': k, 'box': b, 'on': on, 'off': off, 'outside_px': round(w_, 1), 'ok': good})
    return ok, rows, rings

SFX = ([{'f': 0, 'name': 'whoosh', 'peak': -17, 'off': 0.0}] +
       [{'f': c, 'name': 'whoosh', 'peak': -18, 'off': -0.10} for c in CUTS] +
       [{'f': c + 3, 'name': 'click', 'peak': -22} for c in CUTS] +
       [{'f': r[2], 'name': 'pop', 'peak': -21} for r in RINGS if r[0] != 7] +
       [{'f': r[2], 'name': 'ding', 'peak': -19} for r in RINGS if r[0] == 7] +
       [{'f': 165, 'name': 'beep', 'peak': -24}])

def export():
    tags = []
    for k, text, icon, anchor in TAGS:
        on, off = tag_window(k); tags.append({'k': k, 'text': text, 'icon': icon, 'on': on, 'off': off, 'anchor': anchor})
    sfx = SFX + [{'f': t['on'], 'name': 'blip', 'peak': -28} for t in tags]
    frames = []
    for f in range(N):
        frames.append({'f': f, 'layers': [{'k': k, 'a': round(a, 4), 'cam': [round(v, 3) for v in cam(k, f)]} for k, a in layers(f)]})
    rings = [{'k': k, 'box': b, 'on': on, 'off': off, 'color': col} for k, b, on, off, col in RINGS]
    spec = {'FPS': FPS, 'N': N, 'OW': OW, 'OH': OH, 'scenes': SCENES, 'cuts': CUTS, 'rings': rings, 'tags': tags,
            'tag_y': TAG_Y, 'safe': SAFE, 'sfx': sfx, 'frames': frames}
    work = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')
    json.dump(spec, open(os.path.join(work, 'spec.json'), 'w'), ensure_ascii=False)
    ok, rows, ringrep = validate()
    json.dump({'ok': ok, 'tags': rows, 'rings': ringrep}, open(os.path.join(work, 'layout.json'), 'w'), ensure_ascii=False, indent=1)
    sc = [OW / l['cam'][2] for fr in frames for l in fr['layers']]
    print(f'spec: {N} frames ({N / FPS:.2f} s), cuts {CUTS}; image scale {min(sc):.2f}..{max(sc):.2f}x; sfx {len(sfx)}; layout {"OK" if ok else "CHECK"}')
    for r in rows: print('  tag', r)
    for r in ringrep:
        if not r['ok']: print('  ring outside safe zone:', r)

if __name__ == '__main__':
    export()
