// Post-render verification with ffprobe (resolution, 9:16, 30 fps, H.264, duration <= 15 s). Exit code 1 on failure.
const { spawnSync } = require('child_process'); const fs = require('fs');
const file = process.argv[2]; if (!file) { console.error('usage: node verify.js file.mp4'); process.exit(2); }
const r = spawnSync('ffprobe', ['-v', 'error', '-count_frames', '-print_format', 'json', '-show_streams', '-show_format', file], { encoding: 'utf8' });
const j = JSON.parse(r.stdout); const v = j.streams.find(s => s.codec_type === 'video'), a = j.streams.find(s => s.codec_type === 'audio');
const fr = (s) => { const [n, d] = s.split('/').map(Number); return n / d; };
const dur = parseFloat(j.format.duration);
const checks = [
  ['resolution 1080x1920', v.width === 1080 && v.height === 1920, `${v.width}x${v.height}`],
  ['aspect 9:16 (SAR 1:1)', v.width * 16 === v.height * 9 && (!v.sample_aspect_ratio || v.sample_aspect_ratio === '1:1'), `${v.display_aspect_ratio || 'n/a'} sar ${v.sample_aspect_ratio || 'n/a'}`],
  ['30 fps (r_frame_rate & avg)', Math.abs(fr(v.r_frame_rate) - 30) < 1e-6 && Math.abs(fr(v.avg_frame_rate) - 30) < 1e-3, `${v.r_frame_rate} / ${v.avg_frame_rate}`],
  ['codec H.264', v.codec_name === 'h264', `${v.codec_name} ${v.profile} L${v.level} ${v.pix_fmt}`],
  ['duration <= 15 s', dur <= 15.0, `${dur.toFixed(3)} s (${v.nb_read_frames} frames)`],
  ['audio AAC', !!a && a.codec_name === 'aac', a ? `${a.codec_name} ${a.sample_rate} Hz ${a.channels}ch` : 'missing'],
  ['container MP4', /mp4/.test(j.format.format_name), j.format.format_name],
];
let ok = true; for (const [n, p, d] of checks) { ok = ok && p; console.log((p ? 'PASS' : 'FAIL').padEnd(5), n.padEnd(30), d); }
console.log('size:', (fs.statSync(file).size / 1048576).toFixed(2), 'MB   video bitrate:', (parseInt(v.bit_rate) / 1e6).toFixed(2), 'Mbps');
process.exit(ok ? 0 : 1);
