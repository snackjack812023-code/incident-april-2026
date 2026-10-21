"""Mux the picture (work/video.mp4, x264 CRF 14, copied as is) with the mix (work/mix.wav, AAC 320k) -> the deliverable.
usage: final.py OUT.mp4"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec as SP
if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(SP.W, 'video.mp4'), '-i', os.path.join(SP.W, 'mix.wav'),
                    '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-ac', '2',
                    '-metadata', 'title=SmartFlow — แจ้งเตือนสถานะงานเข้า LINE อัตโนมัติ', '-movflags', '+faststart', out], check=True)
    print(out, f'{os.path.getsize(out) / 1e6:.1f} MB')
