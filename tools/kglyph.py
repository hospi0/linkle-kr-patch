# -*- coding: utf-8 -*-
r"""한글 글자 그림 14×14 4bpp(98 B, 바탕 1 · 잉크 2~15 농도) — 대사 글꼴(DATA 글꼴 구역) 용(2026-10-31)
  STYLE: 이름 → (글꼴 파일, 크기 px, 굵게 덧칠 여부, 모노 여부)
  python tools/kglyph.py → work/shot/poc_preview.png (원본 창 | 후보마다, 실제 창 팔레트 CRAM 0x50)"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FD = os.path.join('C:' + os.sep, 'claude', 'utils', 'font')
WF = os.path.join('C:' + os.sep, 'Windows', 'Fonts')
STYLES = {
    'A_나눔고딕Bold13': (os.path.join(FD, 'nanum-gothic', 'NanumGothicBold.ttf'), 13, False),
    'B_나눔고딕ExtraBold13': (os.path.join(FD, 'nanum-gothic', 'NanumGothicExtraBold.ttf'), 13, False),
    'C_맑은고딕Bold12': (os.path.join(WF, 'malgunbd.ttf'), 12, False),
    'D_갈무리11': (os.path.join(FD, 'Galmuri-v2.40.3', 'Galmuri11.ttf'), 12, True),
}
DEFAULT = 'A_나눔고딕Bold13'
LEFT = '.,!?'
SS = 4


def cover(ch, style):
    fp, size, mono = STYLES[style]
    if mono:
        f = ImageFont.truetype(fp, size); im = Image.new('L', (14, 14)); dr = ImageDraw.Draw(im)
        dr.fontmode = '1'
        if ch in LEFT: dr.text((1, 7), ch, font=f, fill=255, anchor='lm')
        else: dr.text((7, 7), ch, font=f, fill=255, anchor='mm')
        return np.asarray(im, dtype=float) / 255
    f = ImageFont.truetype(fp, size * SS); im = Image.new('L', (14 * SS, 14 * SS)); dr = ImageDraw.Draw(im)
    if ch in LEFT: dr.text((1 * SS, 7 * SS), ch, font=f, fill=255, anchor='lm')       # 반각 부호는 칸 왼쪽에
    else: dr.text((7 * SS, 7 * SS), ch, font=f, fill=255, anchor='mm')
    return np.asarray(im.resize((14, 14), Image.BOX), dtype=float) / 255


def glyph(ch, style=DEFAULT):
    a = cover(ch, style)
    v = np.where(a < 0.06, 1, np.clip(np.rint(1 + a * 14), 2, 15)).astype(int)
    out = bytearray(98)
    for r in range(14):
        for c in range(0, 14, 2): out[r * 7 + c // 2] = (v[r, c] << 4) | v[r, c + 1]
    return bytes(out)


def preview():
    import struct
    sys.path.insert(0, HERE); import vdp1cmd, datafile as D
    v = vdp1cmd.load(os.path.join(ROOT, 'work', 'mem', 's15'))
    T = np.array([[((v[0x530c0 + (y * 320 + x) // 2] >> (4 if x % 2 == 0 else 0)) & 15) for x in range(320)] for y in range(80)])
    c = open(os.path.join(ROOT, 'work', 'mem', 's15', 'CRAM.bin'), 'rb').read()
    pal = []
    for k in range(16):
        w = struct.unpack_from('<H', c, 2 * (0x50 + k))[0]; pal.append(((w & 31) * 8, ((w >> 5) & 31) * 8, ((w >> 10) & 31) * 8))
    d = open(os.path.join(ROOT, 'work', 'disc0', 'DATA19.BIN'), 'rb').read(); i = D.parse(d)
    lines = ['HOSPI：………뭐야.', '　방금 그건,꿈이었구나.']   # 첫 줄 앞 5자(HOSPI)는 원본 화면 그대로
    name = T[14:28, 72:142].copy()                                       # 이름 HOSPI： 그대로(이름 글꼴은 따로)
    def og(code): return np.array([[(D.glyph(d, i, code)[r * 7 + k // 2] >> (4 if k % 2 == 0 else 0)) & 15 for k in range(14)] for r in range(14)])
    OLD = {'…': og(0xCE), '：': og(0xC9)}                                                 # 말줄임표는 원래 글꼴 칸
    colon = np.array([[(D.glyph(d, i, 0xC9)[r * 7 + k // 2] >> (4 if k % 2 == 0 else 0)) & 15 for k in range(14)] for r in range(14)])
    def img(A):
        return Image.fromarray(np.array([[pal[x] for x in row] for row in A], dtype=np.uint8), 'RGB').resize((960, 240), Image.NEAREST)
    outs = [('원본', img(T))]
    for st in STYLES:
        A = T.copy(); A[12:68, 72:300] = 1; A[14:28, 72:142] = name
        for li, s in enumerate(lines):
            x = 72; y = 14 + 18 * li
            for ch in (s[5:] if li == 0 else s):
                if li == 0 and x == 72: x = 142
                if ch in OLD: G = OLD[ch]
                else: g = glyph(ch, st); G = np.array([[(g[r * 7 + k // 2] >> (4 if k % 2 == 0 else 0)) & 15 for k in range(14)] for r in range(14)])
                A[y:y + 14, x:x + 14] = np.where(G > 1, G, A[y:y + 14, x:x + 14]); x += 14
        outs.append((st, img(A)))
    W = Image.new('RGB', (960, 270 * len(outs)), (40, 40, 40)); dr = ImageDraw.Draw(W)
    lab = ImageFont.truetype(os.path.join(WF, 'malgun.ttf'), 20)
    for k, (n, im) in enumerate(outs):
        W.paste(im, (0, 270 * k + 28)); dr.text((6, 270 * k + 2), n, font=lab, fill=(255, 255, 0))
    p = os.path.join(ROOT, 'work', 'shot', 'poc_preview.png'); W.save(p); print(p)


if __name__ == '__main__':
    preview()
