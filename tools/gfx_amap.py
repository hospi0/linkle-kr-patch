# -*- coding: utf-8 -*-
r"""월드맵 지명·저장 안내 그림 한글화(2026-10-31 하스피 스샷 「水辺の森ロンド」)
  AMAP.BIN(월드맵 프로그램, 램 0x0600E000) 0x1FFD4 부터 27장 연달아: [u16 LE 가로][u16 LE 세로][8bpp 화소] — 크기 그대로 다시 그림
  팔레트 = CRAM 0x100~(VDP1 색 0x100) 회색 사다리: 번호 k = 밝기 8k(0 검정 ~ 31 흰색) → 안티에일리어스 덮임 비율 그대로 번호로
  0~23 = 검정 바탕 지명 · 24~26 = 회색 상자(번호 8, 테 0) 안 글 → 바탕 지우고(검정/상자색) 가운데 정렬로 그림
  디스크 다른 곳에 같은 그림 사본 없음(전 파일 검색 2026-10-31) · 지명 = 본편 대사 표기
  python tools/gfx_amap.py → work/build/AMAP.BIN · 미리보기 my files/그림미리보기/월드맵_지명.png"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START, N = 0x1FFD4, 27
FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
KO = ['물가의 숲 론도', '인어 동굴', '산호 부도', '작은 사당', '머신헤드', '판다 계곡', '크라운 마을', '지상화 유적',
      '헬레네 산맥', '캇시 폭포', '폭포 바위산', '옥수수 밭', '미스트랄 고산', '수수께끼 시계탑', '사계의 대륙', '야크의 사탑',
      '떨어진 섬', '코냑 삼림', '첼리오 활화산', '용수로 유적', '암석 광장', '판다 유적', '용수로 요새', None,
      'Ⓒ저장／Ⓑ그만두기', '저장 완료', '현재 저장 기능은 사용할 수 없습니다']


def entries(d):
    p = START; out = []
    for _ in range(N):
        w, h = struct.unpack_from('<HH', d, p); out.append((p + 4, w, h)); p += 4 + w * h
    return out


def render(text, w, h, size, bg):
    """글 → 번호 배열(가로 w 넘으면 크기 줄임)"""
    while True:
        f = ImageFont.truetype(FONT, size)
        if f.getlength(text) <= w - 2 or size <= 8: break
        size -= 1
    im = Image.new('L', (w, h), 0); ImageDraw.Draw(im).text((w / 2, h / 2), text, font=f, fill=255, anchor='mm')
    cov = np.asarray(im).astype(np.float32) / 255
    return np.clip(np.round(bg + cov * (31 - bg)), 0, 31).astype(np.uint8), size


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = bytearray(open(os.path.join(ROOT, 'work', 'disc0', 'AMAP.BIN'), 'rb').read()); d0 = bytes(d)
    c = open(os.path.join(ROOT, 'work', 'mem', 's_wmap', 'CRAM.bin'), 'rb').read()
    pal = np.array([((w & 31) * 8, ((w >> 5) & 31) * 8, ((w >> 10) & 31) * 8) for w in (struct.unpack_from('<H', c, 2 * (0x100 + k))[0] for k in range(256))], np.uint8)
    rows = []
    for n, ((p, w, h), ko) in enumerate(zip(entries(d), KO)):
        a = np.frombuffer(d0, np.uint8, w * h, p).reshape(h, w).copy()
        if ko is None: rows.append((a, a)); continue
        if n < 24:
            b, sz = render(ko, w, h, 13, 0)
        else:                                                             # 상자: 테(0) 안쪽 번호 8 영역에 그림
            ys, xs = np.where(a == 8); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            t = ko.replace('／', '/')
            inner, sz = render(t, x1 - x0, y1 - y0, 15, 8)
            b = a.copy(); b[y0:y1, x0:x1] = inner
        d[p:p + w * h] = b.tobytes(); rows.append((a, b))
        print('%2d %3dx%-2d %s (크기 %d)' % (n, w, h, ko, sz))
    assert len(d) == len(d0)
    os.makedirs(os.path.join(ROOT, 'work', 'build'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'build', 'AMAP.BIN'), 'wb').write(bytes(d))
    K = 3; W = max(a.shape[1] for a, _ in rows) * K * 2 + 30; H = sum(a.shape[0] * K + 6 for a, _ in rows)
    S = Image.new('RGB', (W, H), (60, 0, 60)); y = 0
    for a, b in rows:
        for j, x in enumerate((a, b)):
            S.paste(Image.fromarray(pal[x]).resize((x.shape[1] * K, x.shape[0] * K), Image.NEAREST), (j * (W // 2), y))
        y += a.shape[0] * K + 6
    od = os.path.join(ROOT, 'my files', '그림미리보기'); os.makedirs(od, exist_ok=True)
    S.save(os.path.join(od, '월드맵_지명.png')); print('→ work/build/AMAP.BIN · 미리보기', os.path.join(od, '월드맵_지명.png'))


if __name__ == '__main__':
    main()
