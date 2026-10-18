"""Per-frame visual analysis of the phone recording: global shake (phase correlation), content change after
compensating the shake, brightness, sharpness. Writes work/motion.npz. usage: motion.py src.mp4"""
import subprocess, sys
import numpy as np, cv2
src = sys.argv[1]; out = sys.argv[2]
W, H = 270, 480
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-vf', f'scale={W}:{H}:flags=area,format=gray', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
prev = None; rows = []; win = cv2.createHanningWindow((W, H), cv2.CV_32F); ts = []
n = 0
while True:
    b = p.stdout.read(W * H)
    if len(b) < W * H: break
    g = np.frombuffer(b, np.uint8).reshape(H, W).astype(np.float32)
    sharp = cv2.Laplacian(g, cv2.CV_32F).var(); bright = g.mean()
    if prev is None: dx = dy = resid = 0.0
    else:
        (dx, dy), _ = cv2.phaseCorrelate(prev, g, win)
        M = np.float32([[1, 0, -dx], [0, 1, -dy]]); gw = cv2.warpAffine(g, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        d = np.abs(gw - prev)[20:-20, 20:-20]; resid = float(np.percentile(d, 99))
    rows.append((dx, dy, resid, sharp, bright)); prev = g; n += 1
p.wait()
a = np.array(rows, np.float32); np.savez(out, m=a)
print('frames', n)
