#!/usr/bin/env bash
# Rebuilds output/factory_production_tracking_tiktok.mp4 (1080x1920, 30 fps, H.264/AAC, 21.0 s) from the 7 screenshots.
#   SHOTS=/dir/with/screenshots [WORK=/tmp/factory_tiktok] [OUT=file.mp4] ./build.sh
# SHOTS must contain (1920x1080 screenshots of the web app): dashboard.png calendar.png po.png board.png dept.png delivery.png report.png
# Needs: ffmpeg/ffprobe (>= 6, libx264), python3 + Pillow + NumPy + SciPy, node (>= 18) with Playwright + Chromium (NODE_PATH),
# npm (downloads the OFL "Prompt" font). The music is synthesised by kit/music.py (original, no samples).
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; REPO="$(cd "$KIT/../.." && pwd)"
: "${SHOTS:?set SHOTS to the folder with dashboard.png calendar.png po.png board.png dept.png delivery.png report.png}"
W="${WORK:-/tmp/factory_tiktok}"; OUT="${OUT:-$REPO/output/factory_production_tracking_tiktok.mp4}"
mkdir -p "$W/src" "$W/work" "$(dirname "$OUT")"; cp -r "$KIT/kit" "$KIT/gfx" "$W/"
for s in dashboard calendar po board dept delivery report; do cp "$SHOTS/$s.png" "$W/src/"; done
python3 -c "import PIL, numpy, scipy" 2>/dev/null || pip install --quiet pillow numpy scipy
(cd "$W/gfx" && [ -d node_modules/@fontsource/prompt ] || { npm init -y >/dev/null 2>&1; npm install --no-audit --no-fund @fontsource/prompt >/dev/null; })
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
echo "[1/6] timeline";        python3 "$W/kit/spec.py"
echo "[2/6] plate";           python3 "$W/kit/render_plate.py" "$W/work/plate.mkv" | tail -1
echo "[3/6] overlay";         (cd "$W/gfx" && node render_overlay.js | tail -1)
echo "[4/6] music";           python3 "$W/kit/music.py"
echo "[5/6] sfx + mix";       python3 "$W/kit/make_audio.py"
echo "[6/6] encode";          python3 "$W/kit/final.py" "$OUT"
python3 "$W/kit/verify.py" "$OUT"
