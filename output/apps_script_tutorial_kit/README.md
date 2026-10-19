# Google Apps Script quotation + invoice tutorial (TikTok/Reels): build kit

This kit rebuilds two files from the original phone recording `20261018_205830.mp4` (203.9 s, HEVC, 1080x1920 portrait):

- `output/google_apps_script_quotation_invoice_tutorial.mp4`: voice, soft original chord music at the start and the end, and a few soft SFX.
- `output/google_apps_script_quotation_invoice_tutorial_clean.mp4`: the same edit, voice only.

Both are 1080x1920, 30 fps, H.264 High + AAC 256k and 2:25.6 long. The recording itself is not in the repo (349 MB). It is only ever read; nothing writes to it.

```bash
SRC=/path/to/20261018_205830.mp4 ./build.sh     # ~20 min on 4 cores
```

| Step | File | What it does |
|---|---|---|
| 1 | `build.sh`, `kit/motion.py` | Makes a CFR 30 fps working copy (x264 CRF 12) for frame-exact seeks. Records the per-frame camera motion of the hand-held shot (phase correlation) and the frame times. |
| 2 | `kit/voice.py` | Natural voice repair on the source timeline: mono, declip, 4th-order HPF at 75 Hz, light FFT denoise (max 6 dB, no gating, so no robot voice). Then EQ (−2.5 dB at 280 Hz, +3.5 dB at 3 kHz, +1 dB shelf above 7.5 kHz), a split-band de-esser, a 2:1 soft-knee compressor and a ±4 dB phrase leveller. The speaker's own voice is kept: no voice change, no AI voice. |
| 3 | `kit/edl.py`, `kit/timeline.py`, `kit/overlay_items.py` | The edit. Covers every clip (source range, speed, zoom keys, highlight rings, holds), the Thai subtitles (from the real speech, with two-line breaks set by hand so words like ใบเสนอราคา are never split), STEP pills, tips, hook, result text and CTA. Cut points snap to the quietest 10 ms and never into a word: a cut waits for ≥ 40 ms below −45 dBFS. |
| 4 | `gfx/overlay.html`, `gfx/render.js` | Renders every text item to a transparent PNG in Chromium using the Prompt font (SIL OFL 1.1, `gfx/fonts`). |
| 5 | `kit/linefit.py`, `kit/blur_track.py` | Privacy blur keys (see below). Each key is snapped onto its text line, then tracked frame by frame (local phase correlation plus a whole-line fit), forward and backward between keys. |
| 6 | `kit/compose.py` | Builds each frame from the CFR copy. It applies light stabilisation, uniform-scale zoom/pan (never stretched), a mild unsharp mask for screen text, the privacy blur, highlight rings that follow the camera, and the overlays. Output is a master, x264 CRF 16, BT.709. |
| 7 | `kit/music.py`, `kit/mixdown.py`, `kit/audio_qa.py` | Cuts the voice with the same ranges as the picture, so sync holds by construction, with 8 ms fades at real cuts only. The main mix adds original soft-chord music synthesised by `kit/music.py`: felt keys, a warm pad and music-box notes on D major IV–V–iii–vi. It plays at the start (hook → STEP 1 card) and the end ("เสร็จแล้ว!" → CTA). It sits about 10 dB under the voice where nobody talks and dips a further 9 dB under speech; the steps in between stay voice only. A few SFX are added too (pop, two clicks, a success chime in the music's key). Both mixes are normalised to −14 LUFS with a true-peak limiter at −1 dBTP. The QA script checks word safety and clicks at every cut, dead air, and the music level against the voice. |
| 8 | `kit/final.py`, `kit/verify.py` | Re-encodes the master once with 2-pass x264 at ~4.6 Mb/s. Text looks the same as the master (the extra bits there go to the phone camera's grain), and each file stays under 100 MB for phone upload. Muxes that stream with each mix as AAC 256k (faststart). Checks format, decoding, black frames, loudness and true peak, and audio/picture alignment against the mix. |

`kit/asr2.py` is not part of the build. It is the faster-whisper pass (large-v3 / large-v2, Thai, word timestamps, VAD re-runs where large-v3 hallucinated) that the subtitles were transcribed from. The corrected subtitle text lives in `kit/edl.py`.

## Edit

The sections are: hook, intro, STEP 1–5, result, CTA.

- **Hook (0–1.3 s).** The finished dashboard with "สร้างใบเสนอราคา + ใบแจ้งหนี้ อัตโนมัติด้วย Apps Script 🔥".
- **STEP 1.** It is not in the recording, so it is a short dimmed instruction card (Google Sheets → ส่วนขยาย → Apps Script).
- **Waits.** Loading and typing stretches are speed-ramped (×2–×4, muted) or cut.
- **Result.** Reuses the demo footage from the start of the recording.
- **CTA.** It is text only, because there is no spoken CTA in the recording.

## Privacy

The Web App is deployed with access "Anyone", so its URL and deployment ID are blurred wherever they are readable. This covers the address bar in the laptop shots and the ID and URL lines in the deploy dialog. Tabs, page content and buttons stay sharp.
