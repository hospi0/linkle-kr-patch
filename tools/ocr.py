# -*- coding: utf-8 -*-
r"""DATA 글꼴 글자 그림 → 글자 판정(2026-10-31) — 파일마다 부분 글꼴이라 코드만으론 글자를 모름
  후보 = JIS X 0208 전부(cp932 0x8140~0x9FFC·0xE040~0xEAA4), 일본어 고딕(BIZ UD·유고딕·메이리오) 14~16px 로 그려
  게임 글자(값 1 = 바탕, 2~15 = 농도)와 후보를 각자 잉크 범위로 잘라 16×16 으로 맞춘 뒤 상관 + 잉크 범위 크기·위치 차이 벌점
  → work/text/glyphs.tsv (글자 그림 sha1 · 판정 글자 · 점수 · 2등 글자·점수) · work/shot/ocr_low.png(점수 낮은 것)
  python tools/ocr.py"""
import hashlib, os, sys, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import datafile as D

FONTS = [os.path.join('C:' + os.sep, 'Windows', 'Fonts', f) for f in ('BIZ-UDGothicR.ttc', 'YuGothM.ttc', 'meiryo.ttc')]
N = 16


def cands():
    """가나·기호(0x81~0x84) + 제1수준 한자(0x889F~0x9872) — 제2수준·부수(囗卜厶力 등 비슷한 모양) 제외"""
    out = []
    for hi in list(range(0x81, 0x85)) + list(range(0x88, 0x99)):
        for lo in range(0x40, 0xFD):
            if lo == 0x7F: continue
            if (hi << 8 | lo) > 0x9872 or 0x839F <= (hi << 8 | lo) < 0x889F: continue   # 그리스·키릴·괘선 제외
            try: ch = bytes([hi, lo]).decode('cp932')
            except UnicodeDecodeError: continue
            if ch.isprintable() and ch != '　': out.append(ch)
    return out


DAKU = {}
for base, dk, hd in zip('かきくけこさしすせそたちつてとはひふへほカキクケコサシスセソタチツテトハヒフヘホうウ',
                        'がぎぐげござじずぜぞだぢづでどばびぶべぼガギグゲゴザジズゼゾダヂヅデドバビブベボゔヴ',
                        '　　　　　　　　　　　　　　　ぱぴぷぺぽ　　　　　　　　　　　　　　　パピプペポ　　'):
    f = [base, dk] + ([hd] if hd != '　' else [])
    for c in f: DAKU[c] = f


_RCACHE = {}


def rend_all(ch):
    if ch not in _RCACHE:
        _RCACHE[ch] = [np.roll(np.roll(render(ch, ImageFont.truetype(fp, s), s), dy, 0), dx, 1)
                       for fp in FONTS for s in (13, 14, 15) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    return _RCACHE[ch]


def daku_pick(g, fam):
    """같은 계열(기본·탁점·반탁점) 중 오른쪽 위(0~6행·7~13열)가 게임 글자와 가장 닮은 것 — 같으면 기본"""
    reg = g[0:7, 7:14].ravel()
    best = None
    for k, ch in enumerate(fam):
        s = max(float((a[0:7, 7:14].ravel() * reg).sum()) / (np.linalg.norm(a[0:7, 7:14]) * np.linalg.norm(reg) + 1e-9) for a in rend_all(ch))
        s += 0.02 if k == 0 else 0                                       # 같으면 기본 가나
        if best is None or s > best[0]: best = (s, ch)
    return best[1]


def family(ch):
    return DAKU.get(ch, [ch])


def is_kana(ch):
    return '぀' <= ch <= 'ヿ' or ch in 'ー、。・「」！？…～　'


def norm(a):
    """2D 농도 → (16×16 정규화 벡터, 잉크 범위 (x0,y0,x1,y1) 14칸 기준)"""
    ys, xs = np.nonzero(a > 0.15)
    if len(xs) == 0: return None, None
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    c = Image.fromarray((a[y0:y1, x0:x1] * 255).astype('uint8')).resize((N, N), Image.BILINEAR)
    v = np.asarray(c, dtype=float).ravel(); v -= v.mean(); n = np.linalg.norm(v)
    return (v / n if n else v), (x0, y0, x1, y1)


def game(b):
    a = np.zeros((14, 14))
    for r in range(14):
        for c in range(14):
            v = (b[r * 7 + c // 2] >> (4 if c % 2 == 0 else 0)) & 15
            a[r, c] = max(0, v - 1) / 14
    return a


def render(ch, font, size):
    im = Image.new('L', (28, 28)); dr = ImageDraw.Draw(im)
    dr.text((14, 14), ch, font=font, fill=255, anchor='mm')
    a = np.asarray(im, dtype=float) / 255
    # 글자 칸(전각 = size)을 14×14 로: 가운데 기준 잘라 줄임
    s = size; o = 14 - s // 2
    box = a[max(0, o):o + s, max(0, o):o + s]
    return np.asarray(Image.fromarray((box * 255).astype('uint8')).resize((14, 14), Image.BILINEAR), dtype=float) / 255


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    gl = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc0', 'DATA*.BIN'))):
        if os.path.basename(f) in ('DATA98.BIN', 'DATA99.BIN'): continue
        d = open(f, 'rb').read(); i = D.parse(d)
        for c in range(i['nglyph']): gl.setdefault(D.glyph(d, i, c), (os.path.basename(f), c))
    keys = list(gl); G = [norm(game(k)) for k in keys]
    cs = cands()
    vecs = []; boxes = []; who = []
    for fp in FONTS:
        for size in (14, 15, 16):
            font = ImageFont.truetype(fp, size)
            for ch in cs:
                v, bx = norm(render(ch, font, size))
                if v is None: continue
                vecs.append(v); boxes.append(bx); who.append(ch)
    V = np.array(vecs); B = np.array(boxes, dtype=float)
    # 직접 비교용: 후보 14×14 농도를 ±1 칸 옮긴 판까지(탁점·작은 가나는 정규화하면 사라짐)
    raw = []; rwho = []
    for fp in FONTS:
        for size in (13, 14, 15):
            font = ImageFont.truetype(fp, size)
            for ch in cs:
                a = render(ch, font, size)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        b = np.roll(np.roll(a, dy, 0), dx, 1).ravel(); b = b - b.mean(); n = np.linalg.norm(b)
                        if n: raw.append(b / n); rwho.append(ch)
    R = np.array(raw); RW = np.array(rwho)
    rows = []
    for k, (g, gb) in zip(keys, G):
        if g is None: rows.append((k, '　', 1.0, '', 0)); continue
        ga = game(k).ravel(); ga = ga - ga.mean(); ga /= (np.linalg.norm(ga) or 1)
        sr = R @ ga                                                      # 직접 상관(후보마다 최대)
        best_raw = {}
        for ch, s in zip(RW, sr):
            if s > best_raw.get(ch, -9): best_raw[ch] = s
        sc = V @ g
        gbv = np.array(gb, dtype=float)
        pen = np.abs(B - gbv).sum(axis=1) / 56.0                         # 잉크 범위 차이(작은 가나·부호 구분)
        tot = 0.4 * (sc - 0.6 * pen) + 0.6 * np.array([best_raw.get(c, 0) for c in who])
        order = np.argsort(-tot)
        best = who[order[0]]; s1 = tot[order[0]]
        # 히라가나 우선: 1등이 한자이고 0.03 안에 히라가나가 있으면(ち↔右 등)
        if not is_kana(best):
            for j in order[1:40]:
                if 'ぁ' <= who[j] <= 'ゖ' and tot[j] >= s1 - 0.03: best = who[j]; s1 = tot[j]; break
        # 탁점·반탁점: 기본 가나 그림을 빼고 오른쪽 위(0~5행·8~13열)에 남는 잉크로 판정
        fam = family(best)
        if len(fam) > 1:
            best = daku_pick(game(k), fam)
        sec = next((who[j] for j in order[1:] if who[j] != best), ''); s2 = next((tot[j] for j in order[1:] if who[j] != best), 0)
        rows.append((k, best, s1, sec, s2))
    with open(os.path.join(ROOT, 'work', 'text', 'glyphs.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('sha1\t글자\t점수\t2등\t2등점수\t처음파일\t번호\n')
        for k, best, s1, sec, s2 in rows:
            o.write('%s\t%s\t%.3f\t%s\t%.3f\t%s\t%d\n' % (hashlib.sha1(k).hexdigest()[:12], best, s1, sec, s2, gl[k][0], gl[k][1]))
    low = sorted(rows, key=lambda r: r[2] - r[4])[:120]
    im = Image.new('L', (12 * 40, 10 * 40), 0); dr = ImageDraw.Draw(im)
    for j, (k, best, s1, sec, s2) in enumerate(low):
        a = game(k); x, y = (j % 12) * 40, (j // 12) * 40
        im.paste(Image.fromarray((a * 255).astype('uint8')).resize((28, 28)), (x, y))
    im.save(os.path.join(ROOT, 'work', 'shot', 'ocr_low.png'))
    print('글자 그림', len(rows), '점수 <0.8:', sum(1 for r in rows if r[2] < 0.8), '1·2등 차 <0.05:', sum(1 for r in rows if r[2] - r[4] < 0.05))


if __name__ == '__main__':
    main()
