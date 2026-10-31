# -*- coding: utf-8 -*-
"""번역 TSV 만들기(2026-10-31) — script.tsv 에서 같은 대사 빼고 881개 → my files/tsv/ll_###.tsv(18KB 단위, 자투리는 앞 파일에 합침)
  열: 번호 · 위치(처음 ID, 같은 대사 수) · JP · KO(빈칸)
  JP 의 ／(줄 끝·메시지 끝)·{名}·{FFxx} 는 그대로 KO 에 남길 것
  python tools/mk_tsv.py"""
import csv, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 18 * 1024


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'script.tsv'), encoding='utf-8'), delimiter='\t'))
    cnt = {}
    for r in rows:
        k = r['같은글'] or r['ID']; cnt[k] = cnt.get(k, 0) + 1
    uniq = [r for r in rows if not r['같은글']]
    head = '번호\t위치\tJP\tKO\n'
    lines = ['%05d\t%s(×%d)\t%s\t\n' % (n + 1, 'DATA' + r['ID'], cnt[r['ID']], r['JP']) for n, r in enumerate(uniq)]
    chunks = [[]]; size = len(head.encode())
    for ln in lines:
        b = len(ln.encode())
        if chunks[-1] and size + b > LIMIT: chunks.append([]); size = len(head.encode())
        chunks[-1].append(ln); size += b
    if len(chunks) > 1 and sum(len(l.encode()) for l in chunks[-1]) < LIMIT // 3: chunks[-2] += chunks.pop()
    out = os.path.join(ROOT, 'my files', 'tsv'); os.makedirs(out, exist_ok=True)
    for i, c in enumerate(chunks):
        p = os.path.join(out, 'll_%03d.tsv' % (i + 1))
        open(p, 'w', encoding='utf-8', newline='\n').write(head + ''.join(c))
        print(os.path.basename(p), len(c), '줄', os.path.getsize(p), 'B')


if __name__ == '__main__':
    main()
