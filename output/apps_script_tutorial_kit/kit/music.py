"""Original soft-chord music for the start and the end of the main mix, synthesised here: no samples, no downloads,
nothing to license. Gentle "royal road" chords in D major (IV-V-iii-vi) on soft felt keys, a warm pad and a few
music-box notes from the D major pentatonic, in a synthetic room.
  intro : 8 bars from 0:00 (the hook) under the intro talk; the 9th chord lands on the STEP 1 card and rings out
  outro : starts on "เสร็จแล้ว!" (I chord, with the success chime) and resolves (ii-V-I) on the CTA
Each section's tempo (~81-83 BPM) is set so that its phrase lands on those two moments of the edit."""
import numpy as np
from scipy import signal

SR = 48000
RNG = np.random.default_rng(1207)

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def filt(x, kind, fc, order=2): return signal.sosfilt(signal.butter(order, fc, kind, fs=SR, output='sos'), x, axis=0)

# right hand (felt keys), left hand (root, fifth), music-box notes (D major pentatonic tones of the chord)
CHORDS = {
    'Dmaj9': ((61, 64, 66, 69), (38, 45), (74, 76, 78, 81)),
    'Gmaj9': ((59, 62, 66, 69), (43, 50), (74, 78, 81, 83)),
    'A6/9':  ((61, 64, 66, 71), (45, 52), (76, 78, 81, 83)),
    'F#m7':  ((61, 64, 66, 69), (42, 49), (73, 76, 78, 81)),
    'Bm9':   ((57, 61, 62, 66), (35, 42), (73, 74, 78, 81)),
    'Em9':   ((62, 66, 67, 71), (40, 47), (74, 76, 78, 83)),
}
INTRO = ['Gmaj9', 'A6/9', 'F#m7', 'Bm9', 'Gmaj9', 'A6/9', 'Dmaj9', 'Bm9', 'Gmaj9']    # the last one rings out
OUTRO = ['Dmaj9', 'Gmaj9', 'A6/9', 'F#m7', 'Bm9', 'Gmaj9', 'Em9', 'A6/9', 'Dmaj9']     # ii-V-I on the CTA

def keys(f, gate, vel):
    """soft felt keys: slightly inharmonic partials, the upper ones die first, softer playing is darker; damper at gate"""
    n = int((gate + 0.5) * SR) + 1; t = np.arange(n) / SR
    T0 = float(np.clip(3.0 * (220.0 / f) ** 0.4, 1.0, 5.0)); y = np.zeros(n)
    for k in range(1, 9):
        fk = k * f * np.sqrt(1 + 0.00012 * k * k)
        if fk > 8000: break
        y += k ** -1.4 * (0.35 + 0.5 * vel) ** (k - 1) * np.sin(2 * np.pi * fk * t + RNG.uniform(0, 2 * np.pi)) \
             * np.exp(-t * (1 + 0.6 * (k - 1)) / T0)
    a = np.clip(t / 0.006, 0, 1); y *= 0.5 - 0.5 * np.cos(np.pi * a)
    y *= np.where(t < gate, 1.0, np.exp(-(t - gate) / 0.11))
    y += filt(RNG.standard_normal(n), 'low', 900) * np.exp(-t / 0.012) * 0.04       # felt hammer
    return y * vel

def pad(notes, dur):
    """warm string-like pad: 4 harmonics per note, 3 detuned voices spread left/centre/right, slow swell + release"""
    n = int((dur + 2.6) * SR); t = np.arange(n) / SR; out = np.zeros((n, 2))
    for m in notes:
        f = hz(m)
        for det, pan in ((-0.0035, 0.2), (0.0, 0.5), (0.0035, 0.8)):
            ph = RNG.uniform(0, 2 * np.pi, 4)
            s = sum(np.sin(2 * np.pi * k * f * (1 + det) * t + ph[k - 1]) / k ** 1.6 for k in range(1, 5))
            out[:, 0] += s * np.sqrt(1 - pan); out[:, 1] += s * np.sqrt(pan)
    att = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / 1.4, 0, 1))
    rel = 0.5 + 0.5 * np.cos(np.pi * np.clip((t - dur) / 2.4, 0, 1))
    return filt(out * (att * rel)[:, None], 'low', 1500)

def musicbox(f, vel):
    n = int(2.4 * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.0) + 0.18 * np.sin(4 * np.pi * f * t) * np.exp(-t / 0.45)
         + 0.07 * np.sin(6 * np.pi * f * t) * np.exp(-t / 0.25) + 0.05 * np.sin(2 * np.pi * 4.16 * f * t) * np.exp(-t / 0.12))
    return y * np.clip(t / 0.0015, 0, 1) * vel

def low_shelf(x, f0=120.0, gain_db=-3.0):
    """RBJ low shelf (S = 1): keeps the left hand warm without boom under the voice"""
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; c, al = np.cos(w), np.sin(w) / 2 * np.sqrt(2); r = 2 * np.sqrt(A) * al
    b = np.array([A * ((A + 1) - (A - 1) * c + r), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - r)])
    a = np.array([(A + 1) + (A - 1) * c + r, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - r])
    return signal.lfilter(b / a[0], a / a[0], x, axis=0)

def room_ir(rt60=2.2):
    """synthetic stereo room: decorrelated noise per channel, highs decay faster, 22 ms pre-delay, unit energy"""
    n = int(rt60 * 1.1 * SR); t = np.arange(n) / SR; rng = np.random.default_rng(31); ir = np.zeros((n, 2))
    for ch in range(2):
        x = rng.standard_normal(n)
        ir[:, ch] = (filt(x, 'low', 900) * np.exp(-t * 6.91 / rt60) + 0.8 * filt(x, 'band', [900, 4000]) * np.exp(-t * 6.91 / (0.75 * rt60))
                     + 0.5 * filt(x, 'high', 4000) * np.exp(-t * 6.91 / (0.45 * rt60)))
    ir *= np.clip(t / 0.005, 0, 1)[:, None]
    ir = np.vstack([np.zeros((int(0.022 * SR), 2)), ir])
    return ir / np.sqrt((ir ** 2).sum(0))

def section(prog, bar, tail, fade, stems=False):
    """one musical section: len(prog)-1 bars of `bar` s, then the last chord held `tail` s; last `fade` s faded out"""
    beat = bar / 4; n = int(((len(prog) - 1) * bar + tail) * SR) + 1
    K = np.zeros((n, 2)); P = np.zeros((n, 2)); B = np.zeros((n, 2))
    hum = lambda: RNG.normal(0, 0.006)
    def put(dst, x, t0, pan=0.5):
        i = max(0, int(round(t0 * SR))); m = min(len(x), n - i)
        if m <= 0: return
        if x.ndim == 1: dst[i:i + m, 0] += x[:m] * np.sqrt(1 - pan); dst[i:i + m, 1] += x[:m] * np.sqrt(pan)
        else: dst[i:i + m] += x[:m]
    for b, name in enumerate(prog):
        rh, lh, mb = CHORDS[name]; t0 = b * bar; last = b == len(prog) - 1
        gate = tail - 0.4 if last else bar * 0.97
        for j, m in enumerate(rh):                                     # rolled chord on 1, low to high, spread L->R
            put(K, keys(hz(m), gate, 0.52 + RNG.normal(0, 0.03)), t0 + 0.024 * j + abs(hum()), 0.36 + 0.09 * j)
        put(K, keys(hz(lh[0]), gate, 0.42), t0 + abs(hum()), 0.45)       # left hand: root on 1 ...
        if last:
            put(K, keys(hz(lh[1]), gate, 0.34), t0 + 0.03, 0.5)
        else:
            put(K, keys(hz(lh[1]), beat * 1.8, 0.32), t0 + 2 * beat + hum(), 0.5)      # ... fifth on 3
            for j, m in enumerate(rh[2:]):                              # soft repeat of the top two on the "and" of 3
                put(K, keys(hz(m), beat * 1.2, 0.27), t0 + 2.5 * beat + 0.016 * j + hum(), 0.55 + 0.1 * j)
        put(P, pad((lh[0] + 12,) + tuple(rh[:3]), (tail - 1.8) if last else bar * 0.98), t0)
        notes = sorted(mb)
        if last:                                                        # slow falling arpeggio over the last chord
            for j, m in enumerate(reversed(notes + [notes[0] + 12])):
                put(B, musicbox(hz(m), 0.30 - 0.04 * j), t0 + 0.6 + 0.75 * beat * j + hum(), 0.3 + 0.1 * j)
        else:                                                           # a little rising figure in every bar
            for j, (pos, idx, v) in enumerate(((1.0, 0, 0.30), (1.5, 1, 0.24), (2.0, 2, 0.28), (3.0, 1, 0.20))):
                put(B, musicbox(hz(notes[idx] if b % 2 == 0 else notes[idx + 1]), v), t0 + pos * beat + hum(), 0.3 + 0.13 * j)
    ir = room_ir()
    wet = lambda x, s: np.stack([signal.fftconvolve(x[:, c], ir[:, c])[:n] for c in range(2)], 1) * s
    parts = ((K + wet(K, 0.32)) * 1.0, (P + wet(P, 0.5)) * 0.06, (B + wet(B, 0.45)) * 1.5)
    if stems: return parts
    out = sum(parts)
    out = low_shelf(filt(filt(out, 'high', 40), 'low', 9000))
    t = np.arange(n) / SR; T = n / SR
    out *= (0.5 + 0.5 * np.cos(np.pi * np.clip((t - (T - fade)) / fade, 0, 1)))[:, None]
    return out

def render(intro_end, step2_start, outro_start, cta_start, total):
    """intro: 8 bars from 0 to the STEP 1 card, the last chord rings into STEP 2; outro: 8 bars from "เสร็จแล้ว!" to
    the CTA, the last chord rings to the end of the video. Returns (intro, outro) stereo arrays (place at 0 and
    outro_start)."""
    intro = section(INTRO, intro_end / 8, step2_start + 1.5 - intro_end, 1.6)
    outro = section(OUTRO, (cta_start - outro_start) / 8, total - cta_start, 1.6)
    return intro, outro
