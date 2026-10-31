# -*- coding: utf-8 -*-
"""DATA##.BIN 전체 메시지 추출(2026-10-31) → work/text/script.tsv
  열: ID(파일:번호) · 같은글(처음 나온 ID, 중복이면) · JP(glyphs.tsv 판정) · 원본 워드(hex, 재삽입 검산용)
  제어: ／ = FFFF(줄 끝, 메시지 끝 ／／) · {名} = FFFE · {FFxx} = 그 밖(얼굴·화자 지정으로 보임)
  python tools/extract.py"""
import os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import datafile as D, decode

SKIP = ('DATA98.BIN', 'DATA99.BIN')     # 98·99 = 머리 형식 다름(따로 조사)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    M = decode.glyph_map(); first = {}; rows = []; uniq_chars = 0; tot = 0
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc0', 'DATA*.BIN'))):
        n = os.path.basename(f)
        if n in SKIP: continue
        d = open(f, 'rb').read(); i = D.parse(d)
        for k, a, ws in D.messages(d, i):
            jp = decode.dec(d, i, ws, M); mid = '%s:%d' % (n[4:6], k)
            dup = first.get(jp, '')
            if not dup: first[jp] = mid; uniq_chars += sum(1 for w in ws if w < 0xFF00)
            tot += sum(1 for w in ws if w < 0xFF00)
            rows.append((mid, dup, jp, ''.join('%04X' % w for w in ws)))
    with open(os.path.join(ROOT, 'work', 'text', 'script.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('ID\t같은글\tJP\tWORDS\n')
        for r in rows: o.write('\t'.join(r) + '\n')
    print('메시지 %d (중복 빼면 %d) · 글자 %d (중복 빼면 %d)' % (len(rows), len(first), tot, uniq_chars))


if __name__ == '__main__':
    main()
