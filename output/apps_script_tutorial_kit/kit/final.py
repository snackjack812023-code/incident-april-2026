"""Deliverables from the rendered master (work/video.mp4, x264 CRF 16): one 2-pass x264 encode of the picture at
~4.6 Mb/s (visually the same as the master: the extra bits there go to the phone camera's sensor grain; keeps each
file under 100 MB for phone upload), then muxed with each mix (AAC 256k, faststart):
  main  : voice + original lo-fi bed + a few soft SFX      (work/mix_main.wav)
  clean : the same edit, voice only (no music, no SFX)     (work/mix_clean.wav)
usage: final.py OUT_DIR"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL

TITLE = 'สอนสร้างระบบใบเสนอราคา + ใบแจ้งหนี้อัตโนมัติด้วย Google Apps Script'
OUTS = (('google_apps_script_quotation_invoice_tutorial.mp4', 'mix_main.wav', TITLE),
        ('google_apps_script_quotation_invoice_tutorial_clean.mp4', 'mix_clean.wav', TITLE + ' (clean)'))
X264 = ['-c:v', 'libx264', '-preset', 'slow', '-tune', 'film', '-b:v', '4600k', '-maxrate', '8000k', '-bufsize', '10000k',
        '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level:v', '4.1', '-g', '60', '-bf', '2',
        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']
if __name__ == '__main__':
    out_dir = sys.argv[1]; os.makedirs(out_dir, exist_ok=True)
    src, pic, log = (os.path.join(TL.W, n) for n in ('video.mp4', 'video_final.mp4', 'x264_2pass'))
    for p, out in ((1, os.devnull), (2, pic)):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-an'] + X264 + ['-pass', str(p), '-passlogfile', log]
                       + (['-f', 'mp4'] if p == 1 else []) + [out], check=True)
    for name, mix, title in OUTS:
        out = os.path.join(out_dir, name)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', pic, '-i', os.path.join(TL.W, mix),
                        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2',
                        '-metadata', f'title={title}', '-metadata:s:a:0', 'language=tha', '-movflags', '+faststart', out], check=True)
        print(out, f'{os.path.getsize(out) / 1e6:.1f} MB')
