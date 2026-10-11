#!/usr/bin/env bash
# Rebuilds output/SmartFlow_HR_TikTok_Final.mp4 (1080x1920, 30 fps, H.264/AAC, 20.0 s) from the 9-scene storyboard image.
#   [STORYBOARD=/path/storyboard.png] [WORK=/tmp/smartflow_hr] [OUT=file.mp4] ./build.sh
# Needs: ffmpeg/ffprobe (>= 6, libx264), python3 + NumPy + SciPy + Pillow + OpenCV (opencv-python-headless),
# node (>= 18) with Playwright + Chromium (NODE_PATH), npm (OFL "Prompt" font). Downloads the Real-ESRGAN general-x4v3 weights
# (BSD-3-Clause, github.com/xinntao/Real-ESRGAN) once. The music is synthesised by kit/music.py (original, no samples).
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; REPO="$(cd "$KIT/../.." && pwd)"
W="${WORK:-/tmp/smartflow_hr}"; OUT="${OUT:-$REPO/output/SmartFlow_HR_TikTok_Final.mp4}"
mkdir -p "$W/src" "$W/work" "$W/models" "$W/an" "$(dirname "$OUT")"; cp -r "$KIT/kit" "$KIT/gfx" "$W/"
cp "${STORYBOARD:-$KIT/src/storyboard.png}" "$W/src/storyboard.png"
M="$W/models/realesr-general-x4v3.pth"; SHA=8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292
[ -f "$M" ] || curl -sSL -o "$M" https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth
echo "$SHA  $M" | sha256sum -c --quiet
python3 -c "import PIL, numpy, scipy, cv2" 2>/dev/null || pip install --quiet pillow numpy scipy opencv-python-headless
(cd "$W/gfx" && [ -d node_modules/@fontsource/prompt ] || { npm init -y >/dev/null 2>&1; npm install --no-audit --no-fund @fontsource/prompt >/dev/null; })
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
echo "[1/7] panels: cut, remove storyboard badges, 4x super-resolution"; python3 -I "$W/kit/prep.py" | tail -1
echo "[2/7] timeline";             python3 -I "$W/kit/spec.py"
echo "[3/7] picture (lossless)";   python3 -I "$W/kit/render.py" "$W/work/plate.mkv" | tail -1
echo "[4/7] overlay";              (cd "$W/gfx" && node render_overlay.js | tail -1)
echo "[5/7] music";                python3 -I "$W/kit/music.py"
echo "[6/7] sfx + mix";            python3 -I "$W/kit/make_audio.py"
echo "[7/7] encode";               python3 -I "$W/kit/final.py" "$OUT"
python3 -I "$W/kit/verify.py" "$OUT"
