#!/usr/bin/env bash
# Rebuilds output/line_alert_tiktok.mp4 (1080x1920, 30 fps, H.264/AAC, 16.5 s) from the uploaded 576x1024 clip + the cover image.
#   SRC_VIDEO=/path/clip.mp4 [WORK=/tmp/line_alert] [OUT=file.mp4] ./build.sh
# Needs: ffmpeg/ffprobe (>= 6, libx264, vid.stab), python3 + Pillow + NumPy + SciPy, node (>= 18) with Playwright + Chromium (NODE_PATH),
# npm (downloads the OFL "Prompt" font). Music is synthesised by kit/music.py (original, no samples); the clip's own song is not used.
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; REPO="$(cd "$KIT/../.." && pwd)"
: "${SRC_VIDEO:?set SRC_VIDEO to the uploaded clip (576x1024 mp4)}"; export SRC_VIDEO="$(realpath "$SRC_VIDEO")"
W="${WORK:-/tmp/line_alert}"; OUT="${OUT:-$REPO/output/line_alert_tiktok.mp4}"
mkdir -p "$W/work" "$(dirname "$OUT")"; cp -r "$KIT/kit" "$KIT/gfx" "$KIT/src" "$W/"
python3 -c "import PIL, numpy, scipy" 2>/dev/null || pip install --quiet pillow numpy scipy
(cd "$W/gfx" && [ -d node_modules/@fontsource/prompt ] || { npm init -y >/dev/null 2>&1; npm install --no-audit --no-fund @fontsource/prompt >/dev/null; })
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
echo "[1/7] clean + stabilise + track"; python3 "$W/kit/prep.py"
echo "[2/7] edit decision list";       python3 "$W/kit/edit.py"
echo "[3/7] picture";                  python3 "$W/kit/render.py" "$W/work/plate.mkv" | tail -1
echo "[4/7] overlay";                  (cd "$W/gfx" && node render_overlay.js | tail -1)
echo "[5/7] music";                    python3 "$W/kit/music.py"
echo "[6/7] sfx + mix";                python3 "$W/kit/make_audio.py"
echo "[7/7] encode";                   python3 "$W/kit/final.py" "$OUT"
python3 "$W/kit/verify.py" "$OUT"
