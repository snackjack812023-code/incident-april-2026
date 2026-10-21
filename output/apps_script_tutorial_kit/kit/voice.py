"""Natural voice enhancement of the phone recording, on the SOURCE timeline (cuts happen afterwards, so no filter
ever starts mid-word). The speaker's own voice is kept: no voice change, no AI voice, only gentle repair + EQ +
dynamics.
  1. ffmpeg: L+R -> mono (the two channels are identical), declip (the phone AGC flat-topped ~1.8k peaks),
     4th-order high-pass 75 Hz (rumble / handling / 50-60 Hz), light FFT denoise (max 6 dB, no gating -> no robot voice)
  2. numpy: EQ (-2.5 dB @ 280 Hz de-mud, +3.5 dB @ 3 kHz presence, +1 dB shelf above 7.5 kHz), split-band de-esser
     (5-10 kHz, only acts when sibilance sticks out), soft-knee RMS compressor (2:1), slow leveller on the phrases
     (max +-4 dB) so every take sits at the same level.
Writes work/voice_proc.wav (float32 mono 48 kHz, ~-18 dBFS speech RMS, peaks well below 0 dBFS; the final loudness
normalise + true-peak limit happen on the edited programme)."""
import os, subprocess, sys, wave
import numpy as np
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', '20261018_205830.mp4'); W = os.path.join(ROOT, 'work')
SR = 48000

def ff_stage():
    af = ('pan=mono|c0=0.5*c0+0.5*c1,aformat=sample_fmts=fltp,adeclip=w=55:o=75:a=8:t=10:n=1000:m=a,'
          'highpass=f=75:poles=2,highpass=f=75:poles=2,afftdn=nr=6:nf=-56:tn=1')
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', SRC, '-vn', '-af', af, '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)

def biquad(kind, f0, gain_db, q):
    """RBJ cookbook biquad -> sos row"""
    A = 10 ** (gain_db / 40); w0 = 2 * np.pi * f0 / SR; cw, sw = np.cos(w0), np.sin(w0); al = sw / (2 * q)
    if kind == 'peak':
        b = [1 + al * A, -2 * cw, 1 - al * A]; a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == 'highshelf':
        sA = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * cw + sA), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sA)]
        a = [(A + 1) - (A - 1) * cw + sA, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sA]
    b, a = np.array(b) / a[0], np.array(a) / a[0]; return np.concatenate([b, a])

EQ = np.array([biquad('peak', 280, -2.5, 1.0), biquad('peak', 3000, 3.5, 0.8), biquad('highshelf', 7500, 1.0, 0.7)])

def movavg(v, n):
    """centred moving average (cumulative sum: O(N) for any window)"""
    c = np.concatenate([[0.0], np.cumsum(v)]); i = np.arange(len(v)); lo = np.clip(i - n // 2, 0, len(v)); hi = np.clip(i - n // 2 + n, 0, len(v))
    return (c[hi] - c[lo]) / np.maximum(hi - lo, 1)

def env_db(x, win_s):
    return 10 * np.log10(movavg(x * x, max(1, int(win_s * SR))) + 1e-12)

def smooth_gain(g_db, att_s, rel_s, rate):
    """one-pole attack/release smoothing of a gain-reduction curve (dB, <= 0) sampled at `rate` Hz"""
    out = np.empty_like(g_db); a_att = np.exp(-1 / (att_s * rate)); a_rel = np.exp(-1 / (rel_s * rate)); y = 0.0
    for i, v in enumerate(g_db):                       # numba-free loop on a decimated curve (called with ~1 kHz rate)
        a = a_att if v < y else a_rel; y = a * y + (1 - a) * v; out[i] = y
    return out

def deesser(x, lo=5000, hi=10000, thresh=-10.0, max_cut=6.0):
    """reduce the 5-10 kHz band only when it rises above `thresh` dB relative to the broadband level"""
    sos = signal.butter(4, [lo, hi], 'bandpass', fs=SR, output='sos'); band = signal.sosfiltfilt(sos, x)
    rel = env_db(band, 0.004) - env_db(x, 0.004)
    speech = env_db(x, 0.03) > -45                                                # never act on pauses (hiss there is HF-heavy)
    over = np.clip(rel - thresh, 0, None) * speech; cut = -np.minimum(over * 1.5, max_cut)
    dec = 48; c = smooth_gain(cut[::dec], 0.001, 0.04, SR / dec)                  # 1 kHz control rate
    cut = np.interp(np.arange(len(x)), np.arange(0, len(x), dec)[:len(c)], c)
    return x + band * (10 ** (cut / 20) - 1), float((cut[speech] < -1).mean())

def compressor(x, thresh=-20.0, ratio=2.0, knee=6.0, att=0.008, rel=0.15):
    lvl = env_db(x, 0.02); over = lvl - thresh
    gr = np.where(over <= -knee / 2, 0.0, np.where(over >= knee / 2, -(over) * (1 - 1 / ratio), -((over + knee / 2) ** 2) / (2 * knee) * (1 - 1 / ratio)))
    dec = 48; g = smooth_gain(gr[::dec], att, rel, SR / dec)
    g = np.interp(np.arange(len(x)), np.arange(0, len(x), dec)[:len(g)], g)
    return x * 10 ** (g / 20), g

def leveller(x, max_db=4.0):
    """slow phrase leveller: 1.5 s RMS of the speech, gated, nudged toward the median speech level, +-max_db,
    400 ms ramps (evens out takes recorded at different distances; leaves the delivery's own dynamics)"""
    lvl = env_db(x, 1.5); speech = env_db(x, 0.05) > -45; target = np.median(lvl[speech])
    g = np.clip(target - lvl, -max_db, max_db); g = np.where(speech, g, np.nan)
    idx = np.arange(len(x)); ok = ~np.isnan(g); g = np.interp(idx, idx[ok], g[ok])            # hold through pauses
    g = movavg(g, int(0.4 * SR))
    return x * 10 ** (g / 20), g

def main():
    x = ff_stage()
    x = signal.sosfilt(EQ, x)
    x, ds_frac = deesser(x)
    x, gr = compressor(x)
    x, lv = leveller(x)
    pk = np.abs(x).max(); x *= 10 ** (-3 / 20) / max(pk, 1e-9) if pk > 10 ** (-3 / 20) else 1.0
    with wave.open(os.path.join(W, 'voice_proc.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    np.save(os.path.join(W, 'voice_proc.npy'), x.astype(np.float32))
    speech = env_db(x, 0.05) > -40
    print(f'de-esser active {100 * ds_frac:.1f}% of speech; compressor GR median {np.median(gr[speech]):.1f} dB, p95 {np.percentile(gr[speech], 5):.1f} dB; '
          f'leveller gain range {lv.min():+.1f}..{lv.max():+.1f} dB; peak {20 * np.log10(np.abs(x).max()):.1f} dBFS')

if __name__ == '__main__':
    main()
