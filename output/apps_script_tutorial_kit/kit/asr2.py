"""Thai ASR pass with options. usage: asr2.py model wav out.json [start end] [--vad] [--prompt]
Times in the output are absolute (source timeline)."""
import json, sys, time, subprocess
import numpy as np
from faster_whisper import WhisperModel
model_id, wav, out = sys.argv[1:4]
rest = [a for a in sys.argv[4:] if not a.startswith('--')]
t0s, t1s = (float(rest[0]), float(rest[1])) if len(rest) >= 2 else (0.0, None)
vad = '--vad' in sys.argv; use_prompt = '--prompt' in sys.argv
raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t0s)] + (['-to', str(t1s)] if t1s else []) + ['-i', wav, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
audio = np.frombuffer(raw, np.float32)
t0 = time.time(); m = WhisperModel(model_id, device='cpu', compute_type='int8', cpu_threads=4)
prompt = ('สวัสดีครับ วันนี้ผมจะมาสอนสร้างระบบ Google Apps Script สำหรับสร้างใบเสนอราคาและใบแจ้งหนี้อัตโนมัติ '
          'ใช้ Google Sheets เป็นฐานข้อมูล ไฟล์ Code.gs ไฟล์ HTML appsscript.json Run Setup Deploy Web App') if use_prompt else None
segs, info = m.transcribe(audio, language='th', task='transcribe', beam_size=5, word_timestamps=True, vad_filter=vad,
                          vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=200) if vad else None,
                          condition_on_previous_text=False, initial_prompt=prompt, no_repeat_ngram_size=3)
res = []
for s in segs:
    res.append({'start': s.start + t0s, 'end': s.end + t0s, 'text': s.text, 'avg_logprob': s.avg_logprob,
                'words': [{'start': w.start + t0s, 'end': w.end + t0s, 'word': w.word, 'p': w.probability} for w in (s.words or [])]})
    print(f'[{s.start + t0s:7.2f} -> {s.end + t0s:7.2f}] ({s.avg_logprob:+.2f}) {s.text}', flush=True)
json.dump({'model': model_id, 'segments': res}, open(out, 'w'), ensure_ascii=False, indent=1)
print('done', f'{time.time() - t0:.0f}s')
