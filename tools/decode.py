# -*- coding: utf-8 -*-
"""DATA 메시지 → 글자열(work/text/glyphs.tsv 판정 기준). python tools/decode.py DATA19 [첫 번호 개수]"""
import csv, hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import datafile as D


def glyph_map():
    """OCR 판정(glyphs.tsv) + 손 고침(glyph_fix.tsv, 글자 그림 sha1 → 글자)"""
    m = {r['sha1']: r['글자'] for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'glyphs.tsv'), encoding='utf-8'), delimiter='\t')}
    fx = os.path.join(ROOT, 'work', 'text', 'glyph_fix.tsv')
    if os.path.exists(fx):
        for r in csv.DictReader(open(fx, encoding='utf-8'), delimiter='\t'): m[r['sha1']] = r['글자']
    return m


KATA_LIKE = {'口': 'ロ', '卜': 'ト', '力': 'カ', '工': 'エ', '二': 'ニ', '夕': 'タ', '八': 'ハ', '一': 'ー'}


def is_kata(c):
    return 'ァ' <= c <= 'ヺ' or c == 'ー'


def fix(s):
    """가타카나 옆의 비슷한 한자 → 가타카나(口ビン→ロビン·オオ卜カゲ→オオトカゲ), 가타카나 사이 리 그대로, 히라가나 사이 リ→り"""
    s = list(s)
    for k, c in enumerate(s):
        a = s[k - 1] if k else ''; b = s[k + 1] if k + 1 < len(s) else ''
        if c in KATA_LIKE and (is_kata(a) or is_kata(b)): s[k] = KATA_LIKE[c]
        elif c in 'リヘベペ' and not (is_kata(a) or is_kata(b)): s[k] = {'リ': 'り', 'ヘ': 'へ', 'ベ': 'べ', 'ペ': 'ぺ'}[c]   # 같은 모양 — 가타카나 옆이 아니면 히라가나
    return ''.join(s)


def dec(d, i, ws, M):
    o = ''
    for w in ws:
        if w == 0xFFFF: o += '／'
        elif w == 0xFFFE: o += '{名}'
        elif w >= 0xFF00: o += '{%X}' % w
        elif w < i['nglyph']: o += M[hashlib.sha1(D.glyph(d, i, w)).hexdigest()[:12]]
        else: o += '{?%X}' % w
    return fix(o)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    M = glyph_map(); d = open(os.path.join(ROOT, 'work', 'disc0', sys.argv[1] + '.BIN'), 'rb').read(); i = D.parse(d)
    ms = D.messages(d, i); s = int(sys.argv[2]) if len(sys.argv) > 2 else 0; n = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    for k, a, ws in ms[s:s + n]: print(k, dec(d, i, ws, M))
