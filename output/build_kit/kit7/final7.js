// v7 final assembly: lossless RGB plate + overlay PNG sequence composited in RGB, one RGB->YUV (BT.709) conversion,
// + SFX (+ optional licensed BGM found in the project folder) -> H.264/AAC MP4 (1080x1920, 30fps)
const { spawnSync } = require('child_process'); const fs = require('fs'), path = require('path');
const W = path.join(__dirname, '..', 'work'), G = path.join(__dirname, '..', 'gfx7');
const N = JSON.parse(fs.readFileSync(path.join(W, 'spec7.json'), 'utf8')).N;
const frames = parseInt(process.env.FRAMES || String(N), 10);
const out = process.env.OUT || path.join(W, 'final_v7.mp4');
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
  `[0:v]setpts=N/(30*TB),format=gbrp[v0]`,
  `[1:v]setpts=N/(30*TB),format=gbrap[ov]`,
  `[v0][ov]overlay=0:0:format=gbrp:eof_action=pass,scale=out_color_matrix=bt709:out_range=tv:flags=bicubic+accurate_rnd+full_chroma_int,format=yuv420p,setsar=1[vout]`,
];
const args = ['-v', 'error', '-stats', '-y',
  '-i', process.env.PLATE || path.join(W, 'plate7.mkv'),
  '-framerate', '30', '-start_number', '0', '-i', path.join(G, process.env.OV || 'ov', '%04d.png')];
let amap = null;
if (!process.env.NOAUDIO) {
  args.push('-i', path.join(W, 'audio7.wav'));
  if (music) {
    // soft modern-tech bed: -24 dB, fades, ducked by the SFX
    args.push('-i', music);
    g.push(`[2:a]asplit=2[sfx_a][sfx_b]`,
      `[3:a]atrim=0:${(N / 30).toFixed(3)},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:st=0:d=0.6,afade=t=out:st=${(N / 30 - 1.0).toFixed(3)}:d=1.0,volume=-24dB[bgm]`,
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
