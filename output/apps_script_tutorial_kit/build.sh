#!/usr/bin/env bash
# Rebuilds output/google_apps_script_quotation_invoice_tutorial.mp4 and ..._clean.mp4 (1080x1920, 30 fps, H.264/AAC)
# from the original phone recording 20261018_205830.mp4 (not in the repo: 349 MB). The original is only read.
#   SRC=/path/to/20261018_205830.mp4 [WORK=/tmp/apps_script_tutorial] [OUT_DIR=output] ./build.sh
# Needs: ffmpeg/ffprobe (>= 6, libx264), python3 + NumPy + SciPy + OpenCV (opencv-python-headless), node (>= 18) with
# Playwright + Chromium (NODE_PATH). Font: Prompt (SIL OFL 1.1) in gfx/fonts; emoji from the system Noto Color Emoji.
# The music bed and the SFX are synthesised by kit/mixdown.py (original, no samples, no downloads).
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; REPO="$(cd "$KIT/../.." && pwd)"
SRC="${SRC:?set SRC=/path/to/20261018_205830.mp4}"; W="${WORK:-/tmp/apps_script_tutorial}"; OUT="${OUT_DIR:-$REPO/output}"
mkdir -p "$W/src" "$W/work/ov"; cp -r "$KIT/kit" "$KIT/gfx" "$W/"
ln -sf "$(readlink -f "$SRC")" "$W/src/20261018_205830.mp4"
python3 -c "import numpy, scipy, cv2" 2>/dev/null || pip install --quiet numpy scipy opencv-python-headless
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
cd "$W"
echo "[1/8] CFR 30 fps working copy, frame times, camera motion"
ffmpeg -v error -y -i src/20261018_205830.mp4 -vf fps=30 -an -c:v libx264 -preset veryfast -crf 12 -g 15 -pix_fmt yuv420p work/src30.mp4
ffprobe -v error -select_streams v:0 -show_entries frame=best_effort_timestamp_time -of csv=p=0 src/20261018_205830.mp4 > work/pts.txt
python3 -I kit/motion.py src/20261018_205830.mp4 work/motion.npz
echo "[2/8] voice enhancement";            python3 -I kit/voice.py
echo "[3/8] timeline + overlay layout";    python3 -I kit/overlay_items.py | tail -1
echo "[4/8] overlays (Chromium)";          (cd gfx && node render.js ../work/ov/items.json ../work/ov)
echo "[5/8] privacy-blur tracking";        python3 -I kit/blur_track.py | tail -1
echo "[6/8] picture (~10 min)";            python3 -I kit/compose.py work/video.mp4 | tail -1
echo "[7/8] audio: main + clean mixes";    python3 -I kit/mixdown.py; python3 -I kit/audio_qa.py
echo "[8/8] mux + checks";                 python3 -I kit/final.py "$OUT"
python3 -I kit/verify.py "$OUT/google_apps_script_quotation_invoice_tutorial.mp4" work/mix_main.wav
python3 -I kit/verify.py "$OUT/google_apps_script_quotation_invoice_tutorial_clean.mp4" work/mix_clean.wav
