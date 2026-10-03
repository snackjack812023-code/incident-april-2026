# SmartFlow TikTok clip — build kit

Rebuilds `output/smartflow_quotation_tiktok.mp4` ("สร้างใบเสนอราคาอัตโนมัติด้วย Google Apps Script", 9:16, 1080x1920, 30 fps, H.264/AAC, 14.97 s).

```bash
SRC_B=/path/20261003_210036.mp4 SRC_C=/path/20261003_210121.mp4 ./build.sh
```

Requirements: ffmpeg/ffprobe ≥ 6 (libx264), Node ≥ 18 with Playwright + Chromium (set `NODE_PATH` if installed globally), npm
(downloads the OFL-licensed **Prompt** font from `@fontsource/prompt` for the Thai text).

| Step | File | What it does |
|---|---|---|
| 1 | `kit/make_reel.js` | cuts the footage into a 449-frame/30 fps reel (hold frames, 1.2x travel, ping-pong end card) |
| 2 | `gfx/render_chrome.js` | card mask, border, shadow/glow (Chromium → PNG) |
| 3 | `kit/run_plate.js` + `kit/plate.js` | blurred background from the footage, perspective-corrected screen card (keystone fix), de-moiré, white-point, smooth/punch zoom (sub-pixel, `perspective` filter) |
| 4 | `gfx/render_overlay.js` | Thai text, step pills, highlight rings, click ripples (PNG sequence) |
| 5 | `kit/make_sfx.js` | click / key / whoosh / pop / success SFX synthesised with FFmpeg lavfi (no external audio) |
| 6 | `kit/final.js`, `kit/verify.js` | overlay + audio → MP4, ffprobe checks |

Timeline, crops and sound events live in `kit/spec.js` (frame numbers at 30 fps).
Source clips used: `…210036.mp4` (hook, 3 steps, click, PDF saved) and `…210121.mp4` (generated quotation viewer, end card). `…205730.mp4` is not used (different customer/document).

**Privacy:** the Apps Script web-app URL (deployment id) is visible in the browser bar during the first second of the wide shot; `plate.js` blurs it through a slanted mask (`gfx/chrome.html?m=urlmask`). The quotation itself still shows the company phone / LINE / e-mail / tax id exactly as on the original document.

**Background music:** none is mixed unless you drop a *licensed* audio file (mp3/wav/m4a/aac/flac/ogg) in the repo root or in `./music/` — `final.js` then adds it at −24 dB with fades and SFX ducking. No music was available in the folder for the delivered render.
