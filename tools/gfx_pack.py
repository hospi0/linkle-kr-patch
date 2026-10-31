# -*- coding: utf-8 -*-
r"""IKECG 묶음 파일에 한글 그림 반영(2026-10-31) — ★게임은 IKECG\*.XGD 낱장이 아니라 XCGALL·TICGALL·ERCGALL.BIN 안 사본을 읽음
  (낱장만 바꿔 넣어 실기에서 한글 그림이 하나도 안 나왔음 — 하스피 지적)
  묶음 안 사본 = XGD 의 4바이트 머리(가로·세로) 뺀 화소 본문 그대로. 원본 본문을 묶음에서 모두 찾아 한글 본문으로 같은 크기 교체
  work/build/IKECG/*.XGD(gfx_menu.py·nameentry.py 결과) → work/build/IKECG/<묶음>.BIN
  본문을 하나도 못 찾은 그림이 있으면 중단 · 바뀐 바이트가 찾은 자리 밖이면 중단
  python tools/gfx_pack.py   (gfx_menu.py·nameentry.py 다음에)"""
import glob, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'disc0', 'IKECG'); OUT = os.path.join(ROOT, 'work', 'build', 'IKECG')
ARCS = ('XCGALL.BIN', 'TICGALL.BIN', 'ERCGALL.BIN')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    orig = {a: open(os.path.join(SRC, a), 'rb').read() for a in ARCS}
    new = {a: bytearray(d) for a, d in orig.items()}
    owned = {a: [] for a in ARCS}
    miss = []; total = 0
    for p in sorted(glob.glob(os.path.join(OUT, '*.XGD'))):
        n = os.path.basename(p)
        o = open(os.path.join(SRC, n), 'rb').read()[4:]; k = open(p, 'rb').read()[4:]
        assert len(o) == len(k), n
        if o == k: continue
        hits = 0
        for a in ARCS:
            i = orig[a].find(o)
            while i >= 0:
                new[a][i:i + len(k)] = k; owned[a].append((i, i + len(k))); hits += 1
                i = orig[a].find(o, i + 1)
        if not hits: miss.append(n)
        total += hits
    # 50ON(이름 미리보기 글꼴)은 묶음 안에 «16×16 칸 단위(칸마다 128B 연속)»로 160칸 들어 있음(TICGALL 0x0 · XCGALL 0xF000) — 낱장 모양 검색에 안 걸림(2026-10-31 실기: 미리보기만 가나)
    for n, w in (('50ON.XGD', 320),):
        o = open(os.path.join(SRC, n), 'rb').read()[4:]; k = open(os.path.join(OUT, n), 'rb').read()[4:]
        cell = lambda s, c: b''.join(s[((c // 20) * 16 + r) * w // 2 + (c % 20) * 8:((c // 20) * 16 + r) * w // 2 + (c % 20) * 8 + 8] for r in range(16))
        hits = 0
        for c in range(len(o) // 128):
            co, ck = cell(o, c), cell(k, c)
            if co == ck: continue
            for a in ARCS:
                i = orig[a].find(co)
                while i >= 0:
                    if i % 128 == 0 or a != 'ERCGALL.BIN':
                        new[a][i:i + 128] = ck; owned[a].append((i, i + 128)); hits += 1
                    i = orig[a].find(co, i + 1)
        if not hits: sys.exit('⛔ %s 칸 단위 사본 못 찾음' % n)
        print('%s 칸 단위 사본 %d곳 교체' % (n, hits)); total += hits
    STANDALONE = {'17.XGD', '18_BEGI.XGD', '18_OPS.XGD', '18_SERI.XGD', '50ON.XGD', '8.XGD', 'GS_V1.XGD'}   # 디스크 어디에도 사본 없음(조각 검색 0) = 낱장으로 읽힘
    bad = [m for m in miss if m not in STANDALONE]
    if bad: sys.exit('⛔ 묶음에서 본문 못 찾은 그림: %s' % ' '.join(bad))
    print('낱장으로만 있는 그림(사본 없음) %d: %s' % (len(miss), ' '.join(miss)))
    for a in ARCS:
        d0, d1 = orig[a], new[a]
        chg = [j for j in range(len(d0)) if d0[j] != d1[j]]
        bad = [j for j in chg if not any(s <= j < e for s, e in owned[a])]
        if bad: sys.exit('⛔ %s 찾은 자리 밖 변경 %d' % (a, len(bad)))
        if chg:
            open(os.path.join(OUT, a), 'wb').write(bytes(d1))
        print('%-12s 사본 %d곳 · 바뀐 바이트 %d' % (a, len(owned[a]), len(chg)))
    print('한글 그림 사본 교체 합계 %d곳' % total)


if __name__ == '__main__':
    main()
