"""All on-screen text for the tutorial -> work/ov/items.json (rendered to PNG by gfx/render.js, placed by compose.py).
Layout (1080x1920 canvas, TikTok/Reels safe zones): top UI ~0-200, right-side buttons x>960 (y 860-1650),
caption/music area y>1560. Subtitles sit above the caption area over the desk/keyboard (never over the screen UI that
is being clicked); STEP pills and tips sit near the top under the app UI."""
import html, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl, timeline as TL

FPS = TL.FPS
def mk(s):
    s = html.escape(s)
    return re.sub(r'\[\[(.+?)\]\]', r'<span class="kw">\1</span>', s)

def items():
    out = []
    # subtitles
    for i, (f0, f1, txt) in enumerate(TL.subs()):
        out.append(dict(id=f'sub_{i:03d}', cls='sub', html=mk(txt), f0=f0, f1=f1, x=540, y=1520, anchor='bottom', anim='sub'))
    # hook
    h = TL.BY_ID['H1']
    out.append(dict(id='hook', cls='hook', html=mk(edl.HOOK_TEXT[0]) + '<br>' + mk(edl.HOOK_TEXT[1]),
                    f0=h['f0'] + 3, f1=TL.BY_ID['I1']['f0'] + int(2.3 * FPS), x=540, y=270, anchor='top', anim='pop'))
    # step pills (first 3 s of each step section; STEP 1 has its own card)
    for sec, f0, f1 in TL.sections():
        if sec in edl.STEP_TITLES and sec != 'step1':
            n, title = edl.STEP_TITLES[sec]
            out.append(dict(id=f'pill_{sec}', cls='pill', html=f'<span class="n">{n}</span>{mk(title)}',
                            f0=f0 + 2, f1=min(f1, f0 + int(3.2 * FPS)), x=48, y=212, anchor='topleft', anim='slide'))
    # STEP 1 instruction card on the frozen frame
    k = TL.BY_ID['K1']; n, title = edl.STEP_TITLES['step1']
    out.append(dict(id='card_step1', cls='card', html=f'<div class="t1">{n}</div><div class="t2">{mk(title)}</div>'
                    f'<div class="d">{mk(edl.STEP1_DETAIL[0])}<br>{mk(edl.STEP1_DETAIL[1])}</div>',
                    f0=k['f0'] + 2, f1=k['f1'], x=540, y=940, anchor='center', anim='pop'))
    # helper tips
    for j, (cid, t0, dur, txt) in enumerate(edl.TIPS):
        c = TL.BY_ID[cid]; f0 = c['f0'] + int(t0 * FPS); f1 = min(c['f1'] + 6, f0 + int(dur * FPS))
        out.append(dict(id=f'tip_{j}', cls='tip', html=mk(txt), f0=f0, f1=f1, x=540, y=330, anchor='top', anim='fade'))
    # result texts
    for j, (cid, t0, dur, txt, kind) in enumerate(edl.RESULT_TEXT):
        c = TL.BY_ID[cid]; f0 = c['f0'] + int(t0 * FPS)
        if kind == 'big':
            out.append(dict(id=f'res_{j}', cls='big', html=mk(txt), f0=f0, f1=f0 + int(dur * FPS), x=540, y=250, anchor='top', anim='pop'))
        else:
            out.append(dict(id=f'res_{j}', cls='spill', html=mk(txt), f0=f0, f1=f0 + int(dur * FPS), x=540, y=262, anchor='top', anim='fade'))
    # CTA
    c = TL.BY_ID['CTA']
    out.append(dict(id='cta1', cls='cta1', html=mk(edl.CTA_TEXT[0]), f0=c['f0'] + 2, f1=c['f1'], x=540, y=860, anchor='top', anim='pop'))
    out.append(dict(id='cta2', cls='cta2', html=mk(edl.CTA_TEXT[1]) + '<br>' + mk(edl.CTA_TEXT[2]), f0=c['f0'] + 20, f1=c['f1'],
                    x=540, y=1100, anchor='top', anim='pop'))
    return out

if __name__ == '__main__':
    os.makedirs(os.path.join(TL.W, 'ov'), exist_ok=True)
    it = items(); json.dump(it, open(os.path.join(TL.W, 'ov', 'items.json'), 'w'), ensure_ascii=False, indent=1)
    print(len(it), 'items;', sum(1 for i in it if i['cls'] == 'sub'), 'subtitles')
    for i in it:
        if i['cls'] != 'sub': print(f"  {i['id']:12s} {i['f0'] / FPS:6.2f}-{i['f1'] / FPS:6.2f}  {re.sub('<[^>]+>', '', i['html'])[:60]}")
