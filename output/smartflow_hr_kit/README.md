# SmartFlow HR & Time Attendance — TikTok build kit

Rebuilds `output/SmartFlow_HR_TikTok_Final.mp4` (9:16, 1080x1920, 30 fps, H.264 High + AAC 256k, 20.0 s) from the nine
storyboard images in `src/` (scenes 01–09, 941x1672 each). Every picture element comes from those images: the camera only
crops, zooms and pans them (uniform scale, no stretching); nothing in the artwork is redrawn.

```bash
./build.sh            # or IMAGES=/folder/with/s1.png..s9.png ./build.sh
```

| Step | File | What it does |
|---|---|---|
| 1 | `kit/prep.py`, `kit/sr.py` | removes the storyboard's "1 · 0:00-0:02" badges (masked inpaint of the bokeh), 4x super-resolution with Real-ESRGAN general-x4v3 run in plain NumPy (no PyTorch) so Thai text stays sharp when zoomed |
| 2 | `kit/spec.py` | timeline: scenes at 0-2-4-6-8-11-13-16-18-20 s (cuts on a 120 BPM grid), camera keyframes, highlights, keyword-tag windows, SFX cues; validates that tags never cover the headline or UI and that every highlighted element sits inside the TikTok safe zone (incl. the right action rail) |
| 3 | `kit/render.py` | renders each frame from a mip pyramid of the 4x images (Lanczos, never upscaled), zoom-through transitions (0.33 s) with motion blur only on the transitions; headline shots are framed below TikTok's top tabs; closing scene = end card with every line inside the safe zone |
| 4 | `gfx/render_overlay.js` | keyword tags (จัดการ HR ง่ายขึ้น / ลงเวลา / ลา / OT / เงินเดือน / แจ้งเตือน LINE / Report / ครบในระบบเดียว), yellow focus rings, green ring on the LINE CTA; checks every tag on every frame against the safe zone |
| 5 | `kit/music.py` | original 120 BPM modern-tech bed (tense hook → drop on the reveal at 2.0 s → groove → build → calm close) |
| 6 | `kit/make_audio.py` | whoosh / click / pop / LINE ding / digital beep & blip, ~14 dB under the music |
| 7 | `kit/final.py`, `kit/verify.py` | RGB composite → BT.709 → x264 CRF 16; checks: format, no black borders, no stretching, safe zone, overlays vs UI, scene order 01-09, beat sync, duration ≤ 20 s |
