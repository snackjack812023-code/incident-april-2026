"""Planar tracking of the phone screen (SIFT features + RANSAC homography against a reference frame, half resolution).
  card  : the new LINE message card, outlined by hand on frame 470 (just after it arrives at frame 456), followed
          through frames 456-620 -> drives the hero zoom and the glow around the card
  chat  : a point in the chat area on frame 200, followed through frames 0-455 (before the chat scrolls) -> the
          steady centre for the hook / build-up zoom
Writes work/track.json {"card": {frame: [[x, y] x4], ...}, "chat": {frame: [x, y], ...}, "inliers": {...}}"""
import json, os, subprocess, sys
import numpy as np, cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = os.path.join(ROOT, 'work')
SRC = os.path.join(ROOT, 'src', 'source.mp4'); HW, HH = 540, 960
CARD_REF, CARD_Q = 470, np.float32([[435, 1045], [725, 830], [847, 1132], [612, 1370]])
CHAT_REF, CHAT_P = 200, np.float32([[600, 980]])

def frames():
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', SRC, '-vf', f'scale={HW}:{HH}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         stdout=subprocess.PIPE)
    out = []
    while True:
        b = p.stdout.read(HW * HH)
        if len(b) < HW * HH: break
        out.append(np.frombuffer(b, np.uint8).reshape(HH, HW))
    return out

def tracker(ref_img, mask):
    sift = cv2.SIFT_create(nfeatures=4000); kr, dr = sift.detectAndCompute(ref_img, mask)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    def H(img):
        k, d = sift.detectAndCompute(img, None)
        if d is None or len(k) < 8: return None, 0
        good = [m for m, n in bf.knnMatch(dr, d, k=2) if m.distance < 0.75 * n.distance]
        if len(good) < 12: return None, len(good)
        a = np.float32([kr[m.queryIdx].pt for m in good]); b = np.float32([k[m.trainIdx].pt for m in good])
        h, inl = cv2.findHomography(a, b, cv2.RANSAC, 3.0)
        return h, int(inl.sum()) if inl is not None else 0
    return H

if __name__ == '__main__':
    F = frames(); print('frames', len(F))
    res = {'card': {}, 'chat': {}, 'inliers': {}}
    # card: features on the phone screen around the card (the card quad grown 2.3x about its centre)
    c = CARD_Q.mean(0); grow = (c + (CARD_Q - c) * 2.3) / 2
    m = np.zeros((HH, HW), np.uint8); cv2.fillConvexPoly(m, np.round(grow).astype(np.int32), 255)
    H = tracker(F[CARD_REF], m)
    for k in range(456, min(621, len(F))):
        h, n = H(F[k]); res['inliers'][f'card{k}'] = n
        if h is not None and n >= 25:
            res['card'][k] = (cv2.perspectiveTransform((CARD_Q / 2)[None], h)[0] * 2).round(1).tolist()
    # chat point: features on the chat area of frame 200 (the screen before the new message scrolls it)
    m = np.zeros((HH, HW), np.uint8); cv2.ellipse(m, (int(CHAT_P[0, 0] / 2), int(CHAT_P[0, 1] / 2)), (170, 300), -30, 0, 360, 255, -1)
    H = tracker(F[CHAT_REF], m)
    for k in range(0, 456):
        h, n = H(F[k]); res['inliers'][f'chat{k}'] = n
        if h is not None and n >= 25:
            res['chat'][k] = (cv2.perspectiveTransform((CHAT_P / 2)[None], h)[0, 0] * 2).round(1).tolist()
    json.dump(res, open(os.path.join(W, 'track.json'), 'w'))
    ci = [v for kk, v in res['inliers'].items() if kk.startswith('card')]; hi = [v for kk, v in res['inliers'].items() if kk.startswith('chat')]
    print(f'card: {len(res["card"])}/165 frames tracked, inliers min/median {min(ci)}/{int(np.median(ci))}; '
          f'chat: {len(res["chat"])}/456 frames, inliers min/median {min(hi)}/{int(np.median(hi))}')
    lost = [k for k in range(456, 621) if k not in res['card']]
    print('card lost at frames:', lost[:20], '...' if len(lost) > 20 else '')
