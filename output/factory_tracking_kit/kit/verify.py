"""ffprobe checks: 1080x1920, 9:16 (SAR 1:1), 30 fps CFR, H.264, AAC, MP4, 18-22 s. Exit 1 on failure."""
import json, os, subprocess, sys
f = sys.argv[1]
j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-print_format', 'json', '-show_streams', '-show_format', f], capture_output=True, text=True).stdout)
v = next(s for s in j['streams'] if s['codec_type'] == 'video'); a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
fr = lambda s: eval(s.replace('/', '/')) if s and s != '0/0' else 0
dur = float(j['format']['duration'])
checks = [('resolution 1080x1920', v['width'] == 1080 and v['height'] == 1920, f"{v['width']}x{v['height']}"),
          ('aspect 9:16, SAR 1:1', v.get('sample_aspect_ratio', '1:1') == '1:1', f"DAR {v.get('display_aspect_ratio')} SAR {v.get('sample_aspect_ratio')}"),
          ('30 fps (r & avg)', abs(fr(v['r_frame_rate']) - 30) < 1e-6 and abs(fr(v['avg_frame_rate']) - 30) < 1e-3, f"{v['r_frame_rate']} / {v['avg_frame_rate']}"),
          ('H.264', v['codec_name'] == 'h264', f"{v['codec_name']} {v.get('profile')} L{v.get('level')} {v.get('pix_fmt')}"),
          ('duration 18-22 s', 18 <= dur <= 22, f"{dur:.3f} s ({v.get('nb_read_frames')} frames)"),
          ('audio AAC', bool(a) and a['codec_name'] == 'aac', f"{a['codec_name']} {a['sample_rate']} Hz {a['channels']}ch" if a else 'missing'),
          ('container MP4', 'mp4' in j['format']['format_name'], j['format']['format_name'])]
ok = True
for n, p, d in checks: ok &= p; print(('PASS' if p else 'FAIL').ljust(5), n.ljust(24), d)
print(f"size {os.path.getsize(f) / 1048576:.2f} MB, video {int(v['bit_rate']) / 1e6:.2f} Mbps, audio {int(a['bit_rate']) / 1e3:.0f} kbps")
sys.exit(0 if ok else 1)
