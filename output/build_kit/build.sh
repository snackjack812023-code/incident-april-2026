#!/usr/bin/env bash
# Rebuilds output/smartflow_quotation_tiktok.mp4 (1080x1920, 30 fps, H.264/AAC, <= 15 s) from crisp sources:
# two full-HD screenshots of the quotation editor + the generated quotation PDF.
#   SHOT_ITEMS=/path/4.png  SHOT_HEADER=/path/5.png  PDF=/path/QT-20261003-01.pdf  [WORK=/tmp/smartflow_v7] [OUT=file.mp4] ./build.sh
#   SHOT_ITEMS  = editor scrolled to the item table / totals   SHOT_HEADER = editor at the top of the document (FROM / TO)
# Needs: ffmpeg/ffprobe (>= 6, libx264), pdfimages (poppler-utils), python3 + Pillow + NumPy, node (>= 18) with Playwright +
# Chromium (NODE_PATH), npm (for the OFL "Prompt" font). BGM only if a licensed audio file is placed in the repo root or ./music.
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export REPO="$(cd "$KIT/../.." && pwd)"
: "${SHOT_ITEMS:?set SHOT_ITEMS to the screenshot with the item table (4.png)}"
: "${SHOT_HEADER:?set SHOT_HEADER to the screenshot with the document header (5.png)}"
: "${PDF:?set PDF to the generated quotation PDF}"
export SHOT_ITEMS="$(realpath "$SHOT_ITEMS")" SHOT_HEADER="$(realpath "$SHOT_HEADER")" PDF="$(realpath "$PDF")"
W="${WORK:-/tmp/smartflow_v7}"
OUT="${OUT:-$REPO/output/smartflow_quotation_tiktok.mp4}"
mkdir -p "$W/src" "$W/work" "$(dirname "$OUT")"
cp -r "$KIT/kit7" "$KIT/gfx7" "$W/"
python3 -c "import PIL, numpy" 2>/dev/null || pip install --quiet pillow numpy
(cd "$W/gfx7" && [ -d node_modules/@fontsource/prompt ] || { npm init -y >/dev/null 2>&1; npm install --no-audit --no-fund @fontsource/prompt >/dev/null; })
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
echo "[1/7] sources + privacy redaction"; python3 "$W/kit7/prep.py" | tail -1
echo "[2/7] timeline";                    node "$W/kit7/spec7.js"
echo "[3/7] card/paper assets";           (cd "$W/gfx7" && node render_chrome7.js)
echo "[4/7] plate (lossless)";            python3 "$W/kit7/render_plate.py" "$W/work/plate7.mkv" | tail -1
echo "[5/7] overlays";                    (cd "$W/gfx7" && node render_overlay7.js | tail -1)
echo "[6/7] sound";                       node "$W/kit7/make_sfx7.js" | tail -1
echo "[7/7] final encode";                OUT="$OUT" node "$W/kit7/final7.js" | tail -2
if ! node "$W/kit7/verify.js" "$OUT"; then
  echo "verification failed -> re-encoding with strict CFR/duration"; PRESET=slow CRF=12 FRAMES=449 OUT="$OUT" node "$W/kit7/final7.js" | tail -1
  node "$W/kit7/verify.js" "$OUT"
fi
