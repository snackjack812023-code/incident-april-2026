"""Final assembly: lossless plate + overlay PNG sequence composited in RGB, one BT.709 conversion, + audio
-> SmartFlow_HR_TikTok_Final.mp4 (H.264 High, 1080x1920, 30 fps CFR, AAC 256k, exactly 600 frames = 20.000 s)."""
import json, os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = json.load(open(os.path.join(ROOT, 'work', 'spec.json'))); N = spec['N']
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'SmartFlow_HR_TikTok_Final.mp4')
g = ('[0:v]setpts=N/(30*TB),format=gbrp[v0];[1:v]setpts=N/(30*TB),format=gbrap[ov];'
     '[v0][ov]overlay=0:0:format=gbrp:eof_action=pass,scale=out_color_matrix=bt709:out_range=tv:flags=bicubic+accurate_rnd+full_chroma_int,format=yuv420p,setsar=1[vout];'
     '[2:a]aformat=sample_rates=48000:channel_layouts=stereo,alimiter=limit=0.891:level=disabled[aout]')
args = ['ffmpeg', '-v', 'error', '-stats', '-y', '-i', os.path.join(ROOT, 'work', 'plate.mkv'),
        '-framerate', '30', '-start_number', '0', '-i', os.path.join(ROOT, 'gfx', 'ov', '%04d.png'), '-i', os.path.join(ROOT, 'work', 'audio.wav'),
        '-filter_complex', g, '-map', '[vout]', '-map', '[aout]', '-frames:v', str(N), '-r', '30', '-fps_mode', 'cfr',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', os.environ.get('CRF', '16'), '-profile:v', 'high', '-level:v', '4.2', '-pix_fmt', 'yuv420p',
        '-g', '60', '-bf', '2', '-maxrate', '18M', '-bufsize', '36M', '-x264-params', 'aq-mode=3:aq-strength=0.9:deblock=-1,-1:psy-rd=1.0,0.15',
        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
        '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', '-t', f'{N / 30:.4f}', out]
t0 = time.time(); r = subprocess.run(args, capture_output=True, text=True)
lines = [l for l in (r.stderr or '').replace('\r', '\n').splitlines() if l.strip()]
if r.returncode: print('\n'.join(lines[-20:])); sys.exit('FAILED')
print(lines[-1] if lines else ''); print('final ->', out, f'{time.time() - t0:.1f}s')
