"""Measurement QA of the edited audio (no listening possible): splices, word safety at cuts, dead air, bed vs voice."""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL, mixdown as MX

SR, FPS = 48000, TL.FPS
def load(p):
    with wave.open(p) as w: x = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2) / 32768.0
    return x.mean(1)
clean, main = load(os.path.join(TL.W, 'mix_clean.wav')), load(os.path.join(TL.W, 'mix_main.wav'))
v = np.load(os.path.join(TL.W, 'voice_proc.npy')).astype(np.float64)

def rms_db(x): return 20 * np.log10(np.sqrt(np.mean(x * x)) + 1e-12)
# 1) every real cut: energy of the SOURCE around both sides of the cut (a word cut shows up as loud audio at the edge)
cuts = []
for i in range(1, len(TL.CLIPS)):
    p, c = TL.CLIPS[i - 1], TL.CLIPS[i]
    if p['audio'] == 'voice' and c['audio'] == 'voice' and abs(p['b'] - c['a']) < 1e-3: continue      # continuous
    t_out = c['f0'] / FPS
    e_out = rms_db(v[int((p['b'] - 0.02) * SR):int(p['b'] * SR)]) if p['audio'] == 'voice' and p['freeze'] is None else -120
    e_in = rms_db(v[int(c['a'] * SR):int((c['a'] + 0.02) * SR)]) if c['audio'] == 'voice' and c['freeze'] is None else -120
    cuts.append((t_out, p['id'], c['id'], e_out, e_in))
worst = max(cuts, key=lambda r: max(r[3], r[4]))
print(f'{len(cuts)} cuts; loudest 20 ms at a cut edge: {max(worst[3], worst[4]):.1f} dBFS ({worst[1]}->{worst[2]} at {worst[0]:.2f}s)')
for r in sorted(cuts, key=lambda r: -max(r[3], r[4]))[:6]: print(f'   {r[0]:7.2f}s {r[1]:>5}->{r[2]:<5} out-edge {r[3]:6.1f}  in-edge {r[4]:6.1f} dBFS')
# 2) clicks: sample steps relative to the local level, around every cut in the final mixes
for name, x in (('clean', clean), ('main', main)):
    worst = 0
    for t_out, *_ in cuts:
        i = int(t_out * SR); seg = x[max(0, i - 480):i + 480]; d = np.abs(np.diff(seg))
        loc = np.sqrt(np.mean(seg * seg)) + 1e-4; worst = max(worst, d.max() / loc)
    print(f'{name}: max sample step / local RMS at cuts = {worst:.2f} (a click would be >> 1)')
# 3) dead air: stretches quieter than -45 dBFS (50 ms RMS) longer than 1.0 s in the clean version
hop = int(0.05 * SR); r = 20 * np.log10(np.sqrt((clean[: len(clean) // hop * hop].reshape(-1, hop) ** 2).mean(1)) + 1e-9)
q = r < -45; runs = []; i = 0
while i < len(q):
    if q[i]:
        j = i
        while j < len(q) and q[j]: j += 1
        if (j - i) * 0.05 >= 1.0: runs.append((i * 0.05, j * 0.05, TL.clip_at(int(i * 0.05 * FPS))['id']))
        i = j
    else: i += 1
print('quiet stretches >= 1.0 s (clean):', ', '.join(f'{a:.1f}-{b:.1f}s [{c}]' for a, b, c in runs) or 'none')
# 4) music vs voice in the main mix (the music plays only at the start and the end)
sp = np.load(os.path.join(TL.W, 'speech_mask.npy'))
mp = os.path.join(TL.W, 'music_mask.npy'); mm = np.load(mp) if os.path.exists(mp) else np.ones_like(sp)
k = float(np.dot(main[sp], clean[sp]) / np.dot(clean[sp], clean[sp])); diff = main - k * clean      # music + sfx alone
both, alone = sp & mm, mm & ~sp
print(f'main mix: music+sfx under the speech (where the music plays) {rms_db(diff[both]) - rms_db(k * clean[both]):.1f} dB re the voice; '
      f'music where nobody talks {rms_db(main[alone]) - rms_db(k * clean[sp]):.1f} dB re the voice level')
