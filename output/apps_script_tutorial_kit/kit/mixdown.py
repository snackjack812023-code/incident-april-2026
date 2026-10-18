"""Audio for the edited tutorial (48 kHz stereo):
  voice : the enhanced original voice (voice_proc.npy), cut with the same snapped ranges as the picture, so every sample
          keeps its own source time (lip/click sync by construction); 8 ms fades at real cuts only (contiguous clips are
          left untouched, so no dip inside a word)
  clean : voice only -> -14 LUFS integrated, true peak <= -1 dBTP
  main  : voice + a very low original lo-fi bed (synthesised here, rights-free, ducked under the speech) + a few soft SFX
          (pop on titles, 2 clicks on key buttons, success chime) -> -14 LUFS, <= -1 dBTP
Writes work/mix_clean.wav, work/mix_main.wav"""
import os, sys, wave
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL, overlay_items as OI

SR = 48000; FPS = TL.FPS; W = TL.W
N = int(round(TL.N / FPS * SR))
rng = np.random.default_rng(2026)

def tt(n): return np.arange(n) / SR
def filt(x, kind, fc, order=2): return signal.sosfilt(signal.butter(order, fc, kind, fs=SR, output='sos'), x, axis=0)

# ---------------- voice program
def voice_program():
    v = np.load(os.path.join(W, 'voice_proc.npy')).astype(np.float64)
    out = np.zeros(N); speech = np.zeros(N, bool); clips = TL.CLIPS
    for i, c in enumerate(clips):
        if c['freeze'] is not None or c['audio'] != 'voice' or c['speed'] != 1.0: continue
        o0 = int(round(c['f0'] / FPS * SR)); n = int(round((c['f1'] - c['f0']) / FPS * SR))
        s0 = int(round(c['a'] * SR)); seg = v[s0:s0 + n].copy(); n = len(seg)
        prev_cont = i > 0 and clips[i - 1]['audio'] == 'voice' and abs(clips[i - 1]['b'] - c['a']) < 1e-3
        next_cont = i + 1 < len(clips) and clips[i + 1]['audio'] == 'voice' and abs(clips[i + 1]['a'] - c['b']) < 1e-3
        fl = int(0.008 * SR); ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fl))
        if not prev_cont: seg[:fl] *= ramp
        if not next_cont: seg[-fl:] *= ramp[::-1]
        out[o0:o0 + n] += seg[: N - o0]
        if c['sec'] not in ('hook', 'cta'): speech[o0:o0 + n] = True
    return out, speech

# ---------------- loudness + true-peak limiter
def lufs(x):
    from scipy.signal import lfilter
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)
    if y.ndim == 1: y = y[:, None]
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([np.mean(y[i:i + blk] ** 2, axis=0).sum() for i in range(0, len(y) - blk, hop)])
    lk = -0.691 + 10 * np.log10(ms + 1e-12); g = ms[lk > -70]; rel = -0.691 + 10 * np.log10(g.mean()) - 10
    return -0.691 + 10 * np.log10(ms[(lk > -70) & (lk > rel)].mean())

def tp_limit(x, ceiling_db=-1.0, look=0.002, rel=0.08):
    """look-ahead limiter on the 4x-oversampled peak envelope (true peak)"""
    lim = 10 ** (ceiling_db / 20)
    up = signal.resample_poly(x, 4, 1, axis=0); pk = np.abs(up).max(axis=1).reshape(-1, 4).max(axis=1)[:len(x)]
    g = np.minimum(1.0, lim / np.maximum(pk, 1e-9))
    g = _min_ahead(g, int(look * SR))                            # gain reduction starts `look` before each peak
    a = np.exp(-1 / (rel * SR)); out = np.empty_like(g); y = 1.0
    for i, v in enumerate(g):                                   # instant attack (already looked ahead), smooth release
        y = v if v < y else a * y + (1 - a) * v; out[i] = y
    return x * out[:, None]

def _min_ahead(g, la):
    from scipy.ndimage import minimum_filter1d
    return minimum_filter1d(g, size=2 * la + 1, mode='nearest')

def finish(x, target=-14.0):
    x = x * 10 ** ((target - lufs(x)) / 20)
    x = tp_limit(x)
    return x

# ---------------- lo-fi bed (original, synthesised)
BPM = 86.0; BEAT = 60 / BPM
def rhodes(f, dur, vel):
    n = int((dur + 0.8) * SR); t = tt(n)
    I = 0.8 * np.exp(-t / 0.25) * (0.5 + 0.5 * vel) + 0.1
    y = np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * f * t))
    env = (1 - np.exp(-t / 0.006)) * (0.6 * np.exp(-t / 0.6) + 0.4 * np.exp(-t / 2.5)) * np.clip(1 - (t - dur) / 0.35, 0, 1)
    return filt(y * env, 'low', 2600) * vel

def hz(m): return 440 * 2 ** ((m - 69) / 12)
CHORDS = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]    # Fmaj7 Em7 Dm7 Cmaj7
ROOTS = [41, 40, 38, 36]
def bgm(n_samples):
    L = np.zeros(n_samples); R = np.zeros(n_samples)
    bar = 4 * BEAT; nb = int(np.ceil(n_samples / SR / bar)) + 1
    def put(x, t0, pan=0.5, g=1.0):
        i = int(t0 * SR)
        if i >= n_samples: return
        m = min(len(x), n_samples - i); L[i:i + m] += x[:m] * g * (1 - pan) * 1.4; R[i:i + m] += x[:m] * g * pan * 1.4
    for b in range(nb):
        ch = CHORDS[b % 4]; t0 = b * bar
        for j, m in enumerate(ch): put(rhodes(hz(m), 2.6 * BEAT, 0.55), t0 + 0.012 * j, 0.35 + 0.1 * j, 0.16)
        for j, m in enumerate(ch[1:]): put(rhodes(hz(m + 12), 0.4 * BEAT, 0.35), t0 + 2.5 * BEAT, 0.6, 0.07)
        r = hz(ROOTS[b % 4] + 12); n = int(3.6 * BEAT * SR); t = tt(n)
        bass = (np.sin(2 * np.pi * r * t) + 0.25 * np.sin(4 * np.pi * r * t)) * np.clip(t / 0.02, 0, 1) * np.exp(-t / 1.8)
        put(bass, t0, 0.5, 0.20)
        for k in (0, 2.5):                                              # soft kick
            n = int(0.18 * SR); t = tt(n); f = 50 + 70 * np.exp(-t / 0.03)
            put(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.07), t0 + k * BEAT, 0.5, 0.30)
        for k in (1, 3):                                                # rim
            n = int(0.07 * SR); t = tt(n)
            rim = (filt(rng.standard_normal(n), 'band', [1500, 4000]) * 0.5 + np.sin(2 * np.pi * 1800 * t)) * np.exp(-t / 0.018)
            put(rim, t0 + k * BEAT, 0.55, 0.05)
        for k in range(8):                                              # swung brushed hats
            n = int(0.05 * SR); t = tt(n); sw = 0.58 if k % 2 else 0.0
            hat = filt(rng.standard_normal(n), 'high', 6000) * np.exp(-t / 0.012)
            put(hat, t0 + (k // 2 + (sw if k % 2 else 0)) * BEAT, 0.65, 0.035 if k % 2 else 0.05)
    x = np.stack([L, R], 1)
    return filt(x, 'low', 4200)

# ---------------- SFX (original)
def sfx_pop():
    n = int(0.12 * SR); t = tt(n); f = 520 + 600 * (1 - np.exp(-t / 0.02))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035) * np.clip(t / 0.002, 0, 1)
def sfx_click():
    n = int(0.05 * SR); x = np.zeros(n)
    for o in (0, int(0.016 * SR)):
        m = int(0.003 * SR); x[o:o + m] += filt(rng.standard_normal(m), 'band', [1800, 6500]) * np.exp(-np.arange(m) / (0.0008 * SR))
    return x
def sfx_success():
    n = int(0.9 * SR); t = tt(n); y = np.zeros(n)
    for f0, d in ((1046.5, 0.0), (1568.0, 0.11)):
        i = int(d * SR); tt_ = t[: n - i]
        y[i:] += (np.sin(2 * np.pi * f0 * tt_) + 0.25 * np.sin(2 * np.pi * 3 * f0 * tt_)) * np.exp(-tt_ / 0.28) * np.clip(tt_ / 0.003, 0, 1)
    return y

def sfx_track():
    x = np.zeros((N, 2))
    def put(s, t, g):
        i = int(t * SR); m = min(len(s), N - i)
        if m > 0: x[i:i + m] += (s[:m] * g)[:, None]
    for it in OI.items():
        if it['id'] in ('hook', 'card_step1', 'cta1') or it['id'].startswith('pill_'): put(sfx_pop(), it['f0'] / FPS, 10 ** (-17 / 20))
        if it['id'] == 'res_0': put(sfx_success(), it['f0'] / FPS, 10 ** (-17 / 20))
    for cid in ('S5g3', 'S5i2'):                                       # the two clicks that finish the job
        c = TL.BY_ID[cid]; r0 = c['ring'][0][0]
        put(sfx_click(), (TL.out_frame(c, r0) + 6) / FPS, 10 ** (-26 / 20))
    return x

def duck_curve(speech):
    """gain (dB) for the bed: -6 dB while the voice talks, 60 ms attack, 450 ms release"""
    g = np.where(speech, -6.0, 0.0); dec = 48; gd = g[::dec]; out = np.empty_like(gd); y = 0.0
    aa, ar = np.exp(-1 / (0.06 * SR / dec)), np.exp(-1 / (0.45 * SR / dec))
    for i, v in enumerate(gd): a = aa if v < y else ar; y = a * y + (1 - a) * v; out[i] = y
    return np.interp(np.arange(len(g)), np.arange(0, len(g), dec)[:len(out)], out)

def write(path, x):
    pcm = (np.clip(x, -1, 1) * 32767 + rng.uniform(-0.5, 0.5, x.shape)).astype('<i2')
    with wave.open(path, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

if __name__ == '__main__':
    v, speech = voice_program()
    clean = finish(np.stack([v, v], 1)); write(os.path.join(W, 'mix_clean.wav'), clean)
    vn = np.stack([v, v], 1) * 10 ** ((-14.0 - lufs(np.stack([v, v], 1))) / 20)
    bed = bgm(N); bed = bed * 10 ** ((-33.0 - lufs(bed)) / 20)                       # ~19 dB under the voice
    t = tt(N); bed *= np.clip(t / 0.6, 0, 1)[:, None] * np.clip((t[-1] - t) / 1.8, 0, 1)[:, None]
    bed *= 10 ** (duck_curve(speech) / 20)[:, None]
    main = finish(vn + bed + sfx_track()); write(os.path.join(W, 'mix_main.wav'), main)
    np.save(os.path.join(W, 'speech_mask.npy'), speech)
    print(f'clean {lufs(clean):.1f} LUFS, main {lufs(main):.1f} LUFS; bed alone {lufs(bed):.1f} LUFS; duration {N / SR:.2f} s')
