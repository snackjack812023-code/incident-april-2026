"""SFX (whoosh on page changes, click on KPI / button focus, pop on key text) synthesised with NumPy and mixed UNDER the
original music bed (SFX peaks stay well below the music peaks). Writes work/audio.wav (48 kHz stereo, 16-bit)."""
import json, os, wave
import numpy as np
from scipy import signal
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
rng = np.random.default_rng(11)
spec = json.load(open(os.path.join(ROOT, 'work', 'spec.json')))
DUR = spec['N'] / spec['FPS']; N = int(round(DUR * SR))

def tt(n): return np.arange(n) / SR
def filt(x, kind, fc, order=2): return signal.sosfilt(signal.butter(order, fc, kind, fs=SR, output='sos'), x, axis=0)
def whoosh():
    n = int(0.46 * SR); t = tt(n); x = rng.standard_normal(n); y = np.zeros(n); zi = None
    for i in range(0, n, 256):                                       # band-pass sweeping up then down
        p = i / n; fc = 500 * (3600 / 500) ** np.sin(np.pi * p)
        s = signal.butter(2, [fc * 0.6, min(fc * 1.7, 20000)], 'band', fs=SR, output='sos')
        if zi is None: zi = np.zeros((s.shape[0], 2))
        y[i:i + 256], zi = signal.sosfilt(s, x[i:i + 256], zi=zi)
    env = np.sin(np.pi * np.clip(t / 0.46, 0, 1)) ** 2 * np.exp(-np.maximum(t - 0.14, 0) * 3.0)
    y *= env; pan = np.clip(t / 0.46, 0, 1)
    return np.stack([y * np.sqrt(1 - pan * 0.7), y * np.sqrt(0.3 + pan * 0.7)], 1)
def click():
    n = int(0.06 * SR); t = tt(n)
    y = 0.6 * np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 380) + 0.5 * filt(rng.standard_normal(n), 'high', 2500) * np.exp(-t * 1200) + 0.25 * np.sin(2 * np.pi * 320 * t) * np.exp(-t * 160)
    return np.stack([y, y], 1)
def pop():
    n = int(0.16 * SR); t = tt(n)
    f = 300 + 650 * np.exp(-t / 0.018)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 34) * (1 - np.exp(-t * 900)) + 0.15 * filt(rng.standard_normal(n), 'high', 3000) * np.exp(-t * 900)
    return np.stack([y, y], 1)
SFX = {'whoosh': whoosh(), 'click': click(), 'pop': pop()}
LEAD = 0.015                                                           # sound a hair ahead of the picture

def read_wav(p):
    with wave.open(p) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, w.getnchannels()).astype(np.float64) / 32768
    return a
music = read_wav(os.path.join(ROOT, 'work', 'music_raw.wav'))[:N]
music = np.pad(music, ((0, N - len(music)), (0, 0)))
sfx = np.zeros((N, 2))
for e in spec['sfx']:
    x = SFX[e['name']]; x = x / np.abs(x).max() * 10 ** (e['peak'] / 20)
    i = int(round((e['f'] / spec['FPS'] - LEAD + e.get('off', 0)) * SR)); i = max(0, i)
    n = min(len(x), N - i); sfx[i:i + n] += x[:n]
mix = music + sfx
peak = np.abs(mix).max()
if peak > 0.891: mix *= 0.891 / peak                                   # keep >= 1 dB headroom (final encode also limits)
pcm = (np.clip(mix, -1, 1) * 32767).astype('<i2')
with wave.open(os.path.join(ROOT, 'work', 'audio.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
db = lambda x: 20 * np.log10(np.abs(x).max() + 1e-12)
print(f'audio: {DUR:.2f}s, music peak {db(music):.1f} dBFS, sfx peak {db(sfx):.1f} dBFS, mix peak {db(mix):.1f} dBFS, {len(spec["sfx"])} sfx events')
