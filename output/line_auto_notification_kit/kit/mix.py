"""Sound for the SmartFlow LINE clip -> work/mix.wav (48 kHz stereo): the original music (kit/music.py) and five
original SFX on the cues in spec.SFX. The notification is the loudest effect and the music dips ~37% (-4 dB) around
it; then -14 LUFS integrated with a true-peak limiter at -1 dBTP. No voice, no samples, nothing downloaded; the
notification is a generic two-note glass chime, not LINE's own sound."""
import os, sys, wave
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec as SP, music as MU

SR = 48000; N = int(round(SP.DUR * SR)); rng = np.random.default_rng(77)
tt, filt, sweep = MU.tt, MU.filt, MU.sweep

def whoosh(dur, f0, f1, pan0=0.3, pan1=0.7):
    n = int(dur * SR); t = tt(n)
    y = sweep(rng.standard_normal(n), lambda s: f0 * (f1 / f0) ** (s / dur), kind='band', q_band=(0.6, 1.6))
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.6
    p = pan0 + (pan1 - pan0) * t / dur
    return np.stack([y * env * np.sqrt(1 - p), y * env * np.sqrt(p)], 1)
def click():
    n = int(0.06 * SR); x = np.zeros(n); t = tt(n)
    for o, v in ((0, 1.0), (int(0.016 * SR), 0.7)):
        m = int(0.004 * SR); x[o:o + m] += filt(rng.standard_normal(m), 'band', [1800, 6500]) * np.exp(-np.arange(m) / (0.0008 * SR)) * v
    x += np.sin(2 * np.pi * 2600 * t) * np.exp(-t / 0.004) * 0.25 + np.sin(2 * np.pi * 1250 * t) * np.exp(-t / 0.014) * 0.45   # soft body
    return np.stack([x, x], 1)
def notify():
    """two rising glass tones (B5 -> E6) with a soft bubble pop on the onset and a short stereo slap"""
    n = int(1.2 * SR); t = tt(n); y = np.zeros(n)
    for f0, d, v in ((987.77, 0.0, 1.0), (1318.51, 0.115, 0.92)):
        i = int(d * SR); s = t[:n - i]
        tone = np.sin(2 * np.pi * f0 * s) + 0.32 * np.sin(4 * np.pi * f0 * s) * np.exp(-s / 0.08) + 0.12 * np.sin(2 * np.pi * 3.98 * f0 * s) * np.exp(-s / 0.04)
        y[i:] += v * tone * (1 - np.exp(-s / 0.0015)) * np.exp(-s / 0.34)
    m = int(0.06 * SR); tm = tt(m)
    y[:m] += np.sin(2 * np.pi * np.cumsum(420 + 520 * (1 - np.exp(-tm / 0.01))) / SR) * np.exp(-tm / 0.012) * 0.35
    k = int(0.009 * SR); R = np.concatenate([np.zeros(k), y[:-k]])
    return np.stack([y + 0.18 * R, 0.82 * y + 0.35 * R], 1)
def pop():
    n = int(0.12 * SR); t = tt(n); f = 520 + 600 * (1 - np.exp(-t / 0.02))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035) * np.clip(t / 0.002, 0, 1)
    return np.stack([x, x], 1)

def lufs(x):
    from scipy.signal import lfilter
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([np.mean(y[i:i + blk] ** 2, axis=0).sum() for i in range(0, len(y) - blk, hop)])
    lk = -0.691 + 10 * np.log10(ms + 1e-12); rel = -0.691 + 10 * np.log10(ms[lk > -70].mean()) - 10
    return -0.691 + 10 * np.log10(ms[(lk > -70) & (lk > rel)].mean())
def tp_limit(x, ceiling_db=-1.0, look=0.002, rel=0.08):
    from scipy.ndimage import minimum_filter1d
    lim = 10 ** (ceiling_db / 20); up = signal.resample_poly(x, 4, 1, axis=0); pk = np.abs(up).max(axis=1).reshape(-1, 4).max(axis=1)[:len(x)]
    g = minimum_filter1d(np.minimum(1.0, lim / np.maximum(pk, 1e-9)), size=2 * int(look * SR) + 1, mode='nearest')
    a = np.exp(-1 / (rel * SR)); out = np.empty_like(g); y = 1.0
    for i, v in enumerate(g): y = v if v < y else a * y + (1 - a) * v; out[i] = y
    return x * out[:, None]

def duck():
    t0, t1, t2, depth = SP.DUCK; t = tt(N); g = np.ones(N); low = 10 ** (depth / 20)
    down = np.clip((t - t0) / 0.04, 0, 1); up = np.clip((t - t1) / (t2 - t1), 0, 1)
    return 1 - (1 - low) * (0.5 - 0.5 * np.cos(np.pi * down)) * (0.5 + 0.5 * np.cos(np.pi * up))

if __name__ == '__main__':
    with wave.open(os.path.join(SP.W, 'music.wav')) as w:
        mus = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2).astype(np.float64) / 32768.0
    mus = mus[:N] * 10 ** ((-16.0 - lufs(mus[:N])) / 20) * duck()[:, None]
    fx = np.zeros((N, 2))
    def put(x, t, peak):
        i = int(round(t * SR)); m = min(len(x), N - i); fx[i:i + m] += x[:m] * peak / np.abs(x).max()
    put(whoosh(0.42, 700, 5200, 0.35, 0.65), SP.SFX['whoosh_in'], 0.30)
    put(click(), SP.SFX['click'], 0.50)
    put(notify(), SP.SFX['notify'], 0.62)
    put(whoosh(0.62, 380, 6200, 0.15, 0.85), SP.SFX['whoosh_tr'], 0.62)
    put(pop(), SP.SFX['pop'], 0.34)
    mix = mus + fx
    mix = tp_limit(mix * 10 ** ((-14.0 - lufs(mix)) / 20))
    pcm = (np.clip(mix, -1, 1) * 32767 + rng.uniform(-0.5, 0.5, mix.shape)).astype('<i2')
    with wave.open(os.path.join(SP.W, 'mix.wav'), 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    np.save(os.path.join(SP.W, 'fx_only.npy'), fx.astype(np.float32)); np.save(os.path.join(SP.W, 'music_only.npy'), mus.astype(np.float32))
    print(f'mix {lufs(mix):.1f} LUFS, sample peak {20 * np.log10(np.abs(mix).max()):.1f} dBFS, {N / SR:.2f} s')
