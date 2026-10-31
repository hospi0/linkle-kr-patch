# -*- coding: utf-8 -*-
r"""링클 리버 스토리 대사 빌드(2026-10-31 PoC) — 번역 TSV → DATA##.BIN → work/build/
  번역 입력: work/text/poc_ko.tsv (번호·위치·JP·KO — my files/tsv/ll_###.tsv 와 같은 꼴), KO 빈칸 = 원문 그대로
    같은 대사(같은 JP)는 모든 DATA 파일에 같은 번역이 들어감
  토큰: ／ = FFFF · {名} = FFFE · {FFxx} = 제어 — JP 와 차례·개수가 다르면 중단
  문장부호 뒤 공백은 무조건 지움(PUNCT). 반각 공백 ' ' = 그 파일의 전각 빈칸(　) 코드
  글꼴: 코드 0x000~0x106 = 모든 DATA 공통(GAME.BIN 아이템 설명 등이 같은 코드로 씀, DATA07 만 0xC0~ 다름) → 손대지 않음
    새 글자(한글·반각 부호)는 «지역 칸(0x107~) 중 번역 뒤 어떤 메시지도 안 쓰는 칸»에 덮어씀(높은 번호부터) — 파일 크기 그대로
    모자라면 파일 끝에 덧붙임 — 코드 = (자리 − 글꼴 시작)/98 (디스크 자리 문제는 discbuild)
    (엔진은 글꼴 주소를 머리 묶음 [+8] 에서 읽고 코드 ≥ 0xF000 은 제어 — 0x0601B31C)
  본문: 메시지를 원래 순서대로 다시 채우고 색인(u16 워드 오프셋) 고침 — 글꼴 시작을 넘으면 중단
  --name: 이름 음절 160(nameentry.SYL)을 코드 0x00~0x9F 공통 칸에(모든 DATA), 대사 한글도 그 음절은 그 코드로
  python tools/build.py [번역 tsv …] [--name]"""
import csv, glob, hashlib, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import datafile as D, decode, kglyph, nameentry
NAME = '--name' in sys.argv                                              # 이름 음절(코드 0x00~0x9F 공통 칸)을 모든 DATA 에 — 가나가 한글로 바뀌므로 대사·아이템 전부 번역됐을 때만

STYLE = 'B_나눔고딕ExtraBold13'                                           # 하스피 선택(2026-10-31)
PUNCT = '.,!?…:;~、。，．！？：；～·'                                     # 뒤 공백 지움
REUSE = '：…　！？。、「」『』～ー・（）〈〉《》＜＞０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ'   # 원래 글꼴 칸을 그대로 쓰는 글자
TOK = re.compile(r'／|\{名\}|\{FF[0-9A-F]{2}\}')
SKIP = ('DATA98.BIN', 'DATA99.BIN')
LOCAL = 0x107                                                           # 지역 글꼴 시작(그 아래 공통)
ITEM_CODES = [0xA0, 0xCF, 0xD0, 0xD1, 0xD2] + list(range(0xE0, 0x107))  # 공통 칸 중 이름 음절(0x00~0x9F) 밖 44칸 → 아이템 설명 한글: 0xA0 · 번역에 안 쓰는 ‘’“” · 원래 아이템 한자 0xE0~ (DATA07 은 0xC0~ 가 달라 안 씀)
ITEM_FREED = '‘’“”'                                                       # 아이템 칸으로 돌린 부호 — 번역에 나오면 중단
ITEM_TBL, ITEM_BODY, ITEM_END = 0x80D30, 0x80D60, 0x812F8               # GAME.BIN 아이템 색인·본문(tools/items.py) — 0x812F8~ 는 실행 중 바뀌는 변수(스테이트 대조)
ITEM_LIT, ITEM_RELOC = 0x06075758, 0x06010000                            # 본문 기준 주소 리터럴(0x0607568A 가 읽음) · 넘칠 때 옮길 곳(GAME.BIN 0x0600FDD0~ 25 KB 0 구간)
FW = {c: chr(ord(c) + 0xFEE0) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'} | {'(': '（', ')': '）'}   # 반각 영숫자·괄호 → 전각(글꼴에 있음)


def load_ko(paths):
    ko = {}
    for p in paths:
        for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
            k = (r.get('KO') or '').strip()
            if k: ko[r['JP']] = k
    return ko


def tokens(s):
    return TOK.findall(s)


def strip_punct_space(s):
    return re.sub('([%s])[ 　]+' % re.escape(PUNCT), r'\1', s)


def encode(ko, rev, new, kname=None):
    """KO 문자열 → 워드 목록. rev = 이 파일 글꼴에서 재사용할 글자→코드, new = 새 글자 목록(차례 = 덧붙일 순서)"""
    out = []; k = 0
    while k < len(ko):
        m = TOK.match(ko, k)
        if m:
            t = m.group(0)
            out.append(0xFFFF if t == '／' else 0xFFFE if t == '{名}' else int(t[1:-1], 16)); k = m.end(); continue
        ch = ko[k]; k += 1
        if ch == ' ': ch = '　'
        ch = FW.get(ch, ch)
        if kname and ch in kname: out.append(kname[ch]); continue          # 이름 음절 공통 칸
        if ch in ITEM_FREED: sys.exit('⛔ 아이템 칸으로 돌린 부호 %r 가 번역에 있음' % ch)
        if ch in REUSE and ch in rev: out.append(rev[ch]); continue
        if ch in REUSE: sys.exit('⛔ 원래 글꼴에 없는 부호 %r' % ch)
        if not ('가' <= ch <= '힣' or ch in '.,!?~-'): sys.exit('⛔ 글꼴 공급 안 되는 글자 %r in %s' % (ch, ko))
        if ch not in new: new.append(ch)
        out.append(('new', ch))
    return out


def item_map():
    """아이템 설명 음절 중 이름 음절에 없는 것 → 공통 남는 칸(ITEM_CODES)"""
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'ko_item_short.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
    syl = sorted(set(re.findall('[가-힣]', ''.join(r['KO'] for r in rows))) - set(nameentry.SYL))
    if len(syl) > len(ITEM_CODES): sys.exit('⛔ 아이템 음절 %d > 공통 남는 칸 %d' % (len(syl), len(ITEM_CODES)))
    return rows, dict(zip(syl, ITEM_CODES))


def build_file(path, ko, M):
    d = bytearray(open(path, 'rb').read()); i = D.parse(bytes(d)); orig = bytes(d)    # 판독은 원본으로(글꼴 덮어쓰기 전)
    rev = {}
    for c in range(i['nglyph']):
        ch = M[hashlib.sha1(D.glyph(d, i, c)).hexdigest()[:12]]
        if ch in REUSE: rev.setdefault(ch, c)
    msgs = D.messages(bytes(d), i)
    kname = {ch: k for k, ch in enumerate(nameentry.SYL)} if NAME else None
    if NAME:
        for k, ch in enumerate(nameentry.SYL): d[i['font'] + D.G * k:i['font'] + D.G * (k + 1)] = kglyph.glyph(ch, STYLE)
        if os.path.basename(path) != 'DATA07.BIN':                         # 아이템 설명 공통 칸(DATA07 은 0xC0~ 배치가 달라 제외)
            assert not set(rev.values()) & set(ITEM_CODES), ('재사용 부호가 아이템 칸에', os.path.basename(path))
            for ch, c in item_map()[1].items(): d[i['font'] + D.G * c:i['font'] + D.G * (c + 1)] = kglyph.glyph(ch, STYLE)
    new = []; enc = {}; changed = 0
    for n, a, ws in msgs:
        jp = decode.dec(orig, i, ws, M)
        if jp in ko:
            k = strip_punct_space(ko[jp])
            if tokens(k) != tokens(jp): sys.exit('⛔ 토큰 다름 %s\n  JP %s\n  KO %s' % (os.path.basename(path), tokens(jp), tokens(k)))
            enc[n] = encode(k, rev, new, kname); changed += 1
        else:
            enc[n] = list(ws)
    if not changed and not NAME: return None, 0, 0
    # 새 글자 자리: 지역 빈 칸(번역 뒤 어떤 메시지도 안 쓰는 칸) → 모자라면 파일 끝
    used = set(w for e in enc.values() for w in e if not isinstance(w, tuple) and w < 0xF000)
    free = [c for c in range(i['nglyph'] - 1, LOCAL - 1, -1) if c not in used]
    code = {}; extra = []
    for ch in new:
        if free: code[ch] = free.pop(0)
        else: extra.append(ch)
    end = len(d); pad = (-(end - i['font'])) % D.G if extra else 0
    base = (end + pad - i['font']) // D.G
    for j, ch in enumerate(extra): code[ch] = base + j
    if code and max(code.values()) >= 0xF000: sys.exit('⛔ 코드 넘침')
    # 본문 다시 채우기(원래 오프셋 순서, 같은 오프셋 공유는 한 번만)
    tx, lim = i['text'], i['font']
    order = sorted(set(o for o in i['offs'] if 0 < o < (lim - tx) // 2))
    first = {o: n for n, a, ws in reversed(msgs) for o in [(a - tx) // 2]}
    body = bytearray(d[tx:tx + 2 * order[0]]); newoff = {}
    for o in order:
        newoff[o] = len(body) // 2
        for w in enc[first[o]]: body += struct.pack('>H', code[w[1]] if isinstance(w, tuple) else w)
    if tx + len(body) > lim: sys.exit('⛔ 본문 넘침 %s %X > %X' % (os.path.basename(path), tx + len(body), lim))
    body += bytes(lim - tx - len(body))
    d[tx:lim] = body
    for j, o in enumerate(i['offs']):
        if o in newoff: struct.pack_into('>H', d, i['table'] + 2 * j, newoff[o])
    for ch in new:
        if ch not in extra: d[i['font'] + D.G * code[ch]:i['font'] + D.G * (code[ch] + 1)] = kglyph.glyph(ch, STYLE)
    if extra: d += bytes(pad) + b''.join(kglyph.glyph(ch, STYLE) for ch in extra)
    return bytes(d), changed, len(new)


def build_items(M):
    """GAME.BIN 아이템 이름·설명(공통 코드: 이름 음절 0x00~0x9F · 아이템 칸 · 공통 부호) → work/build/GAME.BIN"""
    rows, imap = item_map()
    d19 = open(os.path.join(ROOT, 'work', 'disc0', 'DATA19.BIN'), 'rb').read(); i19 = D.parse(d19)
    rev = {}
    for c in range(LOCAL):
        ch = decode.fix(M[hashlib.sha1(D.glyph(d19, i19, c)).hexdigest()[:12]])
        if ch in REUSE: rev.setdefault(ch, c)
    kname = {ch: k for k, ch in enumerate(nameentry.SYL)} | imap
    g = bytearray(open(os.path.join(ROOT, 'work', 'disc0', 'GAME.BIN'), 'rb').read())
    offs = [struct.unpack_from('>H', g, ITEM_TBL + 2 * k)[0] for k in range(24)]
    body = bytearray(g[ITEM_BODY:ITEM_BODY + 2 * min(o for o in offs if o)])           # 첫 항목 앞 머리 워드 그대로
    for r in rows:
        k = int(r['번호']); s = strip_punct_space(r['KO'])
        ws = encode(s, rev, [], kname)
        assert not any(isinstance(w, tuple) for w in ws), ('아이템에 공통 칸 밖 글자', s)
        struct.pack_into('>H', g, ITEM_TBL + 2 * k, len(body) // 2)
        for w in ws: body += struct.pack('>H', w)
    if ITEM_BODY + len(body) <= ITEM_END:
        g[ITEM_BODY:ITEM_END] = body + bytes(ITEM_END - ITEM_BODY - len(body)); where = '제자리'
    else:                                                                 # 넘치면 GAME.BIN 안 빈 구간(파일 0 · 게임 중 스테이트 4장 0 · 가리키는 리터럴 없음)으로 옮기고 본문 기준 리터럴 바꿈
        o = ITEM_RELOC - 0x0600E000
        assert not any(g[o:o + len(body)]), '옮길 자리가 0 이 아님'
        assert struct.unpack_from('>I', g, ITEM_LIT - 0x0600E000)[0] == 0x0608ED60
        g[o:o + len(body)] = body; struct.pack_into('>I', g, ITEM_LIT - 0x0600E000, ITEM_RELOC); where = '옮김 %X' % ITEM_RELOC
    open(os.path.join(ROOT, 'work', 'build', 'GAME.BIN'), 'wb').write(bytes(g))
    print('GAME.BIN 아이템 %d · 본문 %d B(원래 자리 %d) %s · 아이템 음절 %d칸' % (len(rows), len(body), ITEM_END - ITEM_BODY, where, len(imap)))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    paths = [a for a in sys.argv[1:] if not a.startswith('--')] or [os.path.join(ROOT, 'work', 'text', 'poc_ko.tsv')]
    ko = load_ko(paths); M = decode.glyph_map()
    out = os.path.join(ROOT, 'work', 'build'); os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, 'DATA*.BIN')): os.remove(f)
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc0', 'DATA*.BIN'))):
        if os.path.basename(f) in SKIP: continue
        data, n, g = build_file(f, ko, M)
        if data is None: continue
        open(os.path.join(out, os.path.basename(f)), 'wb').write(data)
        print('%s 번역 메시지 %d · 새 글자 %d · %d → %d B (램 끝 %X)' % (os.path.basename(f), n, g, os.path.getsize(f), len(data), 0x200000 + len(data)))
        if 0x200000 + len(data) > 0x29FC00: sys.exit('⛔ 램 여유 넘침(0x29FC00 부터 다른 자료)')
    if NAME: build_items(M)


if __name__ == '__main__':
    main()
