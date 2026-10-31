# -*- coding: utf-8 -*-
r"""이름 입력 한글화(2026-10-31)
  칸→코드 표: AUTOEXEC(램 0x0600E000) 0x32D4C 부터 판 5개 × u16 50칸(10열×5줄, 줄 먼저) — 판 차례 히라·탁음1·가타·탁음2·영숫자
    C5 = 빈칸(공백 글자) · C8 C8 = OK(마지막 줄 8·9칸) · FFFF = 칸 없음
  이름 = u16 공통 글꼴 코드(0x060B0634) — 대사 {名}(FFFE) 은 DATA 공통 글꼴(코드 0x000~0x106, 모든 DATA 같음)로, 입력 중 미리보기는 50ON.XGD(16×16 칸 20열, 칸 = 코드)로 찍음
  한글: 가나 4판 → 음절판(판마다 1~4줄 40자, 5줄은 OK 만) · 음절 160개 = 코드 0x00~0x9F(가나다순) · 영숫자 판·코드 0xA1~ 그대로
    그림: 4_HIRA·4_DAKU1·4_KATA·4_DAKU2(판 차례) 칸 글자 지우고 음절 · 50ON 칸 0x00~0xA0 · DATA 공통 글꼴은 build.py 가 SYL 로 덮음
  python tools/nameentry.py → work/build/AUTOEXEC.BIN·TITLE.BIN·GAME2.BIN(같은 입력표) · work/build/IKECG/4_*.XGD·50ON.XGD · work/shot/name_preview.png"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx_menu as G

SYL = ('가간강건경고구규그근기길김나남노누니다단달대도동두드라란래레려로루류르리린마만메명모무문미민바박반배백베별보부브'
       '비빈사산상새서선설성세소손송수순스승시신실아안애야양어엘연영예오온와완요용우운원위유윤은을의이인일임자장재전정제'
       '조종주준지진차찬창채철초최추치카케코크키타태테토트티파페포표프피하학한해향허현혜호홍화환훈휘희히')
TBL = 0x32D4A                  # AUTOEXEC 파일 위치(램 0x06040D4A) — ★2026-10-31 실기: 0x32D4C 로 잡아 한 칸씩 밀렸음(원본 첫 칸 あ=0 이 0x32D4A, OK C8 C8 = 칸 48·49)
PAGES = ['4_HIRA', '4_DAKU1', '4_KATA', '4_DAKU2']      # 표 판 차례(0~3)
COLX = [17, 41, 65, 89, 113, 161, 185, 209, 233, 257]   # 칸 글자 왼쪽(원본 잉크 열)
ROWY = [10, 34, 58, 82, 106]
CELL = 16


def check():
    assert len(SYL) == len(set(SYL)), [c for c in SYL if SYL.count(c) > 1]
    assert list(SYL) == sorted(SYL), '가나다순 아님'
    assert len(SYL) <= 160, len(SYL)
    assert all(c in SYL for c in '하스피로빈'), '하스피·로빈'


def glyph16(ch, size=13):
    """16×16 칸 덮임(가운데)"""
    g = G.render(ch, size); h, w = g.shape
    out = np.zeros((16, 16)); y = (16 - h) // 2; x = (16 - w) // 2
    out[y:y + h, x:x + w] = g[:16 - y, :16 - x]
    return out


def table(auto):
    a = bytearray(auto)
    exp = [struct.unpack_from('>H', a, TBL + 100 * p + 2 * c)[0] for p in range(4) for c in (47, 48, 49)]
    assert all(exp[3 * p] != 0xC8 and exp[3 * p + 1] == exp[3 * p + 2] == 0xC8 for p in range(4)), ('OK 칸 자리 다름(칸 47 은 OK 아님, 48·49 = C8)', [hex(x) for x in exp])
    assert struct.unpack_from('>H', a, TBL)[0] == 0, '첫 칸(あ) 코드 0 아님 — 표 시작 어긋남'
    for p in range(4):
        for cell in range(50):
            r, c = divmod(cell, 10); o = TBL + 100 * p + 2 * cell
            if r == 4: v = 0xC8 if c >= 8 else 0xFFFF
            else:
                k = p * 40 + r * 10 + c
                v = k if k < len(SYL) else 0xFFFF
            struct.pack_into('>H', a, o, v)
    return bytes(a)


def grid(n, p):
    head, a = G.load(n); new = a.copy()
    for r in range(5):
        for c in range(10):
            if r == 4 and c >= 8: continue                                  # OK 그대로
            x0, y0 = COLX[c] - 2, ROWY[r] - 2
            cell = new[y0:y0 + 18, x0:x0 + 18]; cell[cell >= 4] = 3        # 글자 지움
            k = p * 40 + r * 10 + c
            if r < 4 and k < len(SYL):
                g = glyph16(SYL[k]); v = np.rint(3 + 12 * g).astype(int)
                reg = new[y0 + 1:y0 + 17, x0 + 1:x0 + 17]
                new[y0 + 1:y0 + 17, x0 + 1:x0 + 17] = np.where(g > 0.06, np.maximum(reg, v), reg)
    return head, a, new


def fifty():
    head, a = G.load('50ON'); new = a.copy()
    for k in range(0xA1):
        y, x = divmod(k, 20); y *= 16; x *= 16
        new[y:y + 16, x:x + 16] = 0
        if k < len(SYL):
            g = glyph16(SYL[k]); v = np.maximum(4, np.rint(3 + 12 * g)).astype(int)
            new[y:y + 16, x:x + 16] = np.where(g > 0.08, v, 0)
    return head, a, new


def main():
    sys.stdout.reconfigure(encoding='utf-8'); check()
    auto = open(os.path.join(ROOT, 'work', 'disc0', 'AUTOEXEC.BIN'), 'rb').read()
    out = os.path.join(ROOT, 'work', 'build'); os.makedirs(os.path.join(out, 'IKECG'), exist_ok=True)
    newauto = table(auto); open(os.path.join(out, 'AUTOEXEC.BIN'), 'wb').write(newauto)
    # ★같은 입력표가 TITLE.BIN·GAME2.BIN(0x32C64)에도 있음 — 새 게임 이름 입력은 이쪽(2026-10-31 AUTOEXEC 만 고쳐 실기에서 한글 입력 안 됐음)
    for fn in ('TITLE.BIN', 'GAME2.BIN'):
        d = bytearray(open(os.path.join(ROOT, 'work', 'disc0', fn), 'rb').read())
        o = bytes(d).find(auto[TBL:TBL + 500]); assert o > 0 and bytes(d).count(auto[TBL:TBL + 500]) == 1, fn
        d[o:o + 500] = newauto[TBL:TBL + 500]; open(os.path.join(out, fn), 'wb').write(bytes(d))
        print('%s 입력표 0x%X 도 고침' % (fn, o))
    shots = []
    for p, n in enumerate(PAGES):
        head, a, new = grid(n, p); open(os.path.join(out, 'IKECG', n + '.XGD'), 'wb').write(G.save(head, new)); shots.append((n, a, new))
    head, a, new = fifty(); open(os.path.join(out, 'IKECG', '50ON.XGD'), 'wb').write(G.save(head, new)); shots.append(('50ON', a, new))
    c = open(os.path.join(ROOT, 'work', 'mem', 's4', 'CRAM.bin'), 'rb').read()
    pal = [((w & 31) * 8, ((w >> 5) & 31) * 8, ((w >> 10) & 31) * 8) for w in (struct.unpack_from('<H', c, 2 * k)[0] for k in range(16))]
    pal[0] = (60, 90, 60)
    H = sum(s[1].shape[0] * 2 + 18 for s in shots); W = max(s[1].shape[1] for s in shots) * 4 + 20
    S = Image.new('RGB', (W, H), (30, 30, 30)); d = ImageDraw.Draw(S); y = 0
    lab = ImageFont.truetype(G.FALLBACK, 13)
    for n, a, new in shots:
        im = lambda z: Image.fromarray(np.array([[pal[v] for v in r] for r in z], dtype=np.uint8)).resize((z.shape[1] * 2, z.shape[0] * 2), Image.NEAREST)
        d.text((2, y), n, font=lab, fill=(255, 255, 0)); S.paste(im(a), (0, y + 16)); S.paste(im(new), (a.shape[1] * 2 + 20, y + 16)); y += a.shape[0] * 2 + 18
    S.save(os.path.join(ROOT, 'work', 'shot', 'name_preview.png'))
    print('음절 %d · 표·그림 → work/build · 미리보기 work/shot/name_preview.png' % len(SYL))


if __name__ == '__main__':
    main()
