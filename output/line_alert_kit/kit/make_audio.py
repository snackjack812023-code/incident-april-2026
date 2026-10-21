"""SFX for the LINE-alert edit (whoosh on cuts, click on the two button presses, success chime, notification ding, pops on
key text) synthesised with NumPy and mixed UNDER the original music bed. Writes work/audio.wav (48 kHz stereo 16-bit)."""
import json, os, wave
import numpy as np
from scipy import signal
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000; rng = np.random.default_rng(11)
spec = json.load(open(os.path.join(ROOT, 'work', 'edit.json'))); N = int(round(spec['N'] / spec['FPS'] * SR))
def tt(n): return np.arange(n) / SR
def filt(x, kind, fc, order=2): return signal.sosfilt(signal.butter(order, fc, kind, fs=SR, output='sos'), x, axis=0)
def st(y): return np.stack([y, y], 1)
def whoosh():
    n = int(0.46 * SR); t = tt(n); x = rng.standard_normal(n); y = np.zeros(n); zi = None
    for i in range(0, n, 256):
        fc = 500 * (3600 / 500) ** np.sin(np.pi * i / n)
        s = signal.butter(2, [fc * 0.6, min(fc * 1.7, 20000)], 'band', fs=SR, output='sos')
        if zi is None: zi = np.zeros((s.shape[0], 2))
        y[i:i + 256], zi = signal.sosfilt(s, x[i:i + 256], zi=zi)
    env = np.sin(np.pi * np.clip(t / 0.46, 0, 1)) ** 2 * np.exp(-np.maximum(t - 0.14, 0) * 3.0); y *= env; pan = np.clip(t / 0.46, 0, 1)
    return np.stack([y * np.sqrt(1 - pan * 0.7), y * np.sqrt(0.3 + pan * 0.7)], 1)
def click():
    n = int(0.06 * SR); t = tt(n)
    return st(0.6 * np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 380) + 0.5 * filt(rng.standard_normal(n), 'high', 2500) * np.exp(-t * 1200) + 0.25 * np.sin(2 * np.pi * 320 * t) * np.exp(-t * 160))
def pop():
    n = int(0.16 * SR); t = tt(n); f = 300 + 650 * np.exp(-t / 0.018)
    return st(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 34) * (1 - np.exp(-t * 900)) + 0.15 * filt(rng.standard_normal(n), 'high', 3000) * np.exp(-t * 900))
def bell(f0, dur, decay):
    n = int(dur * SR); t = tt(n); y = np.zeros(n)
    for ratio, amp, dk in ((1.0, 1.0, 1.0), (2.0, 0.45, 1.6), (3.01, 0.22, 2.4), (4.16, 0.10, 3.2)):
        y += amp * np.sin(2 * np.pi * f0 * ratio * t) * np.exp(-t * decay * dk)
    return y * (1 - np.exp(-t * 2500))
def chime():                       # success: two quick rising bell notes (E6 -> B6)
    y = bell(1318.5, 0.9, 5.0); b = bell(1975.5, 0.9, 5.5); i = int(0.09 * SR); y[i:] += 0.9 * b[:len(y) - i]
    return np.stack([y * 0.9, y], 1)
def ding():                        # incoming message: one soft bell with a gentle octave shimmer
    y = bell(1567.98, 1.1, 3.6) + 0.25 * bell(3135.96, 1.1, 6.0); return np.stack([y, y * 0.92], 1)
SFX = {'whoosh': whoosh(), 'click': click(), 'pop': pop(), 'chime': chime(), 'ding': ding()}
C = spec['cues']
events = [(f, 'whoosh', -21 if f == 0 else -18, -0.10) for f in C['whoosh']] + [(f, 'click', -20, 0) for f in C['clicks']] \
       + [(C['success'], 'chime', -16, 0), (C['ding'], 'ding', -15, 0)] + [(f, 'pop', -19, 0) for f in C['pop']]
LEAD = 0.015
def read_wav(p):
    with wave.open(p) as w: return np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, w.getnchannels()).astype(np.float64) / 32768
music = read_wav(os.path.join(ROOT, 'work', 'music_raw.wav'))[:N]; music = np.pad(music, ((0, N - len(music)), (0, 0)))
sfx = np.zeros((N, 2))
for f, name, peak, off in events:
    x = SFX[name]; x = x / np.abs(x).max() * 10 ** (peak / 20); i = max(0, int(round((f / spec['FPS'] - LEAD + off) * SR)))
    n = min(len(x), N - i); sfx[i:i + n] += x[:n]
mix = music + sfx; pk = np.abs(mix).max()
if pk > 0.891: mix *= 0.891 / pk
with wave.open(os.path.join(ROOT, 'work', 'audio.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
db = lambda x: 20 * np.log10(np.abs(x).max() + 1e-12)
print(f'audio: {N / SR:.2f}s, music peak {db(music):.1f} dBFS, sfx peak {db(sfx):.1f} dBFS, mix peak {db(mix):.1f} dBFS, {len(events)} sfx events')
