# -*- coding: utf-8 -*-
r"""메뉴 그림(IKECG/*.XGD) 한글화(2026-10-31) — XGD = u16 LE 폭·높이 + 4bpp(팔레트 0: 0 투명·2 그림자·3 상자 바탕·4~15 회색→흰색 글자 농도)
  글자 = 상자 안 값 4~15 → 바탕 3 으로 지우고 한글(나눔고딕 Bold, 4배 그려 줄임, 덮임 → 3+12×덮임)을 같은 줄 높이 가운데에
  정렬: 왼쪽 여백이 오른쪽 여백 절반 이하거나 LEFT 목록이면 원래 글자 시작 x 에서, 아니면 원래 글자 덩어리 가운데에
  여러 줄(TYPE_*)은 줄마다. 글자 폭이 자리를 넘으면 0.5px 씩 줄여 맞춤(최소 10px) — 넘치면 중단
  python tools/gfx_menu.py → work/build/IKECG/*.XGD · work/shot/menu_preview_*.png(원본|한글, 실제 팔레트 s4 CRAM 0x00)"""
import os, re, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'disc0', 'IKECG')
FONT = os.path.join('C:' + os.sep, 'claude', 'utils', 'font', 'nanum-gothic', 'NanumGothicBold.ttf')
FALLBACK = os.path.join('C:' + os.sep, 'Windows', 'Fonts', 'malgunbd.ttf')     # ©·Ⓑ 처럼 나눔에 없는 글자
SIZE, SS = 13, 4
LEFT = {'17'} | {'MES_%02d' % i for i in range(1, 18)}
PUNCT = ',.!?…~:;'
KO = {
    '1': ['주인공의 이름을 입력해 주세요'],
    '10': ['옵션'],
    '11_C': ['컨트롤러'],
    '11_M': ['메시지 속도'],
    '11_SB': ['사운드 밸런스'],
    '11_SM': ['사운드 모드'],
    '14_FUTU': ['보통'], '14_HAYA': ['빠름'], '14_OSOI': ['느림'],
    '15_MONO': ['모노'], '15_ST': ['스테레오'],
    '17': ['의 색을 골라 주세요'],
    '18_BEGI': ['처음부터'], '18_OPS': ['옵션'], '18_SERI': ['이어서'],
    '6': ['저장 방법을 골라 주세요'],
    '7_CRAM': ['카트리지 RAM'], '7_RAM': ['본체 RAM'],
    '8': ['불러올 데이터를 골라 주세요'],
    'GS_V1': ['게임 시작'],
    'MENEU': ['시작 메뉴'],
    'MES_01': ['여행을 떠날 때'], 'MES_02': ['검은 안개가 걷히고'], 'MES_03': ['꿈에 들어가는 약'], 'MES_04': ['로빈을 찾아서'],
    'MES_05': ['크라운 마을로'], 'MES_06': ['장로의 행방'], 'MES_07': ['야크의 사탑'], 'MES_08': ['자, 하늘의 섬으로'],
    'MES_09': ['떠오른 옛 대륙'], 'MES_10': ['생명을 빨아들이는 돌'], 'MES_11': ['돌을 부숴라'], 'MES_12': ['장로 구출'],
    'MES_13': ['부활의 운가로'], 'MES_14': ['비보를 찾아서①'], 'MES_15': ['비보를 찾아서②'], 'MES_16': ['비보를 찾아서③'],
    'MES_17': ['마지막 싸움'],
    'NEW10': ['어느 데이터에 복사할까요?'], 'NEW11': ['©복사/Ⓑ그만두기'],
    'NEW12': ['어느 데이터를 지울까요?'], 'NEW13': ['©지우기/Ⓑ그만두기'],
    'NEW1_B': ['처음부터'], 'NEW2': ['시작'], 'NEW3': ['복사'], 'NEW4': ['삭제'], 'NEW5': ['설정'],
    'NEW6': ['어느 데이터로 시작할까요?'], 'NEW7': ['©처음부터/Ⓑ그만두기'], 'NEW8': ['©이어서/Ⓑ그만두기'],
    'NEW9': ['어느 데이터를 복사할까요?'],
}
_T = {'A': '마법', 'B': '공격', 'C': '점프', 'X': '아이템', 'Y': '아이템', 'Z': '아이템', 'L': '무기 타입 선택', 'R': '무기 타입 선택'}
TYPE = {   # 원문 그림 그대로 옮김(버튼 → 기능)
    'TYPE_A': ['A-마법', 'B-공격', 'C-점프', 'X-(사용 안 함)', 'Y-(사용 안 함)', 'Z-아이템', 'L-무기 타입 선택', 'R-무기 타입 선택'],
    'TYPE_B': ['A-아이템', 'B-공격', 'C-점프', 'X-(사용 안 함)', 'Y-(사용 안 함)', 'Z-마법', 'L-무기 타입 선택', 'R-무기 타입 선택'],
    'TYPE_C': ['A-마법', 'B-공격', 'C-점프', 'X-무기 타입 선택', 'Y-무기 타입 선택', 'Z-아이템', 'L-(사용 안 함)', 'R-(사용 안 함)'],
    'TYPE_D': ['A-아이템', 'B-공격', 'C-점프', 'X-무기 타입 선택', 'Y-무기 타입 선택', 'Z-마법', 'L-(사용 안 함)', 'R-(사용 안 함)'],
    'TYPE_E': ['A-마법', 'B-공격', 'C-점프', 'X-아이템', 'Y-무기 타입 선택', 'Z-무기 타입 선택', 'L-무기 타입 선택', 'R-무기 타입 선택'],
    'TYPE_F': ['A-아이템', 'B-공격', 'C-점프', 'X-마법', 'Y-무기 타입 선택', 'Z-무기 타입 선택', 'L-무기 타입 선택', 'R-무기 타입 선택'],
}
KO.update(TYPE)


def load(n):
    d = open(os.path.join(SRC, n + '.XGD'), 'rb').read(); w, h = struct.unpack_from('<HH', d, 0)
    a = np.zeros((h, w), int)
    for y in range(h):
        for x in range(w): a[y, x] = (d[4 + (y * w + x) // 2] >> (4 if x % 2 == 0 else 0)) & 15
    return d[:4], a


def save(head, a):
    h, w = a.shape; out = bytearray(head)
    for y in range(h):
        for x in range(0, w, 2): out.append((a[y, x] << 4) | a[y, x + 1])
    return bytes(out)


def has(font, ch):
    from fontTools.ttLib import TTFont
    if font not in has.c: has.c[font] = set(TTFont(font).getBestCmap())
    return ord(ch) in has.c[font]
has.c = {}


def render(text, size):
    """글자열 → 덮임 배열(높이 = size+4, 기준선 맞춤)·잉크 폭"""
    text = re.sub('([%s]) +' % re.escape(PUNCT), r'\1', text)            # 문장부호 뒤 공백 지움(규칙)
    f1 = ImageFont.truetype(FONT, int(size * SS)); f2 = ImageFont.truetype(FALLBACK, int(size * SS))
    W = int(size * SS * (len(text) + 2)); H = int((size + 6) * SS)
    im = Image.new('L', (W, H)); dr = ImageDraw.Draw(im); x = 0
    for ch in text:
        f = f1 if has(FONT, ch) else f2
        dr.text((x, int(1 * SS)), ch, font=f, fill=255)
        x += dr.textlength(ch, font=f)
    a = np.asarray(im.resize((W // SS, H // SS), Image.BOX), dtype=float) / 255
    cols = np.nonzero(a.max(axis=0) > 0.08)[0]; rows = np.nonzero(a.max(axis=1) > 0.08)[0]
    return a[rows.min():rows.max() + 1, cols.min():cols.max() + 1]


def bands(a, x0, x1):
    ys = [y for y in range(a.shape[0]) if (a[y, x0:x1 + 1] >= 4).any()]
    out = []
    for y in ys:
        if out and y <= out[-1][1] + 1: out[-1][1] = y
        else: out.append([y, y])
    return out


def build(n):
    head, a = load(n); box = np.argwhere(a == 3)
    bx0, bx1 = box[:, 1].min(), box[:, 1].max()
    lines = KO[n]; bs = bands(a, bx0, bx1)
    if len(bs) != len(lines): raise SystemExit('⛔ %s 줄 수 %d ≠ 번역 %d' % (n, len(bs), len(lines)))
    new = a.copy()
    gx0 = min(np.argwhere(a[y0:y1 + 1] >= 4)[:, 1].min() for y0, y1 in bs)   # 여러 줄은 공통 시작 x(줄마다 첫 글자 폭이 달라 들쭉날쭉 방지)
    for (y0, y1), t in zip(bs, lines):
        seg = a[y0:y1 + 1]; ink = np.argwhere(seg >= 4); x0, x1 = ink[:, 1].min(), ink[:, 1].max()
        if len(bs) > 1: x0 = gx0
        new[y0:y1 + 1][seg >= 4] = 3                                      # 글자 지움(상자 바탕)
        left = n in LEFT or n.startswith('TYPE_') or (x0 - bx0) * 2 <= (bx1 - x1) and n not in ('17',)
        room = (bx1 - 2) - (x0 if left else bx0 + 2) + 1
        size = SIZE
        while True:
            g = render(t, size)
            if g.shape[1] <= room or size <= 10: break
            size -= 0.5
        if g.shape[1] > room: raise SystemExit('⛔ %s «%s» 폭 %d > 자리 %d' % (n, t, g.shape[1], room))
        gx = x0 if left else int(round((x0 + x1) / 2 - g.shape[1] / 2))
        gx = max(bx0 + 1, min(gx, bx1 - g.shape[1]))
        gy = int(round((y0 + y1) / 2 - g.shape[0] / 2))
        v = np.rint(3 + 12 * g).astype(int)
        reg = new[gy:gy + g.shape[0], gx:gx + g.shape[1]]
        assert (a[gy:gy + g.shape[0], gx:gx + g.shape[1]] >= 3).all(), ('상자 밖에 그림', n, t)
        new[gy:gy + g.shape[0], gx:gx + g.shape[1]] = np.where(g > 0.06, np.maximum(reg, v), reg)
    return head, a, new


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import struct as S
    c = open(os.path.join(ROOT, 'work', 'mem', 's4', 'CRAM.bin'), 'rb').read()
    pal = [((w & 31) * 8, ((w >> 5) & 31) * 8, ((w >> 10) & 31) * 8) for w in (S.unpack_from('<H', c, 2 * k)[0] for k in range(16))]
    pal[0] = (60, 90, 60)                                                  # 투명 = 초록(미리보기만)
    od = os.path.join(ROOT, 'work', 'build', 'IKECG'); os.makedirs(od, exist_ok=True)
    pairs = []
    for n in KO:
        head, a, new = build(n)
        open(os.path.join(od, n + '.XGD'), 'wb').write(save(head, new))
        pairs.append((n, a, new))
    def img(a, k=2):
        return Image.fromarray(np.array([[pal[v] for v in r] for r in a], dtype=np.uint8)).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)
    pages = []; cur = []; hsum = 0
    for p in pairs:
        h = p[1].shape[0] * 2 + 18
        if hsum + h > 1400 and cur: pages.append(cur); cur = []; hsum = 0
        cur.append(p); hsum += h
    pages.append(cur)
    lab = ImageFont.truetype(FALLBACK, 13)
    for i, pg in enumerate(pages):
        W = max(p[1].shape[1] for p in pg) * 4 + 30; H = sum(p[1].shape[0] * 2 + 18 for p in pg)
        S_ = Image.new('RGB', (W, H), (30, 30, 30)); d = ImageDraw.Draw(S_); y = 0
        for n, a, new in pg:
            d.text((2, y), n, font=lab, fill=(255, 255, 0)); S_.paste(img(a), (0, y + 16)); S_.paste(img(new), (a.shape[1] * 2 + 20, y + 16)); y += a.shape[0] * 2 + 18
        S_.save(os.path.join(ROOT, 'work', 'shot', 'menu_preview_%d.png' % (i + 1)))
    print('그림 %d장 → work/build/IKECG · 미리보기 %d장 work/shot/menu_preview_*.png' % (len(pairs), len(pages)))


if __name__ == '__main__':
    main()
