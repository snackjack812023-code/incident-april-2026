# LINE alert demo — TikTok re-edit build kit

Rebuilds `output/line_alert_tiktok.mp4` (9:16, 1080x1920, 30 fps, H.264 High + AAC 256k, 16.5 s) from the uploaded clip
(576x1024, phone footage of the "ส่งแจ้งเตือน LINE" feature) and the clip's cover image (`src/cover.png`).

```bash
SRC_VIDEO=/path/to/clip.mp4 ./build.sh
```

Edit (output seconds): 0–2 hook (payoff first: the LINE message on the phone + title styled like the cover) · 2–4 step 1 click
"ส่งแจ้งเตือน LINE" · 4–6.5 step 2 check the message, click "ยืนยันส่ง" (1.33x) · 6.5–8 step 3 success · 8–12.3 tilt to the
phone (2x, frame-blended), the message card is tracked and highlighted · 12.3–15 CTA "ทัก LINE: @smartflow" · 15–16.5 cover poster
(pick it as the TikTok cover). Dead time removed: loading spinner, idle cursor, the slow hand-held move down to the phone.

| Step | File | What it does |
|---|---|---|
| 1 | `kit/prep.py` | deblock + denoise + vid.stab stabilisation → lossless `clean.mkv`; phase-correlation track of the message card |
| 2 | `kit/edit.py` | shot list, speed ramps, camera keyframes, highlight targets, sound cues → `work/edit.json` |
| 3 | `kit/render.py` | per-shot white balance (blue monitor cast removed), single-pass Lanczos crop/upscale, zoom-through motion blur, CTA dim, cover |
| 4 | `gfx/render_overlay.js` | hook title, step captions, green rings, click ripples, "ข้อความใหม่" badge, CTA (Chromium → PNG, safe-area check) |
| 5 | `kit/music.py` | original 120 BPM tech-pop bed (synthesised; the clip's song is not reused) |
| 6 | `kit/make_audio.py` | whoosh / click / success chime / message ding / pop under the music (−14 LUFS, peak −1 dBFS) |
| 7 | `kit/final.py`, `kit/verify.py` | RGB composite → BT.709 → x264 CRF 14 (keeps the file under 30 MB), ffprobe checks |
