"""SFX for the HR clip, synthesised with NumPy and mixed UNDER the music bed: whoosh on every scene change, click when the
function tag switches, pop on highlights, soft chime on the LINE notifications, small digital beep/blip UI sounds.
Writes work/audio.wav (48 kHz stereo 16-bit) and work/sfx_cues.json (cue times for the sync check)."""
import json, os, wave
import numpy as np
from scipy import signal
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000; rng = np.random.default_rng(11)
spec = json.load(open(os.path.join(ROOT, 'work', 'spec.json'))); N = int(round(spec['N'] / spec['FPS'] * SR))
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
def ding():                          # soft notification chime (generic, two bell partials)
    y = bell(1567.98, 1.0, 4.0) + 0.25 * bell(3135.96, 1.0, 6.5); return np.stack([y, y * 0.92], 1)
def beep():                          # scan-confirm: two short digital tones
    n = int(0.22 * SR); t = tt(n); y = np.zeros(n)
    for f, t0 in ((1760.0, 0.0), (2349.3, 0.09)):
        m = t >= t0; tt0 = t[m] - t0; y[m] += np.sin(2 * np.pi * f * tt0) * np.exp(-tt0 * 30) * (1 - np.exp(-tt0 * 3000))
    return st(y)
def blip():                          # data / export UI blip: short rising FM chirp
    n = int(0.09 * SR); t = tt(n); f = 900 + 900 * (t / 0.09)
    return st(np.sin(2 * np.pi * np.cumsum(f) / SR + 0.8 * np.sin(2 * np.pi * 2.0 * np.cumsum(f) / SR)) * np.exp(-t * 38) * (1 - np.exp(-t * 2000)))
SFX = {'whoosh': whoosh(), 'click': click(), 'pop': pop(), 'ding': ding(), 'beep': beep(), 'blip': blip()}
LEAD = 0.015
def read_wav(p):
    with wave.open(p) as w: return np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, w.getnchannels()).astype(np.float64) / 32768
music = read_wav(os.path.join(ROOT, 'work', 'music_raw.wav'))[:N]; music = np.pad(music, ((0, N - len(music)), (0, 0)))
sfx = np.zeros((N, 2)); cues = []
for e in spec['sfx']:
    x = SFX[e['name']]; x = x / np.abs(x).max() * 10 ** (e['peak'] / 20)
    t = e['f'] / spec['FPS'] - LEAD + e.get('off', 0); i = max(0, int(round(t * SR)))
    n = min(len(x), N - i); sfx[i:i + n] += x[:n]; cues.append({'name': e['name'], 'frame': e['f'], 't': round(max(0, t), 4)})
mix = music * 10 ** (-1.0 / 20) + sfx                      # music bed 1 dB down to make room; SFX stay well under it
pk = np.abs(mix).max()
if pk > 0.891: mix *= 0.891 / pk
with wave.open(os.path.join(ROOT, 'work', 'audio.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
json.dump(cues, open(os.path.join(ROOT, 'work', 'sfx_cues.json'), 'w'), indent=0)
db = lambda x: 20 * np.log10(np.abs(x).max() + 1e-12)
print(f'audio: {N / SR:.2f}s, music peak {db(music):.1f} dBFS, sfx peak {db(sfx):.1f} dBFS, mix peak {db(mix):.1f} dBFS, {len(cues)} sfx cues')
