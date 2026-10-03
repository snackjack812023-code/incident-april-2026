const { spawnSync } = require('child_process');
const fs = require('fs'), path = require('path');
const { segments, N } = require('./spec.js');
const S = process.env.S, W = path.join(S, 'seg'); fs.mkdirSync(W, { recursive: true });
const SRC = { B: path.join(S, 'B.mp4'), C: path.join(S, 'C.mp4') };
const ENC = ['-c:v', 'ffv1', '-level', '3', '-g', '1', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-an'];
function run(args) { const r = spawnSync('ffmpeg', ['-v', 'error', '-y', ...args], { encoding: 'utf8' }); if (r.status !== 0) { console.error(r.stderr); process.exit(1); } }
const list = [];
for (const s of segments) {
  const out = path.join(W, s.id + '.mkv'); list.push(`file '${out}'`);
  const sp = s.speed || 1;
  let vf, pre;
  if (s.hold) {
    // freeze one frame
    vf = `fps=30,trim=end_frame=1,loop=loop=${s.n - 1}:size=1:start=0,setpts=N/(30*TB)`;
    pre = ['-ss', String(s.t0), '-i', SRC[s.src]];
  } else if (s.reverse) {
    const dur = s.n / 30 + 0.2, t0 = s.t0 - (s.n - 1) / 30 - 0.05;
    vf = `fps=30,reverse`; pre = ['-ss', t0.toFixed(4), '-t', dur.toFixed(4), '-i', SRC[s.src]];
  } else {
    vf = `setpts=PTS/${sp},fps=30`; pre = ['-ss', String(s.t0), '-t', (s.n / 30 * sp + 0.5).toFixed(4), '-i', SRC[s.src]];
  }
  run([...pre, '-vf', vf, '-frames:v', String(s.n), ...ENC, out]);
  const p = spawnSync('ffprobe', ['-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', out], { encoding: 'utf8' });
  const got = parseInt(p.stdout.trim(), 10);
  console.log(s.id.padEnd(5), `f${s.f0}-${s.f1 - 1}`.padEnd(10), `${s.src} t0=${s.t0}`.padEnd(16), got === s.n ? 'OK ' : 'BAD', got, '/', s.n);
}
fs.writeFileSync(path.join(W, 'list.txt'), list.join('\n') + '\n');
run(['-f', 'concat', '-safe', '0', '-i', path.join(W, 'list.txt'), '-c', 'copy', path.join(S, 'reel.mkv')]);
const p = spawnSync('ffprobe', ['-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames,width,height,r_frame_rate,pix_fmt:format=duration', '-of', 'default=nw=1', path.join(S, 'reel.mkv')], { encoding: 'utf8' });
console.log(p.stdout);
