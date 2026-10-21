#!/usr/bin/env bash
# Rebuilds output/SmartFlow_LINE_Auto_Notification_TikTok.mp4 (1080x1920, 30 fps, H.264 High CRF 14 + AAC 320k, 17.0 s)
# from the original phone clip (1080x1920 HEVC, 59.94 fps, no audio). The original is only read.
#   SRC=/path/to/clip.mp4 [WORK=/tmp/line_notification] [OUT=file.mp4] ./build.sh
# Needs: ffmpeg/ffprobe (>= 6, libx264), python3 + NumPy + SciPy + OpenCV (with SIFT, opencv >= 4.4),
# node (>= 18) with Playwright + Chromium (NODE_PATH). Font: Prompt (SIL OFL 1.1) in gfx/fonts; emoji: system Noto Color Emoji.
# Music and sound effects are synthesised by kit/music.py and kit/mix.py (original, no samples, no downloads).
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; REPO="$(cd "$KIT/../.." && pwd)"
SRC="${SRC:?set SRC=/path/to/clip.mp4}"; W="${WORK:-/tmp/line_notification}"; OUT="${OUT:-$REPO/output/SmartFlow_LINE_Auto_Notification_TikTok.mp4}"
mkdir -p "$W/src" "$W/work/ov"; cp -r "$KIT/kit" "$KIT/gfx" "$W/"; ln -sf "$(readlink -f "$SRC")" "$W/src/source.mp4"
python3 -c "import numpy, scipy, cv2; cv2.SIFT_create()" 2>/dev/null || pip install --quiet numpy scipy opencv-python-headless
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
cd "$W"
echo "[1/7] frame times + planar tracking (chat, LINE card)"
ffprobe -v error -select_streams v:0 -show_entries frame=best_effort_timestamp_time -of csv=p=0 src/source.mp4 > work/pts.txt
python3 -I kit/track.py | tail -2
echo "[2/7] text layout";             python3 -I kit/spec.py
echo "[3/7] text (Chromium)";         (cd gfx && node render.js ../work/items.json ../work/ov)
echo "[4/7] picture (~2 min)";        python3 -I kit/render.py work/video.mp4 2>/dev/null | tail -1
echo "[5/7] music";                   python3 -I kit/music.py
echo "[6/7] sfx + mix";               python3 -I kit/mix.py
echo "[7/7] mux + checks";            python3 -I kit/final.py "$OUT"; python3 -I kit/verify.py "$OUT" work/mix.wav
