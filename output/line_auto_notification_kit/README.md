# SmartFlow: LINE auto-notification demo (TikTok/Reels): build kit

This kit rebuilds `output/SmartFlow_LINE_Auto_Notification_TikTok.mp4`. The output is 9:16, 1080x1920, 30 fps, H.264 High (CRF 14) with AAC 320k, and runs 17.0 s. It is made from the original phone clip (1080x1920 HEVC, 59.94 fps, no audio).

```bash
SRC=/path/to/clip.mp4 ./build.sh
```

The recording stays in its original order and in real time: output second = source second. Nothing on the LINE screen is changed or made up.

| Time | Shot | Treatment |
|---|---|---|
| 0–2 s | phone with the LINE group | Fast zoom-in 1.0→1.1 with a soft whoosh. "อัปเดตงานแล้ว..." shows on the first frame, then "ต้อง**พิมพ์**แจ้งใน LINE / **เอง**ทุกครั้ง?" (two lines at most per screen). |
| 2–7.6 s | same | UI click, then "ถ้าให้ระบบแจ้งให้อัตโนมัติล่ะ?" and "เปลี่ยนสถานะงาน → แจ้ง LINE". A slow zoom drifts towards the bottom of the chat; the last 0.8 s has no text, so the viewer waits. |
| 7.61–10 s | the new status card arrives (source frame 456) | The notification sound plays in a deliberate gap in the music. A fast but smooth zoom to 1.6x locks onto the card. A green glow and a "ping" ring appear around the card, never on it. Text: "แจ้งเตือนเข้า LINE อัตโนมัติ! 🔔" / "ไม่ต้องคอยพิมพ์แจ้งเอง". |
| 10–11.5 s | the camera moves to her | Transition whoosh; the zoom backs out. |
| 11–14 s | she shows the phone | Slow push-in. Text: "ทีมรู้สถานะงานทันที" / "Real-Time • Automatic • ลดงานซ้ำ". |
| 14–17 s | same | Soft pop. "อยากทำระบบแบบนี้ไหม?" / "Google Apps Script + LINE", then "ติดตามไว้ เดี๋ยวคลิปหน้าสอนทำ 👇" / "SmartFlow \| @smartflow". |

| Step | File | What it does |
|---|---|---|
| 1 | `kit/track.py` | SIFT plus RANSAC homography tracking of the phone screen. It follows the chat area for frames 0–455 and the LINE card (outlined by hand on frame 470) for frames 456–620. |
| 2 | `kit/spec.py`, `gfx/` | Timeline, text, camera keys and sound cues. Each text line is rendered in Chromium with the Prompt font (SIL OFL) and auto-fitted to a single line. |
| 3 | `kit/render.py` | Takes the source frame nearest in time and applies a uniform zoom centred on the tracked content (no stretching). Fast zooms get a 3-sample shutter blur. A light unsharp mask goes on, the glow is drawn outside the card, and text sits on frosted-glass panels inside the TikTok safe area. |
| 4 | `kit/music.py` | Original 120 BPM modern-tech track: Am–F–C–G, beat from the first frame. A snare roll and riser lead into a gap at the card, then the groove returns on 8.0 s. It resolves on C and fades out. |
| 5 | `kit/mix.py` | Original whoosh, UI click, notification chime (a generic two-note glass chime, not LINE's sound), transition whoosh and pop. The music dips 4 dB (≈37%) around the notification. Output is −14 LUFS, true peak −1 dBTP. |
| 6 | `kit/final.py`, `kit/verify.py` | Muxes with faststart, then checks format, decoding, black frames, loudness and A/V alignment. |
