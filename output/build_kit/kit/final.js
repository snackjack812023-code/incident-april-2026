// Final assembly: plate + overlay PNG sequence + SFX (+ optional licensed BGM found in the project folder)
// -> H.264/AAC MP4 (1080x1920, 30fps, BT.709)
const { spawnSync } = require('child_process'); const fs = require('fs'), path = require('path');
const S = process.env.S; const { N } = require('./spec.js');
const frames = parseInt(process.env.FRAMES || String(N), 10);
const out = process.env.OUT || path.join(S, 'final_test.mp4');
const dur = (frames / 30).toFixed(4);

// BGM is used ONLY if the user placed a (licensed) music file in the project folder (or MUSIC_FILE/MUSIC_DIR).
function findMusic() {
  if (process.env.MUSIC_FILE) return fs.existsSync(process.env.MUSIC_FILE) ? process.env.MUSIC_FILE : null;
  const dirs = [process.env.MUSIC_DIR, process.env.REPO, process.env.REPO && path.join(process.env.REPO, 'music')].filter(Boolean);
  for (const d of dirs) {
    if (!fs.existsSync(d)) continue;
    const hit = fs.readdirSync(d).filter(f => /\.(mp3|wav|m4a|aac|flac|ogg)$/i.test(f)).sort()[0];
    if (hit) return path.join(d, hit);
  }
  return null;
}
const music = process.env.NOAUDIO ? null : findMusic();

const g = [
  `[0:v]setpts=N/(30*TB),format=yuv420p[v0]`,
  `[1:v]setpts=N/(30*TB),format=rgba,scale=out_color_matrix=bt709:out_range=tv:flags=bicubic+accurate_rnd,format=yuva420p[ov]`,
  `[v0][ov]overlay=0:0:format=yuv420:eof_action=pass,format=yuv420p,setsar=1[vout]`,
];
const args = ['-v', 'error', '-stats', '-y',
  '-i', process.env.PLATE || path.join(S, 'plate.mkv'),
  '-framerate', '30', '-start_number', '0', '-i', path.join(S, 'gfx', process.env.OV || 'ov', '%04d.png')];
let amap = null;
if (!process.env.NOAUDIO) {
  args.push('-i', path.join(S, 'audio.wav'));
  if (music) {
    // soft modern-tech bed: -24 dB, fades, ducked by the SFX
    args.push('-i', music);
    g.push(`[2:a]asplit=2[sfx_a][sfx_b]`,
      `[3:a]atrim=0:14.9,asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:st=0:d=0.6,afade=t=out:st=13.9:d=1.0,volume=-24dB[bgm]`,
      `[bgm][sfx_b]sidechaincompress=threshold=0.03:ratio=6:attack=10:release=300[bgd]`,
      `[sfx_a][bgd]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[aout]`);
    amap = '[aout]';
  } else amap = '2:a';
}
args.push('-filter_complex', g.join(';'), '-map', '[vout]');
if (amap) args.push('-map', amap, '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2'); else args.push('-an');
args.push('-frames:v', String(frames), '-r', '30', '-fps_mode', 'cfr',
  '-c:v', 'libx264', '-preset', process.env.PRESET || 'slow', '-crf', process.env.CRF || '12', '-profile:v', 'high', '-level:v', '4.2',
  '-pix_fmt', 'yuv420p', '-g', '60', '-bf', '2', '-maxrate', '28M', '-bufsize', '56M',
  '-x264-params', 'aq-mode=3:aq-strength=0.9:deblock=-1,-1:psy-rd=1.0,0.15',
  '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
  '-movflags', '+faststart', '-t', dur, out);
console.log('BGM:', music ? music : 'none (no licensed music file found in the project folder)');
const t0 = Date.now(); const r = spawnSync('ffmpeg', args, { encoding: 'utf8' });
console.log((r.stderr || '').split('\r').slice(-2).join('\n')); if (r.status !== 0) { console.error('FAILED'); process.exit(1); }
console.log('final ->', out, ((Date.now() - t0) / 1000).toFixed(1) + 's');
