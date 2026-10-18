"""Mux the rendered picture (work/video.mp4, H.264 copied as is) with each mix -> the two deliverables.
  main  : voice + original lo-fi bed + a few soft SFX      (work/mix_main.wav)
  clean : the same edit, voice only (no music, no SFX)     (work/mix_clean.wav)
usage: final.py OUT_DIR"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL

TITLE = 'สอนสร้างระบบใบเสนอราคา + ใบแจ้งหนี้อัตโนมัติด้วย Google Apps Script'
OUTS = (('google_apps_script_quotation_invoice_tutorial.mp4', 'mix_main.wav', TITLE),
        ('google_apps_script_quotation_invoice_tutorial_clean.mp4', 'mix_clean.wav', TITLE + ' (clean)'))
if __name__ == '__main__':
    out_dir = sys.argv[1]; os.makedirs(out_dir, exist_ok=True)
    for name, mix, title in OUTS:
        out = os.path.join(out_dir, name)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(TL.W, 'video.mp4'), '-i', os.path.join(TL.W, mix),
                        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2',
                        '-metadata', f'title={title}', '-metadata:s:a:0', 'language=tha', '-movflags', '+faststart', out], check=True)
        print(out, f'{os.path.getsize(out) / 1e6:.1f} MB')
