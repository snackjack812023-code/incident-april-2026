# SmartFlow TikTok clip — build kit (v7)

Rebuilds `output/smartflow_quotation_tiktok.mp4` ("สร้างใบเสนอราคาอัตโนมัติด้วย Google Apps Script", 9:16, 1080x1920, 30 fps, H.264/AAC, 14.97 s).

v7 is built only from crisp sources — two full-HD screenshots of the quotation editor and the generated quotation PDF — instead of
phone-camera footage of the monitor (which looked blocky after TikTok's re-encode). Typing, cursor, hover and click are animated over
the real screenshots: every UI pixel shown comes from the screenshots/PDF.

```bash
SHOT_ITEMS=/path/4.png SHOT_HEADER=/path/5.png PDF=/path/QT-20261003-01.pdf ./build.sh
```

Requirements: ffmpeg/ffprobe ≥ 6 (libx264), pdfimages (poppler-utils), Python 3 with Pillow + NumPy, Node ≥ 18 with Playwright +
Chromium (set `NODE_PATH` if installed globally), npm (downloads the OFL-licensed **Prompt** font from `@fontsource/prompt`).

| Step | File | What it does |
|---|---|---|
| 1 | `kit7/prep.py` | blurs the browser URL, extracts the PDF page image (flattened on white, top part only), redacts tax ID + bank account, builds the "empty form" states and the blurred backgrounds |
| 2 | `kit7/spec7.js` | the timeline: per-frame camera (smooth / punch zoom), cursor path, keystrokes, highlight rings, SFX events → `work/spec7.json` |
| 3 | `gfx7/render_chrome7.js` | card + paper masks, shadows, borders, background glows (Chromium → PNG) |
| 4 | `kit7/render_plate.py` | renders every frame (live typing from the real glyphs, caret, button hover/press, sub-pixel Lanczos crops) → lossless FFV1 |
| 5 | `gfx7/render_overlay7.js` | Thai text, step pills, cursor (arrow / I-beam / hand), rings, click ripples (PNG sequence, safe-area check) |
| 6 | `kit7/make_sfx7.js` | click / key / whoosh / pop / success SFX synthesised with FFmpeg lavfi (no external audio) |
| 7 | `kit7/final7.js`, `kit7/verify.js` | RGB composite → one BT.709 conversion → MP4 (x264 CRF 12, AAC 256k), ffprobe checks |

Timeline (30 fps): S1 hook 0–2.0 s · S2 customer → item → price (totals auto-calculate) 2.0–6.3 s · S3 hover 0.27 s → click PDF +
punch zoom 6.3–8.1 s · S4 generated PDF + zoom to the grand total 8.1–12.0 s · S5 end card 12.0–14.97 s.

**Privacy:** the Apps Script web-app URL is blurred; the personal tax ID (shown twice) and the bank account number are smudged;
the PDF is cut above the bank details. Company name / phone / LINE / e-mail stay as on the original document.

**Background music:** none is mixed unless you drop a *licensed* audio file (mp3/wav/m4a/aac/flac/ogg) in the repo root or in
`./music/` — `final7.js` then adds it at −24 dB with fades and SFX ducking. No music was available for the delivered render.
