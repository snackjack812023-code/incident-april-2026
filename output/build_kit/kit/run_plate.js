const { spawnSync } = require('child_process'); const fs = require('fs'), path = require('path');
const S = process.env.S; const { N } = require('./spec.js'); const { graph } = require('./plate.js');
const a = parseInt(process.env.A || '0', 10), b = parseInt(process.env.B || String(N), 10);
const gfx = path.join(S, 'gfx'); const outFile = process.env.OUT || path.join(S, 'plate.mkv');
const g = graph({ startFrame: a }); fs.writeFileSync(path.join(S, 'plate_graph.txt'), g.text);
const args = ['-v', 'error', '-stats', '-y',
  '-ss', (a / 30).toFixed(5), '-i', path.join(S, 'reel.mkv'),
  '-loop', '1', '-framerate', '30', '-i', path.join(gfx, 'chrome_mask.png'),
  '-loop', '1', '-framerate', '30', '-i', path.join(gfx, 'chrome_shadow.png'),
  '-loop', '1', '-framerate', '30', '-i', path.join(gfx, 'chrome_border.png'),
  '-loop', '1', '-framerate', '30', '-i', path.join(gfx, 'chrome_urlmask.png'),
  '-filter_complex_script', path.join(S, 'plate_graph.txt'), '-map', '[plate]', '-frames:v', String(b - a), '-r', '30',
  '-c:v', 'libx264', '-preset', process.env.PRESET || 'veryfast', '-crf', process.env.CRF || '8', '-pix_fmt', 'yuv420p',
  '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', outFile];
const t0 = Date.now(); const r = spawnSync('ffmpeg', args, { encoding: 'utf8' });
console.log(r.stderr.split('\r').slice(-2).join('\n')); if (r.status !== 0) { console.error('FAILED'); process.exit(1); }
console.log('plate', a, '->', b, 'in', ((Date.now() - t0) / 1000).toFixed(1), 's ->', outFile);
