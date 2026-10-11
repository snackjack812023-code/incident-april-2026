# SmartFlow HR & Time Attendance — TikTok build kit

Rebuilds `output/SmartFlow_HR_TikTok_Final.mp4` (9:16, 1080x1920, 30 fps, H.264 High + AAC 256k, 20.0 s) from the 9-scene
storyboard image (`src/storyboard.png`). Every picture element comes from the storyboard: the camera only crops, zooms and
pans the panels (uniform scale, no stretching); nothing in the artwork is redrawn.

```bash
./build.sh            # or STORYBOARD=/path/storyboard.png ./build.sh
```

| Step | File | What it does |
|---|---|---|
| 1 | `kit/prep.py`, `kit/sr.py` | cuts the 9 panels at the white gutters, removes the storyboard's "1 · 0:00-0:02" badges (masked inpaint), 4x super-resolution with Real-ESRGAN general-x4v3 run in plain NumPy (no PyTorch) so Thai text stays sharp |
| 2 | `kit/spec.py` | timeline: scenes at 0-2-4-6-8-11-13-16-18-20 s (cuts on a 120 BPM grid), camera keyframes per scene, highlight rings, keyword-tag windows, SFX cues; validates that tags never cover UI rows |
| 3 | `kit/render.py` | renders each frame from the SR panels (Lanczos), soft-focus extension of the same panel instead of black bars, zoom-through transitions (0.33 s) with motion blur only on the transitions |
| 4 | `gfx/render_overlay.js` | keyword tags (จัดการ HR ง่ายขึ้น / ลงเวลา / ลา / OT / เงินเดือน / แจ้งเตือน LINE / Report / ครบในระบบเดียว), yellow focus rings, end-card CTA; TikTok safe-zone check |
| 5 | `kit/music.py` | original 120 BPM modern-tech bed (tense hook → drop on the reveal at 2.0 s → groove → calm close) |
| 6 | `kit/make_audio.py` | whoosh / click / pop / LINE ding / digital beep & blip under the music (SFX peaks ≈ 14 dB below the music) |
| 7 | `kit/final.py`, `kit/verify.py` | RGB composite → BT.709 → x264 CRF 14; checks: format, no black borders, no stretching, safe zone, tags vs UI, scene order 01-09, beat sync, duration ≤ 20 s |

Note: the storyboard is an AI-generated image; some small UI labels inside it are garbled (e.g. the dashboard title, a few
menu items, the OT tab label). They are kept as they are (no new UI/text is created) and the focus rings avoid them.
