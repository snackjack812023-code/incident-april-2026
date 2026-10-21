"""Audio for the edited tutorial (48 kHz stereo):
  voice : the enhanced original voice (voice_proc.npy), cut with the same snapped ranges as the picture, so every sample
          keeps its own source time (lip/click sync by construction); 8 ms fades at real cuts only (contiguous clips are
          left untouched, so no dip inside a word)
  clean : voice only -> -14 LUFS integrated, true peak <= -1 dBTP
  main  : voice + original soft-chord music at the start (hook -> STEP 1 card) and at the end ("เสร็จแล้ว!" -> CTA),
          synthesised by kit/music.py (rights-free), ~7 dB under the voice where nobody talks and dipped a further
          9 dB under the speech; the steps in between stay voice only. Plus a few soft SFX (pop on titles, 2 clicks on
          key buttons, success chime in the music's key) -> -14 LUFS, <= -1 dBTP
Writes work/mix_clean.wav, work/mix_main.wav"""
import os, sys, wave
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL, overlay_items as OI, music as MU

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

# ---------------- music (original soft chords, kit/music.py)
MUSIC_LUFS, DUCK_DB = -21.0, -9.0          # the music on its own where nobody talks, and its dip under the speech
def music_track():
    """intro from 0:00 (hook) to just into STEP 2, outro from "เสร็จแล้ว!" to the end, silent in between"""
    card, step2 = TL.BY_ID['K1']['f0'] / FPS, TL.BY_ID['S2a']['f0'] / FPS
    res = next(it for it in OI.items() if it['id'] == 'res_0')['f0'] / FPS; cta = TL.BY_ID['CTA']['f0'] / FPS
    intro, outro = MU.render(card, step2, res, cta, N / SR)
    x = np.zeros((N, 2)); x[:min(len(intro), N)] += intro[:N]
    i = int(round(res * SR)); m = min(len(outro), N - i); x[i:i + m] += outro[:m]
    return x * 10 ** ((MUSIC_LUFS - lufs(np.concatenate([intro, outro]))) / 20)

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
    for f0, d in ((1174.66, 0.0), (1760.0, 0.11)):          # D6 + A6
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

def duck_curve(speech, depth=DUCK_DB, att=0.12, rel=0.6, look=0.10):
    """gain (dB) for the music: `depth` while the voice talks (from `look` s before each talking clip), smooth
    attack / release"""
    L = int(look * SR); sp = speech.copy(); sp[:-L] |= speech[L:]
    g = np.where(sp, depth, 0.0); dec = 48; gd = g[::dec]; out = np.empty_like(gd); y = 0.0
    aa, ar = np.exp(-1 / (att * SR / dec)), np.exp(-1 / (rel * SR / dec))
    for i, v in enumerate(gd): a = aa if v < y else ar; y = a * y + (1 - a) * v; out[i] = y
    return np.interp(np.arange(len(g)), np.arange(0, len(g), dec)[:len(out)], out)

def write(path, x):
    pcm = (np.clip(x, -1, 1) * 32767 + rng.uniform(-0.5, 0.5, x.shape)).astype('<i2')
    with wave.open(path, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

if __name__ == '__main__':
    v, speech = voice_program()
    clean = finish(np.stack([v, v], 1)); write(os.path.join(W, 'mix_clean.wav'), clean)
    vn = np.stack([v, v], 1) * 10 ** ((-14.0 - lufs(np.stack([v, v], 1))) / 20)
    mus = music_track(); playing = np.abs(mus).max(1) > 1e-6
    mus *= 10 ** (duck_curve(speech) / 20)[:, None]
    main = finish(vn + mus + sfx_track()); write(os.path.join(W, 'mix_main.wav'), main)
    np.save(os.path.join(W, 'speech_mask.npy'), speech); np.save(os.path.join(W, 'music_mask.npy'), playing)
    print(f'clean {lufs(clean):.1f} LUFS, main {lufs(main):.1f} LUFS; music alone {lufs(mus[playing]):.1f} LUFS where it plays '
          f'({playing.mean() * N / SR:.1f} s); duration {N / SR:.2f} s')
