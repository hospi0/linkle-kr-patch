# -*- coding: utf-8 -*-
"""DATA##.BIN 구조(2026-10-31) — WorkRAML 0x00200000 에 통째로 실림
  머리 0x100~: 램 주소 u32 목록 … «DAT0nn» 서명 앞까지. 끝에서 [-4] 메시지 색인(u16 워드 오프셋, 0 = 빈 칸) · [-3] 대사 본문 · [-2] 글꼴 시작 · [-1] 글꼴 끝
  글꼴 = 14×14 4bpp(98 B/글자, 바탕 1) — 코드 = 글자 번호
  python tools/datafile.py → 파일마다 구역·메시지 수·글꼴 글자 수"""
import os, struct, glob, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0x00200000
G = 98


def sections(d):
    sig = d.find(b'DAT0', 0x100)
    ptrs = [struct.unpack_from('>I', d, o)[0] for o in range(0x100, sig, 4)]
    return ptrs, sig


def parse(d):
    """엔진과 같은 규칙(0x0601B44C 등): 묶음 = 머리 + 4×u32@0x7C → [+0] 색인 [+4] 본문 [+8] 글꼴(×98)"""
    ptrs, sig = sections(d)
    grp = 4 * struct.unpack_from('>I', d, 0x7C)[0]
    tb, tx, f0 = [struct.unpack_from('>I', d, grp + 4 * k)[0] - BASE for k in range(3)]
    f1 = struct.unpack_from('>I', d, grp + 12)[0] - BASE if grp + 12 < sig else len(d)
    if not f0 < f1 <= len(d) or (f1 - f0) % G: f1 = len(d)               # DATA17: 글꼴 끝 포인터 없음 → 파일 끝
    offs = [struct.unpack_from('>H', d, tb + 2 * i)[0] for i in range((tx - tb) // 2)]
    return dict(grp=grp, ptrs=ptrs, sig=sig, table=tb, text=tx, font=f0, font_end=f1, offs=offs, nglyph=(f1 - f0) // G)


def messages(d, info):
    """(번호, 시작 바이트, 워드 목록) — 색인 0 은 빈 칸, 끝 = 다음 큰 오프셋"""
    tx = info['text']; lim = (info['font'] - tx) // 2
    ends = sorted(set(o for o in info['offs'] if 0 < o < lim) | {lim})
    out = []
    for i, o in enumerate(info['offs']):
        if not 0 < o < lim: continue
        e = ends[ends.index(o) + 1]
        out.append((i, tx + 2 * o, [struct.unpack_from('>H', d, tx + 2 * k)[0] for k in range(o, e)]))
    return out


def glyph(d, info, c):
    return d[info['font'] + c * G:info['font'] + (c + 1) * G]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc0', 'DATA*.BIN'))):
        d = open(f, 'rb').read()
        try: i = parse(d)
        except Exception as e: print(os.path.basename(f), '실패', e); continue
        ms = messages(d, i)
        print('%s 색인 %05X 본문 %05X 글꼴 %05X~%05X(%d자, 나머지 %d B) 메시지 %d 워드 %d 파일끝 %X' % (os.path.basename(f), i['table'], i['text'], i['font'], i['font_end'], i['nglyph'], (i['font_end'] - i['font']) % G, len(ms), sum(len(m[2]) for m in ms), len(d)))
