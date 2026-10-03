#!/usr/bin/env bash
# Rebuilds output/smartflow_quotation_tiktok.mp4 (1080x1920, 30 fps, H.264/AAC, <= 15 s) from the screen-recording clips.
#   SRC_B=/path/to/..._210036.mp4  SRC_C=/path/to/..._210121.mp4  [WORK=/tmp/smartflow_work] [OUT=file.mp4] ./build.sh
# Needs: ffmpeg/ffprobe (>= 6, libx264), node (>= 18) with Playwright + Chromium available (NODE_PATH), npm (for the OFL "Prompt" font).
# BGM: only if a licensed music file (mp3/wav/m4a/aac/flac/ogg) is placed in the repo root or ./music — otherwise none is used.
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export REPO="$(cd "$KIT/../.." && pwd)"
: "${SRC_B:?set SRC_B to the 21:00:36 clip (…210036.mp4)}"; : "${SRC_C:?set SRC_C to the 21:01:21 clip (…210121.mp4)}"
export S="${WORK:-/tmp/smartflow_work}"
OUT="${OUT:-$REPO/output/smartflow_quotation_tiktok.mp4}"
mkdir -p "$S/kit" "$S/gfx/ov" "$S/seg" "$S/sfx" "$(dirname "$OUT")"
cp "$KIT"/kit/*.js "$S/kit/"; cp "$KIT"/gfx/* "$S/gfx/"; cp "$KIT/kit/lib.js" "$S/gfx/lib.js"
ln -sf "$(realpath "$SRC_B")" "$S/B.mp4"; ln -sf "$(realpath "$SRC_C")" "$S/C.mp4"
(cd "$S/gfx" && [ -d node_modules/@fontsource/prompt ] || { npm init -y >/dev/null 2>&1; npm install --no-audit --no-fund @fontsource/prompt >/dev/null; })
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
echo "[1/6] footage reel";  node "$S/kit/make_reel.js" | tail -3
echo "[2/6] card assets";   (cd "$S/gfx" && node render_chrome.js)
echo "[3/6] plate";         A=0 B=449 OUT="$S/plate.mkv" node "$S/kit/run_plate.js" | tail -1
echo "[4/6] overlays";      (cd "$S/gfx" && OUT=ov node render_overlay.js | tail -1)
echo "[5/6] sound";         node "$S/kit/make_sfx.js" | tail -1
echo "[6/6] final encode";  OUT="$OUT" node "$S/kit/final.js" | tail -2
if ! node "$S/kit/verify.js" "$OUT"; then
  echo "verification failed -> re-encoding with strict CFR/duration"; PRESET=slow CRF=12 FRAMES=449 OUT="$OUT" node "$S/kit/final.js" | tail -1
  node "$S/kit/verify.js" "$OUT"
fi
