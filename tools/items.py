# -*- coding: utf-8 -*-
"""아이템 이름·설명(GAME.BIN, 램 0x0600E000 적재) 추출(2026-10-31)
  색인 0x80D30 u16×24(워드 오프셋, 0 = 없음 — 21개) · 본문 0x80D60~0x812FC(1,436 B) — 0x06075678 이 색인[아이템]·0x0607568A 가 본문 기준(리터럴 0x06075758)
  글자 = 공통 글꼴 코드(0x000~0x106, 모든 DATA 같음) → DATA19 글꼴로 판정
  한 항목 = 이름 ／ 설명 줄들 ／／ (FFFF FFFF 끝)
  python tools/items.py → work/text/items.tsv · my files/tsv/ll_item.tsv(번역용)"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import datafile as D, decode

TBL, BODY, END, N = 0x80D30, 0x80D60, 0x812FC, 24


def entries(g):
    out = []
    for k in range(N):
        o = struct.unpack_from('>H', g, TBL + 2 * k)[0]
        if not o: continue
        a = BODY + 2 * o; ws = []
        while True:
            w = struct.unpack_from('>H', g, a)[0]; ws.append(w); a += 2
            if len(ws) >= 2 and ws[-2:] == [0xFFFF, 0xFFFF]: break
        out.append((k, BODY + 2 * o, ws))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(os.path.join(ROOT, 'work', 'disc0', 'GAME.BIN'), 'rb').read()
    M = decode.glyph_map(); d = open(os.path.join(ROOT, 'work', 'disc0', 'DATA19.BIN'), 'rb').read(); i = D.parse(d)
    rows = []
    for k, a, ws in entries(g):
        assert all(w < 0x107 or w == 0xFFFF for w in ws), (k, ws)
        rows.append((k, a, decode.dec(d, i, ws, M)))
    with open(os.path.join(ROOT, 'work', 'text', 'items.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\t위치\tJP\n')
        for k, a, s in rows: o.write('%02d\tGAME:%X\t%s\n' % (k, a, s))
    with open(os.path.join(ROOT, 'my files', 'tsv', 'll_item.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\t위치\tJP\tKO\n')
        for k, a, s in rows: o.write('%02d\tGAME:%X\t%s\t\n' % (k, a, s))
    for r in rows: print(r[0], r[2])
    print('항목 %d · 본문 %d / %d 워드' % (len(rows), sum(len(e[2]) for e in entries(g)), (END - BODY) // 2))


if __name__ == '__main__':
    main()
