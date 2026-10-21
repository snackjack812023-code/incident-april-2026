"""Original 120 BPM modern-tech / SaaS bed for the SmartFlow HR clip, synthesised from scratch (no samples, no licensing).
Arrangement (2 s bars = the scene grid): bar 0 tense A-minor hook (filtered, riser + snare build) | 2.0 drop on the
solution reveal | bars 1-8 C-G-Am-F groove (lift at 8.0) | 17-18 build | 18.0 impact, calm C-major close without drums.
writes work/music_raw.wav (48 kHz stereo 16-bit)"""
import os
import numpy as np
from scipy import signal
from scipy.signal import fftconvolve

SR, BPM = 48000, 120
BEAT = 60 / BPM; BAR = 4 * BEAT; DUR = 20.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def tt(n): return np.arange(n) / SR
def place(buf, x, t0, gain=1.0):
    i = int(round(t0 * SR))
    if i >= len(buf) or i < 0: return
    n = min(len(x), len(buf) - i); buf[i:i + n] += gain * x[:n]
def sos(kind, fc, order=2): return signal.butter(order, fc, kind, fs=SR, output='sos')
def filt(x, kind, fc, order=2): return signal.sosfilt(sos(kind, fc, order), x, axis=0)
def sweep(x, fc_at, kind='low', block=256, q_band=None):
    """time-varying 2nd-order filter (coefficients updated every block, state carried over)"""
    y = np.zeros_like(x); zi = None
    for i in range(0, len(x), block):
        fc = fc_at(i / SR)
        s = sos('band', [max(30, fc * q_band[0]), min(SR * 0.45, fc * q_band[1])]) if kind == 'band' else sos(kind, float(np.clip(fc, 30, SR * 0.45)))
        if zi is None: zi = np.zeros((s.shape[0], 2) + x.shape[1:])
        y[i:i + block], zi = signal.sosfilt(s, x[i:i + block], axis=0, zi=zi)
    return y
def saw(f, n, ph0=0.0):
    """band-limited (polyBLEP) sawtooth"""
    dt = f / SR; ph = (ph0 + dt * np.arange(n)) % 1.0; y = 2 * ph - 1
    a = ph < dt; x = ph[a] / dt; y[a] -= 2 * x - x * x - 1
    b = ph > 1 - dt; x = (ph[b] - 1) / dt; y[b] -= x * x + 2 * x + 1
    return y
def hz(note):
    names = {'C': -9, 'C#': -8, 'D': -7, 'D#': -6, 'E': -5, 'F': -4, 'F#': -3, 'G': -2, 'G#': -1, 'A': 0, 'A#': 1, 'B': 2}
    return 440.0 * 2 ** ((names[note[:-1]] + 12 * (int(note[-1]) - 4)) / 12)

# ---------------- instruments
def kick(vel=1.0):
    n = int(0.5 * SR); t = tt(n)
    f = 50 + 120 * np.exp(-t / 0.032) + 40 * np.exp(-t / 0.004)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22) * (1 - np.exp(-t / 0.0015))
    click = filt(rng.standard_normal(n) * np.exp(-t / 0.0025), 'high', 1800) * 0.35
    x = np.tanh(1.8 * (body + click)) / np.tanh(1.8)
    return x * np.clip((0.5 - t) / 0.05, 0, 1) * vel
def clap(vel=1.0):
    n = int(0.4 * SR); t = tt(n); env = np.zeros(n)
    for d in (0, 0.009, 0.018): env += np.where(t >= d, np.exp(-np.maximum(t - d, 0) / 0.006), 0) * 0.8
    env += np.where(t >= 0.024, np.exp(-np.maximum(t - 0.024, 0) / 0.11), 0) * 0.55
    return filt(rng.standard_normal(n), 'band', [900, 4200]) * env * vel
def hat(open_=False, vel=1.0):
    n = int((0.38 if open_ else 0.08) * SR); t = tt(n)
    return filt(rng.standard_normal(n), 'high', 7200, 4) * np.exp(-t / (0.15 if open_ else 0.021)) * vel
def snare(vel=1.0):
    n = int(0.2 * SR); t = tt(n)
    return (np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.5 + filt(rng.standard_normal(n), 'band', [1500, 7000]) * np.exp(-t / 0.07)) * vel
def bass_note(f, dur=0.22, vel=1.0):
    n = int((dur + 0.06) * SR); t = tt(n)
    x = filt(0.6 * saw(f, n) + 0.8 * np.sin(2 * np.pi * f * t), 'low', 560)
    env = (1 - np.exp(-t / 0.004)) * np.where(t < dur, 1 - 0.35 * t / dur, 0.65 * np.exp(-np.maximum(t - dur, 0) / 0.02))
    return np.tanh(1.5 * x * env) * vel
def pad_chord(freqs, dur, detune=0.14, voices=5):
    n = int((dur + 0.7) * SR); t = tt(n); L = np.zeros(n); R = np.zeros(n)
    for f in freqs:
        for v in range(voices):
            d = (v - (voices - 1) / 2) / ((voices - 1) / 2) * detune
            s = saw(f * 2 ** (d / 12), n, ph0=rng.random()); p = 0.5 + 0.38 * d / detune
            L += s * (1 - p); R += s * p
    env = np.minimum(1, t / 0.06) * np.where(t < dur, 1, np.exp(-np.maximum(t - dur, 0) / 0.2))
    return np.stack([L, R], 1) * env[:, None] / (len(freqs) * voices) * 2
def pluck(f, vel=1.0, dur=0.24, decay=1.0):
    n = int(dur * SR); t = tt(n); x = np.zeros(n)
    for k in range(1, 14):
        if f * k > 9000: break
        x += np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (10 + 7 * k) / decay)
    return x * (1 - np.exp(-t / 0.002)) * vel
def riser(dur, f0=350, f1=7500, vel=1.0):
    n = int(dur * SR); t = tt(n)
    y = sweep(rng.standard_normal(n), lambda s: f0 * (f1 / f0) ** (s / dur), kind='band', q_band=(0.7, 1.45))
    env = (t / dur) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2 * t / dur)) / SR) * 0.12 * env
    return (y * env + tone) * vel
def impact():
    n = int(2.4 * SR); t = tt(n)
    boom = np.sin(2 * np.pi * np.cumsum(32 + 45 * np.exp(-t / 0.22)) / SR) * np.exp(-t / 0.65) * (1 - np.exp(-t / 0.002))
    crash = filt(rng.standard_normal(n), 'high', 3200) * np.exp(-t / 0.75)
    return boom, crash
def reverb_ir(rt60=1.9, dur=2.4):
    n = int(dur * SR); t = tt(n)
    ir = filt(rng.standard_normal((n, 2)) * np.exp(-6.91 * t / rt60)[:, None], 'low', 5500)
    k = int(0.012 * SR); ir[:k] *= np.linspace(0, 1, k)[:, None]
    return ir / np.sqrt((ir ** 2).sum(axis=0))

# ---------------- arrangement (20.0 s = 10 bars)
CHORDS = [(0, 'Am'), (2, 'C'), (4, 'G'), (6, 'Am'), (8, 'F'), (10, 'C'), (12, 'G'), (14, 'Am'), (16, 'F'), (18, 'C')]
PAD = {'Am': ['A3', 'C4', 'E4'], 'F': ['A3', 'C4', 'F4'], 'C': ['G3', 'C4', 'E4'], 'G': ['G3', 'B3', 'D4']}
BASS = {'Am': 'A2', 'F': 'F2', 'C': 'C3', 'G': 'G2'}
ARP = {'Am': ['A4', 'C5', 'E5', 'A5'], 'F': ['A4', 'C5', 'F5', 'A5'], 'C': ['G4', 'C5', 'E5', 'G5'], 'G': ['G4', 'B4', 'D5', 'G5']}
ARP_PAT = [0, 1, 2, 3, 2, 1, 2, 3, 0, 2, 3, 2, 1, 2, 3, 1]
ARP_VEL = [1, .55, .8, .55, .9, .55, .8, .6, 1, .55, .8, .55, .9, .6, .8, .6]
GAIN = {'kick': 0.50, 'clap': 1.70, 'hats': 0.60, 'snare': 0.40, 'boom': 0.50, 'bass': 0.85, 'pads': 1.25, 'arp': 0.42, 'fx': 0.40, 'reverb': 0.45}
def chord_at(t):
    c = CHORDS[0][1]
    for t0, ch in CHORDS:
        if t >= t0: c = ch
    return c
st = {k: np.zeros(N) for k in ('kick', 'clap', 'hats', 'snare', 'boom', 'bass', 'arp')}
pads = np.zeros((N, 2)); fx = np.zeros((N, 2)); send = np.zeros((N, 2))
# drums: hook bar (kick only) -> groove 2.0-17.5 -> build stop -> single soft kick on the close
kicks = [b * BEAT for b in range(35)] + [18.0]
for k in kicks: place(st['kick'], kick(1.12 if k in (0.0, 2.0, 18.0) else 1.0), k, 0.75 if k == 18.0 else 1.0)
for b in range(4, 35):                                                           # claps on 2 & 4 from the drop
    if b % 2 == 1: c = clap(); place(st['clap'], c, b * BEAT); place(send, np.stack([c, c], 1), b * BEAT, 0.25)
for i in range(int(2.0 / (BEAT / 2)), int(17.5 / (BEAT / 2))):                  # hats from the drop to the build stop
    t = i * BEAT / 2
    if i % 2 == 1:
        op = 8.0 <= t < 16.0 and i % 4 == 1
        place(st['hats'], hat(open_=op), t, 1.0 if not op else 0.8)
    place(st['hats'], hat(vel=0.35), t + BEAT / 4)
for t in (0.5 + j * BEAT / 2 for j in range(3)): place(st['hats'], hat(vel=0.5), t, 0.6)   # light ticks in the hook bar
st['hats'] = filt(st['hats'], 'low', 12500)
for i in range(12):                                                              # snare builds: hook (1.5-2.0) and 17.0-18.0
    t = 1.5 + i * BEAT / 12
    place(st['snare'], snare(0.3 + 0.6 * i / 11), t)
for i in range(12):
    t = 17.0 + i * BEAT / 4 if i < 4 else 17.5 + (i - 4) * BEAT / 8
    if t < 17.97: place(st['snare'], snare(0.3 + 0.7 * (t - 17.0)), t)
place(st['bass'], bass_note(hz('A1'), dur=1.8), 0.0, 0.9)                      # hook: one long sub note
for b in range(4, 35):                                                           # off-beat bass in the groove
    t = b * BEAT + BEAT / 2; place(st['bass'], bass_note(hz(BASS[chord_at(t)])), t)
place(st['bass'], bass_note(hz('C2'), dur=1.6), 18.0, 0.95)
for i, (t0, ch) in enumerate(CHORDS):                                            # pads, one chord per bar (close rings out)
    t1 = CHORDS[i + 1][0] if i + 1 < len(CHORDS) else 19.6
    p = pad_chord([hz(n) for n in PAD[ch]], t1 - t0); place(pads, p, t0); place(send, p, t0, 0.30)
for s_ in range(int(2.0 / (BEAT / 4)), int(17.5 / (BEAT / 4))):                 # 16th pluck arp in the groove
    t = s_ * BEAT / 4; stp = s_ % 16; ch = chord_at(t); v = ARP_VEL[stp]
    place(st['arp'], pluck(hz(ARP[ch][ARP_PAT[stp]]), v), t)
    if 8.0 <= t < 16.0: place(st['arp'], pluck(hz(ARP[ch][ARP_PAT[stp]]) * 2, v * 0.5, dur=0.15), t)
for j, n_ in enumerate(['C5', 'E5', 'G5', 'C6', 'G5', 'E5']):                    # calm 8th-note arp on the close
    place(st['arp'], pluck(hz(n_), 0.55 - 0.05 * j, dur=0.5, decay=2.2), 18.0 + j * BEAT / 2)
boom, crash = impact()
for t, g in ((0.0, 0.55), (2.0, 0.60), (8.0, 0.40), (16.0, 0.35), (18.0, 0.60)):
    place(fx, np.stack([crash, crash], 1), t, g); place(send, np.stack([crash, crash], 1), t, 0.4)
for t, g in ((0.0, 0.9), (2.0, 0.7), (18.0, 0.8)): place(st['boom'], boom, t, g)
r = riser(1.0, f0=300, vel=1.0); place(fx, np.stack([r, r * 0.92], 1), 1.0, 1.0)
r = riser(1.0, f0=300, vel=1.0); place(fx, np.stack([r, r * 0.92], 1), 17.0, 1.05)

# ---------------- processing + mix
def sidechain(times, depth=0.62, rel=0.13):
    g = np.ones(N)
    for k in times:
        i = int(k * SR); n = min(int(0.5 * SR), N - i); g[i:i + n] = np.minimum(g[i:i + n], 1 - depth * np.exp(-np.arange(n) / SR / rel))
    return g
# hook bar: pads/arp behind a low-pass that opens into the drop; groove fully open; close slightly softer
pads = sweep(pads, lambda s: 350 * (1800 / 350) ** min(1, s / 2.0) if s < 2.0 else 2600) * sidechain(kicks)[:, None]
st['bass'] *= sidechain(kicks, depth=0.35, rel=0.08)
d = int(0.375 * SR); arp_st = np.stack([st['arp'], st['arp']], 1)
for k in range(1, 6): arp_st[k * d:, k % 2] += st['arp'][:N - k * d] * 0.36 ** k * 0.9
arp_st = filt(arp_st, 'high', 250); place(send, arp_st, 0, 0.30)
wet = np.stack([fftconvolve(send[:, c], reverb_ir()[:, c])[:N] for c in range(2)], 1)
mono = lambda x: np.stack([x, x], 1)
music = (mono(st['kick'] * GAIN['kick'] + st['clap'] * GAIN['clap'] + st['hats'] * GAIN['hats'] + st['snare'] * GAIN['snare'] + st['boom'] * GAIN['boom'] + st['bass'] * GAIN['bass'])
         + pads * GAIN['pads'] + arp_st * GAIN['arp'] + fx * GAIN['fx'] + wet * GAIN['reverb'])
music = filt(music, 'high', 28)
fade = int(0.5 * SR); music[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.6
music = np.tanh(1.1 * music / np.abs(music).max()) / np.tanh(1.1) * 0.89
import wave
out = os.path.join(ROOT, 'work', 'music_raw.wav')
pcm = (np.clip(music, -1, 1) * 32767).astype('<i2')
with wave.open(out, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('music ->', out, f'{DUR:.1f}s', 'peak', round(float(np.abs(music).max()), 3))
