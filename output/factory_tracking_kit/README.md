# Factory Production Tracking — TikTok promo build kit

Rebuilds `output/factory_production_tracking_tiktok.mp4` (9:16, 1080x1920, 30 fps, H.264 High + AAC 256k, 21.0 s) from the
seven original screenshots of the web app. Every UI pixel comes from the screenshots: the camera only crops / zooms / pans them
(sub-pixel Lanczos), nothing in the UI is redrawn.

```bash
SHOTS=/path/to/screenshots ./build.sh      # folder with dashboard / calendar / po / board / dept / delivery / report .png
```

| Step | File | What it does |
|---|---|---|
| 1 | `kit/spec.py` | timeline: 9 scenes, cuts on a 120 BPM beat grid, camera keyframes (holds stay sharp, quick moves get motion blur), spotlight targets, SFX cue list → `work/spec.json` |
| 2 | `kit/render_plate.py` | blurred + navy-tinted screenshot background, floating card with shadow/glow, camera crops with temporal-supersampled motion blur, zoom-through transitions → lossless FFV1 |
| 3 | `gfx/render_overlay.js` | Thai headlines (Prompt font, auto-fit, TikTok safe area check), spotlight rings, status chips, closing title + CTA (Chromium → PNG sequence) |
| 4 | `kit/music.py` | original 120 BPM corporate / tech track synthesised from scratch (kick, clap, hats, off-beat bass, supersaw pads, pluck arp, risers, impact) |
| 5 | `kit/make_audio.py` | whoosh / click / pop SFX mixed under the music (−14 LUFS mix, peaks −1 dBFS) |
| 6 | `kit/final.py`, `kit/verify.py` | RGB composite → BT.709 → x264 CRF 12, ffprobe checks |

Browser bar (web-app URL) and Windows taskbar are never in frame: crops stay inside the app area (y 88–1032).
