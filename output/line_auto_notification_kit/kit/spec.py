"""SmartFlow "LINE auto-notification" TikTok/Reels (17.0 s, 1080x1920, 30 fps): timeline, text, camera, sound cues.
The edit keeps the original recording in order and in real time (output second = source second): the hand-held phone
showing the LINE group (0-7.6 s), the new status card arriving at 7.61 s (frame 456), the move to the office worker
(10-11.5 s) and her showing the phone (11.5-17 s). Nothing on the LINE screen is changed; the text sits on frosted
panels outside the card. Writes work/items.json for gfx/render.js."""
import json, os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = os.path.join(ROOT, 'work')
FPS, OW, OH, DUR = 30, 1080, 1920, 17.0
N = int(round(DUR * FPS))
PTS = np.array([float(l.strip().strip(',')) for l in open(os.path.join(W, 'pts.txt')) if l.strip()])
ARRIVE = float(PTS[456])                       # the LINE card appears (source frame 456)

# TikTok/Reels safe area: top bar < 200, caption/music > 1560, action rail x > 960 for y 860-1650
TOP_Y, BOTTOM_Y = 262, 1528                    # top edge of top panels / bottom edge of bottom panels
GROUPS = {   # id: (anchor, centre x, max text width)
    'hookA': ('top', 540, 900), 'hookB': ('top', 540, 900), 'build': ('top', 540, 900), 'hero': ('top', 540, 900),
    'proof': ('bottom', 505, 800), 'cta1': ('bottom', 505, 800), 'cta2': ('bottom', 505, 800),
}
ARROW = '{ARROW}'
MAXW = {}                     # per-item width overrides
ITEMS = [   # id, group, t_in, t_out, html, size, weight
    ('hook1', 'hookA', -0.08, 0.92, 'อัปเดตงานแล้ว...', 84, 800),                    # big, on the very first frame
    ('hook2', 'hookB', 0.92, 2.15, 'ต้อง<span class="em">พิมพ์</span>แจ้งใน LINE', 76, 800),
    ('hook3', 'hookB', 1.04, 2.15, '<span class="em">เอง</span>ทุกครั้ง?', 76, 800),
    ('build1', 'build', 2.20, 6.75, 'ถ้าให้ระบบแจ้งให้<span class="c">อัตโนมัติ</span>ล่ะ?', 68, 800),
    ('build2', 'build', 2.55, 6.75, f'<span class="dim">เปลี่ยนสถานะงาน</span>{ARROW}<span class="dim">แจ้ง</span> <span class="g">LINE</span>', 46, 600),
    ('hero1', 'hero', ARRIVE + 0.15, 9.85, 'แจ้งเตือนเข้า <span class="g">LINE</span> อัตโนมัติ! 🔔', 70, 800),
    ('hero2', 'hero', ARRIVE + 0.55, 9.85, '<span class="dim">ไม่ต้องคอยพิมพ์แจ้งเอง</span>', 46, 600),
    ('proof1', 'proof', 11.00, 13.90, 'ทีมรู้สถานะงาน<span class="y">ทันที</span>', 70, 800),
    ('proof2', 'proof', 11.35, 13.90, '<span class="c">Real-Time</span><span class="dot">•</span><span class="c">Automatic</span>'
                                      '<span class="dot">•</span>ลดงานซ้ำ', 42, 600),
    ('cta1', 'cta1', 14.00, 15.55, 'อยากทำระบบแบบนี้ไหม?', 72, 800),
    ('cta2', 'cta1', 14.45, 15.55, '<span class="c">Google Apps Script</span> + <span class="g">LINE</span>', 50, 700),
    ('cta3', 'cta2', 15.65, DUR + 1, 'ติดตามไว้ เดี๋ยวคลิปหน้าสอนทำ 👇', 58, 800),
    ('brand', 'cta2', 15.95, DUR + 1, '<span class="brand"><b>SmartFlow</b> <span class="dim">| @smartflow</span></span>', 38, 600),
]
PAD_X, PAD_Y, GAP = 40, 22, 4

# camera: zoom keys (t, z, easing to this key); the centre follows tracked content (see render.py)
ZOOM = [(0.00, 1.00, None), (0.35, 1.10, 'out'), (7.55, 1.22, 'inout'), (ARRIVE, 1.22, None), (ARRIVE + 0.53, 1.62, 'inout3'),
        (9.95, 1.68, 'lin'), (10.55, 1.00, 'inout3'), (14.00, 1.10, 'inout'), (DUR, 1.16, 'lin')]
CHAT_ANCHOR, CARD_ANCHOR = (540, 1000), (540, 1080)       # where the tracked point sits on the output frame
FIXED_C = (505, 905)                                       # her shots: a slow push towards the phone she holds
DRIFT_BUILD = (0, 110)                                     # build-up: the centre drifts towards the bottom of the chat

# sound cues (s): whoosh on the hook, UI click when the question appears, the notification on the card's arrival,
# transition whoosh into her shot, soft pop on the CTA; the music dips ~37% (-4 dB) around the notification
SFX = {'whoosh_in': 0.0, 'click': 2.20, 'notify': ARRIVE, 'whoosh_tr': 9.92, 'pop': 14.0}
DUCK = (ARRIVE - 0.05, ARRIVE + 0.75, ARRIVE + 1.25, -4.0)  # start, hold until, back to full by, depth dB

if __name__ == '__main__':
    items = [{'id': i, 'html': h, 'size': s, 'weight': w, 'maxw': MAXW.get(i, GROUPS[g][2]), 'cls': ''} for i, g, a, b, h, s, w in ITEMS]
    json.dump(items, open(os.path.join(W, 'items.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'{len(items)} text items; card arrives at {ARRIVE:.3f} s; {N} frames')
