"""Final assembly: lossless RGB plate + overlay PNG sequence composited in RGB, one BT.709 conversion,
+ music/SFX mix -> MP4 (H.264 High, 1080x1920, 30 fps CFR, AAC 256k)."""
import os, subprocess, sys, json, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = json.load(open(os.path.join(ROOT, 'work', 'edit.json'))); N = spec['N']
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'final.mp4')
g = ('[0:v]setpts=N/(30*TB),format=gbrp[v0];[1:v]setpts=N/(30*TB),format=gbrap[ov];'
     '[v0][ov]overlay=0:0:format=gbrp:eof_action=pass,scale=out_color_matrix=bt709:out_range=tv:flags=bicubic+accurate_rnd+full_chroma_int,format=yuv420p,setsar=1[vout];'
     '[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1dB,alimiter=limit=0.891:level=disabled[aout]')
# CRF 14 (12 in the other kits): this upscaled phone footage keeps some grain, 14 keeps the file under 30 MB and the
# difference is invisible after TikTok's own re-encode
args = ['ffmpeg', '-v', 'error', '-stats', '-y', '-i', os.path.join(ROOT, 'work', 'plate.mkv'),
        '-framerate', '30', '-start_number', '0', '-i', os.path.join(ROOT, 'gfx', 'ov', '%04d.png'), '-i', os.path.join(ROOT, 'work', 'audio.wav'),
        '-filter_complex', g, '-map', '[vout]', '-map', '[aout]', '-frames:v', str(N), '-r', '30', '-fps_mode', 'cfr',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', os.environ.get('CRF', '14'), '-profile:v', 'high', '-level:v', '4.2', '-pix_fmt', 'yuv420p',
        '-g', '60', '-bf', '2', '-maxrate', '30M', '-bufsize', '60M', '-x264-params', 'aq-mode=3:aq-strength=0.9:deblock=-1,-1:psy-rd=1.0,0.15',
        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
        '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', '-t', f'{N / 30:.4f}', out]
t0 = time.time(); r = subprocess.run(args, capture_output=True, text=True)
print([l for l in (r.stderr or '').replace('\r', '\n').splitlines() if l.strip()][-1:])
if r.returncode: print(r.stderr[-2000:]); sys.exit('FAILED')
print('final ->', out, f'{time.time() - t0:.1f}s')
