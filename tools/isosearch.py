# -*- coding: utf-8 -*-
"""글자 같음 무늬 검색(2026-10-30) — 인코딩을 모를 때 «같은 글자 = 같은 코드, 다른 글자 = 다른 코드» 로 문자열 찾기
  python tools/isosearch.py <문자열> <파일…>   (1·2 바이트 단위, 2바이트는 BE)"""
import sys, glob


def pattern(s):
    m = {}; return [m.setdefault(c, len(m)) for c in s]


def search(d, s, width):
    pat = pattern(s); n = len(s); out = []
    units = [d[i:i + width] for i in range(0, len(d) - width + 1, 1)]
    for st in range(0, len(d) - n * width):
        m = {}; rev = {}; ok = True
        for k in range(n):
            u = d[st + k * width:st + k * width + width]
            p = pat[k]
            if m.setdefault(p, u) != u or rev.setdefault(u, p) != p: ok = False; break
        if ok: out.append(st)
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    s = sys.argv[1]
    for f in [g for a in sys.argv[2:] for g in glob.glob(a)]:
        d = open(f, 'rb').read()
        for w in (1, 2):
            h = search(d, s, w)
            if 0 < len(h) < 50:
                for a in h[:5]: print(f, 'w%d' % w, hex(a), d[a:a + len(s) * w].hex(' '))
