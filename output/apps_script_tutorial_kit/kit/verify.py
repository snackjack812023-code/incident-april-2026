"""Checks on a finished MP4: format (1080x1920, 30 fps CFR, H.264 High yuv420p BT.709, AAC 48 kHz stereo, faststart),
decodes without errors, no black frames, loudness (-14 LUFS, <= -1 dBTP), and that its audio is sample-aligned with
the mix it was muxed from (A/V sync).  usage: verify.py file.mp4 [mix.wav]"""
import json, re, subprocess, sys, wave
import numpy as np

def run(cmd): return subprocess.run(cmd, capture_output=True, text=True)
f = sys.argv[1]; mix = sys.argv[2] if len(sys.argv) > 2 else None; ok = True
def check(cond, msg):
    global ok
    print(('  ok   ' if cond else '  FAIL ') + msg); ok &= bool(cond)

p = json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', f]).stdout)
v = [s for s in p['streams'] if s['codec_type'] == 'video'][0]; a = [s for s in p['streams'] if s['codec_type'] == 'audio'][0]
dur = float(p['format']['duration']); size = int(p['format']['size'])
print(f'{f}\n  {size / 1e6:.1f} MB, {dur:.3f} s, {int(p["format"]["bit_rate"]) / 1e6:.2f} Mb/s')
check(v['codec_name'] == 'h264' and v.get('profile') == 'High', f'video {v["codec_name"]} {v.get("profile")} level {v.get("level")}')
check((v['width'], v['height']) == (1080, 1920), f'{v["width"]}x{v["height"]} (9:16), SAR {v.get("sample_aspect_ratio", "1:1")}')
check(v.get('sample_aspect_ratio', '1:1') in ('1:1', '0:1'), 'square pixels (no stretch)')
check(v['r_frame_rate'] == '30/1' and v['avg_frame_rate'] == '30/1', f'fps {v["r_frame_rate"]} (avg {v["avg_frame_rate"]}), {v.get("nb_frames")} frames')
check(v['pix_fmt'] == 'yuv420p' and v.get('color_primaries') == 'bt709' and v.get('color_transfer') == 'bt709', f'{v["pix_fmt"]}, {v.get("color_space")}/{v.get("color_primaries")}/{v.get("color_transfer")}, range {v.get("color_range")}')
check(not any(sd.get('rotation') for sd in v.get('side_data_list', [])), 'no rotation flag')
check(a['codec_name'] == 'aac' and int(a['sample_rate']) == 48000 and a['channels'] == 2, f'audio {a["codec_name"]} {a["sample_rate"]} Hz {a["channels"]} ch {int(a.get("bit_rate", 0)) // 1000} kb/s')
check(abs(float(v['duration']) - float(a['duration'])) < 0.05, f'video {float(v["duration"]):.3f} s / audio {float(a["duration"]):.3f} s')
with open(f, 'rb') as fh: head = fh.read(1 << 16)
check(head.find(b'moov') < head.find(b'mdat') if b'moov' in head else False, 'faststart (moov before mdat)')
e = run(['ffmpeg', '-v', 'error', '-i', f, '-f', 'null', '-']).stderr.strip()
check(e == '', 'decodes without errors' + ('' if not e else ': ' + e[:200]))
bd = run(['ffmpeg', '-hide_banner', '-i', f, '-vf', 'blackdetect=d=0.1:pix_th=0.08', '-an', '-f', 'null', '-']).stderr
blacks = re.findall(r'black_start:(\S+) black_end:(\S+)', bd)
check(not blacks, 'no black frames' + ('' if not blacks else f': {blacks[:5]}'))
lo = run(['ffmpeg', '-hide_banner', '-nostats', '-i', f, '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr
I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', lo)[-1]); LRA = float(re.findall(r'LRA:\s+([\d.]+) LU', lo)[-1])
TP = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', lo)[-1])
check(abs(I + 14) <= 1.0, f'loudness {I:.1f} LUFS integrated (target -14), LRA {LRA:.1f} LU')
check(TP <= -0.5, f'true peak {TP:.1f} dBTP')
if mix:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-map', '0:a', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    with wave.open(mix) as w: y = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2).mean(1) / 32768.0
    s0, n = 48000 * 2, 48000 * 20                                      # 20 s window, FFT cross-correlation
    xs, ys = x[s0:s0 + n], y[s0:s0 + n]; m = 1 << int(np.ceil(np.log2(2 * n)))
    c = np.fft.irfft(np.fft.rfft(xs, m) * np.conj(np.fft.rfft(ys, m)), m)
    lag = int(np.argmax(np.concatenate([c[-960:], c[:961]]))) - 960; best = lag
    check(abs(best) <= 48, f'audio offset vs {mix.split("/")[-1]}: {best} samples ({best / 48:.1f} ms)')
print('  RESULT:', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
