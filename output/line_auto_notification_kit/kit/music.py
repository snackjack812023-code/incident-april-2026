"""Original 120 BPM modern-tech / corporate music for the SmartFlow LINE clip, synthesised from scratch (no samples,
nothing to license). Bars are 2 s and follow the edit:
  bar 0 hook: beat from the first frame (kick, off-beat bass), pads/hats behind an opening low-pass
  bars 1-2 build-up: 16th pluck arp + claps | bar 3: snare roll + riser, everything stops just before the LINE card
  arrives (7.61 s) so the notification sound stands alone, a soft sub-drop under it
  bars 4-6 hero + proof: the groove comes back on 8.0 s (arp an octave up in bars 5-6), a fill into the 10 s transition
  bar 7 CTA, bar 8: final C chord on 16.0 s and a short fade-out to 17.0 s.   Chords: Am F C G Am F C G C
writes work/music.wav (48 kHz stereo float32 -> 16-bit)"""
import os, wave
import numpy as np
from scipy import signal
from scipy.signal import fftconvolve

SR, BPM = 48000, 120
BEAT = 60 / BPM; BAR = 4 * BEAT; DUR = 17.0
N = int(SR * DUR)
rng = np.random.default_rng(1121)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOP, BACK = 7.55, 8.0                      # the music stops for the LINE card, the groove returns on bar 4

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
    return np.tanh(1.8 * (body + click)) / np.tanh(1.8) * np.clip((0.5 - t) / 0.05, 0, 1) * vel
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
def riser(dur, f0=350, f1=7000, vel=1.0):
    n = int(dur * SR); t = tt(n)
    y = sweep(rng.standard_normal(n), lambda s: f0 * (f1 / f0) ** (s / dur), kind='band', q_band=(0.7, 1.45))
    env = (t / dur) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2 * t / dur)) / SR) * 0.12 * env
    return (y * env + tone) * vel
def subdrop(dur=0.7):
    n = int(dur * SR); t = tt(n)
    return np.sin(2 * np.pi * np.cumsum(90 * (35 / 90) ** (t / dur)) / SR) * np.exp(-t / 0.35) * (1 - np.exp(-t / 0.003))
def reverb_ir(rt60=1.7, dur=2.2):
    n = int(dur * SR); t = tt(n)
    ir = filt(rng.standard_normal((n, 2)) * np.exp(-6.91 * t / rt60)[:, None], 'low', 5500)
    k = int(0.012 * SR); ir[:k] *= np.linspace(0, 1, k)[:, None]
    return ir / np.sqrt((ir ** 2).sum(axis=0))

# ---------------- arrangement
CHORDS = ['Am', 'F', 'C', 'G', 'Am', 'F', 'C', 'G', 'C']
PAD = {'Am': ['A3', 'C4', 'E4'], 'F': ['A3', 'C4', 'F4'], 'C': ['G3', 'C4', 'E4'], 'G': ['G3', 'B3', 'D4']}
BASS = {'Am': 'A2', 'F': 'F2', 'C': 'C3', 'G': 'G2'}
ARP = {'Am': ['A4', 'C5', 'E5', 'A5'], 'F': ['A4', 'C5', 'F5', 'A5'], 'C': ['G4', 'C5', 'E5', 'G5'], 'G': ['G4', 'B4', 'D5', 'G5']}
ARP_PAT = [0, 1, 2, 3, 2, 1, 2, 3, 0, 2, 3, 2, 1, 2, 3, 1]
ARP_VEL = [1, .55, .8, .55, .9, .55, .8, .6, 1, .55, .8, .55, .9, .6, .8, .6]
GAIN = {'kick': 0.50, 'clap': 1.55, 'hats': 0.60, 'snare': 0.40, 'sub': 0.45, 'bass': 0.95, 'pads': 1.15, 'arp': 0.42, 'fx': 0.38, 'reverb': 0.42}
def chord_at(t): return CHORDS[min(len(CHORDS) - 1, int(t // BAR))]
def playing(t): return t < 7.0 or t >= BACK                       # groove gap 7.0-8.0 (roll, riser, the card)

if __name__ == '__main__':
    M = lambda: np.zeros(N)
    st = {k: M() for k in ('kick', 'clap', 'hats', 'snare', 'sub', 'bass', 'arp')}
    pads = np.zeros((N, 2)); fx = np.zeros((N, 2)); send = np.zeros((N, 2))
    kicks = [b * BEAT for b in range(33) if playing(b * BEAT)]
    for k in kicks: place(st['kick'], kick(1.08 if k in (0.0, BACK, 16.0) else 1.0), k)
    for b in range(33):                                                   # claps on 2 & 4 from bar 1
        t = b * BEAT
        if b % 2 == 1 and (2.0 <= t < 6.0 or BACK <= t < 16.0):
            c = clap(); place(st['clap'], c, t); place(send, np.stack([c, c], 1), t, 0.25)
    for i in range(int(16.0 / (BEAT / 2))):                               # hats: off-beat 8ths + 16th ghosts from bar 1
        t = i * BEAT / 2
        if not playing(t): continue
        if i % 2 == 1:
            op = 8.0 <= t < 14.0 and i % 4 == 1
            place(st['hats'], hat(open_=op), t, 1.0 if not op else 0.8)
        if t >= 2.0: place(st['hats'], hat(vel=0.35), t + BEAT / 4)
    st['hats'] = filt(st['hats'], 'low', 12500)
    roll = [6.0, 6.25, 6.5, 6.75, 7.0, 7.125, 7.25, 7.3125, 7.375, 7.4375]          # 8ths -> 16ths -> 32nds
    for t in roll: place(st['snare'], snare(0.3 + 0.7 * (t - 6.0) / 1.5), t)
    for t in (9.5, 9.625, 9.75, 9.875): place(st['snare'], snare(0.45 + 0.4 * (t - 9.5) / 0.4), t)   # fill into the transition
    for t in (15.5, 15.75): place(st['snare'], snare(0.6), t)
    for b in range(33):                                                   # off-beat bass
        t = b * BEAT + BEAT / 2
        if t < 16.0 and playing(t): place(st['bass'], bass_note(hz(BASS[chord_at(t)])), t)
    place(st['bass'], bass_note(hz('C2'), dur=0.9), 16.0, 0.9)
    for bi, ch in enumerate(CHORDS):                                      # pads, one chord per bar (gap 7.0-8.0)
        t0 = bi * BAR; dur = 1.0 if bi == 3 else (BAR if bi < len(CHORDS) - 1 else 0.9)
        p = pad_chord([hz(n) for n in PAD[ch]], dur); place(pads, p, t0); place(send, p, t0, 0.30)
    for s_ in range(int(2.0 / (BEAT / 4)), int(16.0 / (BEAT / 4))):     # 16th pluck arp
        t = s_ * BEAT / 4; stp = s_ % 16; ch = chord_at(t)
        if not playing(t): continue
        v = ARP_VEL[stp]
        place(st['arp'], pluck(hz(ARP[ch][ARP_PAT[stp]]), v), t)
        if 10.0 <= t < 14.0: place(st['arp'], pluck(hz(ARP[ch][ARP_PAT[stp]]) * 2, v * 0.5, dur=0.15), t)
    for n_ in ('C4', 'E4', 'G4', 'C5', 'E5'): place(st['arp'], pluck(hz(n_), 0.6, dur=0.9, decay=3.0), 16.0)   # final stab
    r = riser(STOP - 5.8); place(fx, np.stack([r, r * 0.92], 1), 5.8, 1.0)
    place(st['sub'], subdrop(), 7.6)

    def sidechain(times, depth=0.6, rel=0.13):
        g = np.ones(N)
        for k in times:
            i = int(k * SR); n = min(int(0.5 * SR), N - i); g[i:i + n] = np.minimum(g[i:i + n], 1 - depth * np.exp(-np.arange(n) / SR / rel))
        return g
    pads = sweep(pads, lambda s: 2600 if s >= 2.0 else 380 * (2600 / 380) ** (s / 2.0)) * sidechain(kicks)[:, None]
    st['bass'] *= sidechain(kicks, depth=0.35, rel=0.08)
    d = int(0.375 * SR); arp_st = np.stack([st['arp'], st['arp']], 1)     # dotted-8th ping-pong delay on the arp
    for k in range(1, 6): arp_st[k * d:, k % 2] += st['arp'][:N - k * d] * 0.36 ** k * 0.9
    arp_st = filt(arp_st, 'high', 250); place(send, arp_st, 0, 0.30)
    wet = np.stack([fftconvolve(send[:, c], reverb_ir()[:, c])[:N] for c in range(2)], 1)
    mono = lambda x: np.stack([x, x], 1)
    rest = (mono(st['clap'] * GAIN['clap'] + st['hats'] * GAIN['hats'] + st['snare'] * GAIN['snare'] + st['sub'] * GAIN['sub']
                 + st['bass'] * GAIN['bass']) + pads * GAIN['pads'] + arp_st * GAIN['arp'] + fx * GAIN['fx'] + wet * GAIN['reverb'])
    seg = int(2.05 * SR)                                                  # bar 0: all but kick + bass behind an opening low-pass
    hook_bass = mono(st['bass'] * GAIN['bass']); rest_hook = rest[:seg] - hook_bass[:seg]
    rest[:seg] = sweep(rest_hook, lambda s: 600 * (16000 / 600) ** min(1, s / 2.0) ** 1.6) + hook_bass[:seg]
    music = filt(mono(st['kick'] * GAIN['kick']) + rest, 'high', 28)
    i0, i1 = int((STOP - 0.01) * SR), int(STOP * SR)                      # hard stop of the riser/roll tails for the card
    keep = np.ones(N); keep[i0:i1] = np.linspace(1, 0, i1 - i0); keep[i1:int(BACK * SR)] = 0
    tail = np.zeros((N, 2)); tail[:, 0] = tail[:, 1] = st['sub'] * GAIN['sub']               # the sub-drop stays
    music = music * keep[:, None] + tail * (1 - keep)[:, None]
    f0 = int(16.2 * SR); music[f0:] *= (0.5 + 0.5 * np.cos(np.pi * np.linspace(0, 1, N - f0)))[:, None]   # fade-out
    music = np.tanh(1.1 * music / np.abs(music).max()) / np.tanh(1.1) * 0.89
    out = os.path.join(ROOT, 'work', 'music.wav')
    pcm = (np.clip(music, -1, 1) * 32767).astype('<i2')
    with wave.open(out, 'wb') as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print('music ->', out, f'{DUR:.1f}s', 'peak', round(float(np.abs(music).max()), 3))
