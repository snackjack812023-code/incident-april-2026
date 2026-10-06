"""Stage 0: uploaded clip -> work/clean.mkv (deblocked, denoised, vidstab-stabilised, lossless) + work/card_track.json
(per-frame drift of the LINE message card in the phone close-up, phase correlation against source frame 570)."""
import json, os, subprocess, sys
import numpy as np
from numpy.fft import fft2, ifft2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = os.path.join(ROOT, 'work'); os.makedirs(W, exist_ok=True)
src = os.environ.get('SRC_VIDEO') or os.path.join(ROOT, 'src', 'source.mp4')
# libvidstab parallelises with OpenMP and then writes its motion list in thread order, which changes the stabilisation from run
# to run; one OpenMP thread makes the whole build deterministic
ENV = dict(os.environ, OMP_NUM_THREADS='1')
run = lambda a, **k: subprocess.run(a, check=True, env=ENV, **k)
run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', 'vidstabdetect=shakiness=5:accuracy=15:result=transforms.trf', '-f', 'null', '-'], cwd=W)
run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-an', '-vf', 'deblock=filter=strong:block=8,hqdn3d=2:1.5:3:3,vidstabtransform=input=transforms.trf:smoothing=12:optzoom=1:interpol=bicubic,format=rgb24',
     '-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'bgr0', 'clean.mkv'], cwd=W)
raw = run(['ffmpeg', '-v', 'error', '-i', os.path.join(W, 'clean.mkv'), '-vf', "select='gte(n\\,480)',format=gray", '-f', 'rawvideo', '-'], capture_output=True).stdout
a = np.frombuffer(raw, np.uint8).reshape(-1, 1024, 576).astype(np.float32)
ref = a[90][250:600, 150:430]
def shift(img, tpl):
    A = fft2(img - img.mean()); B = fft2(tpl - tpl.mean()); R = A * np.conj(B); R /= np.abs(R) + 1e-6; r = np.real(ifft2(R))
    dy, dx = np.unravel_index(np.argmax(r), r.shape); dy = dy - r.shape[0] if dy > r.shape[0] // 2 else dy; dx = dx - r.shape[1] if dx > r.shape[1] // 2 else dx
    return int(dx), int(dy)
track = {480 + i: shift(a[i][250:600, 150:430], ref) for i in range(len(a))}
ks = sorted(track); dx = np.array([track[k][0] for k in ks], float); dy = np.array([track[k][1] for k in ks], float)
med = lambda x, w=5: np.array([np.median(x[max(0, i - w // 2):i + w // 2 + 1]) for i in range(len(x))])
dx, dy = med(dx), med(dy)
json.dump({str(k): [float(x), float(y)] for k, x, y in zip(ks, dx, dy)}, open(os.path.join(W, 'card_track.json'), 'w'))
print(f'prep: clean.mkv + card_track.json ({len(ks)} tracked frames)')
