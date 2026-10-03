// Synthesises all SFX with FFmpeg lavfi (no external audio -> no licensing questions) and mixes them to audio.wav
const { spawnSync } = require('child_process'); const fs = require('fs'), path = require('path');
const S = process.env.S, D = path.join(S, 'sfx'); fs.mkdirSync(D, { recursive: true });
const SR = 48000;
function ff(args) { const r = spawnSync('ffmpeg', ['-v', 'error', '-y', ...args], { encoding: 'utf8' }); if (r.status !== 0) { console.error(args.join(' ')); console.error(r.stderr); process.exit(1); } }
function synth(name, expr, dur, post) {
  ff(['-f', 'lavfi', '-i', `aevalsrc='${expr}':s=${SR}:d=${dur}`, '-af', post, '-c:a', 'pcm_f32le', path.join(D, name + '.wav')]);
}
const TAU = '2*PI';
// hero mouse click: crisp tick + short low body + air
synth('click_main',
  `0.55*sin(${TAU}*2300*t)*exp(-t*300)+0.50*(random(0)*2-1)*exp(-t*850)+0.42*sin(${TAU}*190*t)*exp(-t*80)+0.22*sin(${TAU}*5600*t)*exp(-t*520)`,
  0.16, 'highpass=f=90,lowpass=f=11000,afade=t=out:st=0.12:d=0.04,alimiter=limit=0.95');
// softer/higher click for secondary clicks
synth('click_soft',
  `0.50*sin(${TAU}*3100*t)*exp(-t*430)+0.38*(random(0)*2-1)*exp(-t*1300)+0.16*sin(${TAU}*260*t)*exp(-t*140)`,
  0.09, 'highpass=f=150,lowpass=f=10000,afade=t=out:st=0.06:d=0.03,alimiter=limit=0.95');
// keyboard-style tick for digits
synth('key',
  `0.42*(random(0)*2-1)*exp(-t*1250)+0.38*sin(${TAU}*1650*t)*exp(-t*650)+0.18*sin(${TAU}*420*t)*exp(-t*300)`,
  0.07, 'highpass=f=200,lowpass=f=7000,afade=t=out:st=0.045:d=0.025');
// step tick (very light)
synth('tick',
  `0.45*sin(${TAU}*2600*t)*exp(-t*520)+0.2*(random(0)*2-1)*exp(-t*1500)`,
  0.06, 'highpass=f=300,lowpass=f=9000,afade=t=out:st=0.04:d=0.02');
// whoosh (soft): noise with smooth swell; low body + air layer delayed slightly (spectral motion)
synth('whoosh_soft',
  `(random(1)*2-1)*pow(sin(PI*min(1,t/0.36)),2.2)*exp(-t*1.8)`,
  0.42, 'highpass=f=380,lowpass=f=5200,equalizer=f=1400:t=q:w=0.8:g=3,afade=t=out:st=0.30:d=0.12,alimiter=limit=0.9');
// whoosh for the punch zoom (shorter, snappier)
synth('whoosh_punch',
  `(random(2)*2-1)*pow(sin(PI*min(1,t/0.22)),1.6)*exp(-t*3.5)`,
  0.26, 'highpass=f=520,lowpass=f=6500,equalizer=f=2200:t=q:w=0.9:g=3,afade=t=out:st=0.18:d=0.08,alimiter=limit=0.9');
// soft bubble pop (pitch drop)
synth('pop_soft',
  `sin(${TAU}*(300*t+800*0.02*(1-exp(-t/0.02))))*exp(-t*42)*(1-exp(-t*900))`,
  0.14, 'highpass=f=120,lowpass=f=6000,afade=t=out:st=0.10:d=0.04');
// success: pop thump + glassy major arpeggio (C6 E6 G6 C7) with a short reverb-like tail
const note = (f, o, a) => `if(gte(t,${o}),${a}*(1-exp(-(t-${o})*700))*exp(-(t-${o})*5.2)*(sin(${TAU}*${f}*(t-${o}))+0.33*sin(${TAU}*${2 * f}*(t-${o}))+0.11*sin(${TAU}*${3 * f}*(t-${o}))),0)`;
const thump = `0.55*sin(${TAU}*(170*t+520*0.018*(1-exp(-t/0.018))))*exp(-t*38)*(1-exp(-t*1200))`;
synth('success',
  [thump, note(1046.5, 0, 0.42), note(1318.5, 0.075, 0.40), note(1568, 0.15, 0.40), note(2093, 0.235, 0.26)].join('+'),
  1.35, 'highpass=f=140,aecho=0.8:0.55:70|140|230:0.34|0.22|0.12,afade=t=out:st=1.0:d=0.35,alimiter=limit=0.95');
console.log('sfx synthesized:', fs.readdirSync(D).filter(f => f.endsWith('.wav')).join(' '));

// ---------------- mix ----------------
const spec = require('./spec.js');
function peakDb(file) {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', file, '-af', 'astats=metadata=0:reset=0', '-f', 'null', '-'], { encoding: 'utf8' });
  const m = /Peak level dB:\s*(-?[\d.]+)/.exec(r.stderr); return parseFloat(m[1]);
}
const peaks = {}; for (const e of spec.sfxEvents) if (!(e.name in peaks)) peaks[e.name] = peakDb(path.join(D, e.name + '.wav'));
const total = 14.90;
const ins = [], fl = [];
spec.sfxEvents.forEach((e, i) => {
  ins.push('-i', path.join(D, e.name + '.wav'));
  const t = Math.max(0, e.f / 30 - spec.LEAD + (e.off || 0)), ms = Math.round(t * 1000), g = e.peak - peaks[e.name];
  fl.push(`[${i}:a]volume=${g.toFixed(2)}dB,adelay=${ms}|${ms},aformat=sample_fmts=fltp:channel_layouts=mono[a${i}]`);
});
const n = spec.sfxEvents.length;
fl.push(`${spec.sfxEvents.map((_, i) => `[a${i}]`).join('')}amix=inputs=${n}:normalize=0:duration=longest,apad=whole_dur=${total},atrim=end=${total},alimiter=limit=0.89:level=false,pan=stereo|c0=c0|c1=c0,aformat=sample_fmts=fltp:sample_rates=${SR}[mix]`);
ff([...ins, '-filter_complex', fl.join(';'), '-map', '[mix]', '-c:a', 'pcm_f32le', path.join(S, 'audio.wav')]);
const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', path.join(S, 'audio.wav'), '-af', 'astats=metadata=0:reset=0,volumedetect', '-f', 'null', '-'], { encoding: 'utf8' });
console.log('mix:', (r.stderr.match(/(Peak level dB|RMS level dB|mean_volume|max_volume):[^\n]*/g) || []).slice(0, 6).join(' | '));
console.log('events:', spec.sfxEvents.map(e => `${(e.f / 30 - spec.LEAD + (e.off || 0)).toFixed(2)}s ${e.name}@${e.peak}`).join(', '));
