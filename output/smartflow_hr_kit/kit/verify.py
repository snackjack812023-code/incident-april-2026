"""Checks the exported file against the brief: format (1080x1920, 9:16, SAR 1:1, 30 fps CFR, H.264, AAC, MP4),
1 no black borders, 2 no stretching (affine fit frame->panel has equal x/y scale), 3 text inside the TikTok safe zone,
4 scenes 01-09 in order (each scene's mid-frame matches its storyboard panel best), 5 transitions + SFX on the beat,
6 duration <= 20 s.  usage: python3 verify.py file.mp4   (exit 1 on any failure)"""
import json, os, subprocess, sys
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = os.path.join(ROOT, 'work')
f = sys.argv[1]; spec = json.load(open(os.path.join(W, 'spec.json')))
res = []
def check(name, ok, detail): res.append((name, bool(ok), detail))
j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-print_format', 'json', '-show_streams', '-show_format', f], capture_output=True, text=True).stdout)
v = next(s for s in j['streams'] if s['codec_type'] == 'video'); a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
fr = lambda s: (lambda n, d: n / d)(*map(float, s.split('/')))
dur = float(j['format']['duration']); vdur = float(v.get('duration', dur)); adur = float(a.get('duration', 0)) if a else 0
check('resolution 1080x1920', v['width'] == 1080 and v['height'] == 1920, f"{v['width']}x{v['height']}")
check('aspect 9:16, SAR 1:1', v.get('sample_aspect_ratio', '1:1') == '1:1' and v['width'] * 16 == v['height'] * 9, f"DAR {v.get('display_aspect_ratio')} SAR {v.get('sample_aspect_ratio')}")
check('30 fps CFR', abs(fr(v['r_frame_rate']) - 30) < 1e-6 and abs(fr(v['avg_frame_rate']) - 30) < 1e-3, f"{v['r_frame_rate']} / {v['avg_frame_rate']}")
check('H.264 / MP4', v['codec_name'] == 'h264' and 'mp4' in j['format']['format_name'], f"{v['codec_name']} {v.get('profile')} L{v.get('level')} {v.get('pix_fmt')}")
check('audio AAC', bool(a) and a['codec_name'] == 'aac', f"{a['codec_name']} {a['sample_rate']} Hz {a['channels']}ch" if a else 'missing')
# decode all frames once (RGB)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, 1920, 1080, 3)
# 1 black borders: thickness of any contiguous near-black band (>= 95% of pixels with max channel <= 12) at a frame edge
def band(lines):
    n = 0
    for ln in lines:
        if (ln.reshape(-1, 3).max(axis=1) <= 12).mean() >= 0.95: n += 1
        else: break
    return n
worst = (0, None)
for i, im in enumerate(frames):
    for name, lines in (('top', im[:24]), ('bottom', im[::-1][:24]), ('left', im.transpose(1, 0, 2)[:24]), ('right', im.transpose(1, 0, 2)[::-1][:24])):
        t = band(lines)
        if t > worst[0]: worst = (t, f'frame {i} {name}')
check('1 no black borders', worst[0] < 4, f'thickest near-black edge band: {worst[0]} px' + (f' ({worst[1]})' if worst[1] else '') + f' over {len(frames)} frames, 4 edges')
# 2 no stretching: fit a full affine from an SR panel to the plate frame of a hold, compare x/y scale
plate = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(W, 'plate.mkv'), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
pf = np.frombuffer(plate, np.uint8).reshape(-1, 1920, 1080, 3)
orb = cv2.ORB_create(4000); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
ratios = []
for k, f0, f1 in spec['scenes']:
    t = (f0 + f1) // 2 if k != 1 else 40
    pan = cv2.imread(os.path.join(W, f'sr_p{k}.png'), cv2.IMREAD_GRAYSCALE); g = cv2.cvtColor(pf[t], cv2.COLOR_RGB2GRAY)
    k1, d1 = orb.detectAndCompute(pan, None); k2, d2 = orb.detectAndCompute(g, None)
    m = sorted(bf.match(d1, d2), key=lambda x: x.distance)[:600]
    A, inl = cv2.estimateAffine2D(np.float32([k1[x.queryIdx].pt for x in m]), np.float32([k2[x.trainIdx].pt for x in m]), ransacReprojThreshold=2.0)
    sx, sy = np.hypot(A[0, 0], A[1, 0]), np.hypot(A[0, 1], A[1, 1]); ratios.append((k, sx / sy, int(inl.sum())))
dev = max(abs(r - 1) for _, r, _ in ratios)
check('2 no stretching (uniform scale)', dev < 0.01, 'x/y scale ratio per scene: ' + ', '.join(f'S{k} {r:.4f}' for k, r, _ in ratios))
# 3 safe zone (overlay layout check written by render_overlay.js)
sz = json.load(open(os.path.join(W, 'safezone.json')))
check('3 text inside TikTok safe zone', sz['bad'] == 0, f"{len(sz['report'])} text boxes checked, outside: {sz['bad']} (zone x {sz['SAFE']['left']}-{sz['SAFE']['right']}, y {sz['SAFE']['top']}-{sz['SAFE']['bottom']}, right rail x>{sz['SAFE']['railX']})")
lay = json.load(open(os.path.join(W, 'layout.json')))
check('3b text overlays never cover UI rows', lay['ok'], '; '.join(f"S{k}: tag f{on}-{off}" + ('' if top is None else f" UI {top}-{bot}px") for k, on, off, head, top, bot, g in lay['rows']))
# 4 scene order: correlate each scene's mid-frame (final video) against all 9 panels rendered through that frame's camera
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
order = []
for k, f0, f1 in spec['scenes']:
    t = (f0 + f1) // 2; cam = next(l['cam'] for l in spec['frames'][t]['layers'] if l['k'] == k)
    vid = cv2.resize(frames[t], (135, 240), interpolation=cv2.INTER_AREA).astype(np.float32)
    scores = []
    for c in range(1, 10):
        ref = cv2.cvtColor(np.clip(R.panel(c).view(tuple(cam)), 0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
        ref = cv2.resize(ref, (135, 240), interpolation=cv2.INTER_AREA).astype(np.float32)
        x, y = vid - vid.mean(), ref - ref.mean(); scores.append(float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum())))
    order.append(int(np.argmax(scores)) + 1)
check('4 scenes 01-09 in order', order == list(range(1, 10)), f'best-matching panel per scene: {order}')
# 5 sync: every cut on the 120 BPM grid, with a whoosh leading it and a click right after
cues = json.load(open(os.path.join(W, 'sfx_cues.json')))
ok5 = True; det = []
for c in spec['cuts']:
    on_beat = (c % 15) == 0
    wh = [q for q in cues if q['name'] == 'whoosh' and q['frame'] == c]; ck = [q for q in cues if q['name'] == 'click' and q['frame'] == c + 3]
    ok5 &= on_beat and bool(wh) and bool(ck); det.append(f'{c / 30:.1f}s')
check('5 transitions on the beat + SFX in sync', ok5, f"cuts at {', '.join(det)} (all multiples of 0.5 s = 120 BPM beats); whoosh {abs(cues[1]['t'] - spec['cuts'][0] / 30):.3f} s before each cut, click 0.1 s after")
# 6 duration
check('6 duration <= 20 s', dur <= 20.0005 and vdur <= 20.0005 and adur <= 20.0005, f'container {dur:.3f} s, video {vdur:.3f} s ({v.get("nb_read_frames")} frames), audio {adur:.3f} s')
ok = True
for n, p, d in res: ok &= p; print(('PASS' if p else 'FAIL').ljust(5), n.ljust(38), d)
print(f"size {os.path.getsize(f) / 1048576:.2f} MB, video {int(v['bit_rate']) / 1e6:.2f} Mbps, audio {int(a['bit_rate']) / 1e3:.0f} kbps")
sys.exit(0 if ok else 1)
