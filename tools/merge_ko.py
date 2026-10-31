# -*- coding: utf-8 -*-
r"""하스피 번역 병합(2026-10-31) — my files/링클번역/ll_*.tsv → work/text/ko.tsv(대사: JP·KO) · work/text/ko_item.tsv
  1) 이름 통일(하스피 2026-10-31: オサ = 장로) — 오사·족장 → 장로(조사 받침 맞춤) · 프치무타 → 푸치무타 · 츠루모구 → 츠루모그
  2) 손 고침 FIX(번호 → KO): {名} 빠진 5줄(호격으로 되살림) · 말투(주인공 00333·00796·00808, 플라워 00816 → 원문대로 반말)
  3) 메시지 끝 꼬리(마지막 글 줄 뒤 ／·　)를 원문과 똑같이
  4) 토큰({名}·{FFxx}·／) 차례 검사 — 다르면 중단
  5) 줄 폭: 얼굴 있는 창({FFxx} 로 시작) 16칸 · 없는 창 20칸(원문 최대 실측), {名} = 4칸, 부호 뒤 공백은 지운 뒤 셈
     넘치면 같은 줄 수 안에서 낱말 단위로 다시 나눔(첫 줄 «이름：», 둘째 줄부터 «　» 들여쓰기 유지) → 그래도 넘치면 work/text/overflow.tsv(줄이기 후보)
  python tools/merge_ko.py"""
import csv, glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'my files', '링클번역')
TOK = re.compile(r'／|\{名\}|\{FF[0-9A-F]{2}\}')
PUNCT = ',.!?…~:;'
FIX = {
    '00176': '{FF10}로빈：하지만 장로님은 역시 대단해.／　{名}, 네 소질을 제대로／　꿰뚫어 보고 키워 냈으니까.／／',
    '00177': '{FF10}　지금은 동물들 중에서／　장로님 다음으로 {名},／　네가 강하다고 생각해.／／／',
    '00181': '{FF10}로빈：자자, {名}.／　분명 장로님은 엄하셔.／　하지만 상냥함도 강함도 있으셔.／／',
    '00187': '{FF14}로빈：알아, 알아.／　그게 {名},／　네 좋은 점이기도 하지만.／／／',
    '00217': '{FF30}장로：이 녀석!／　이건 {名}, 너를 위해／　마음을 독하게 먹고 하는 말이다.／／',
    '00333': '{FF13}{名}：모두를 잠들게 한 건／　생명을 빼앗기 위해서였구나.／　어째서 그런 짓을 하는 거야？／／',
    '00796': '{FF06}{名}：멸망시켰다고？！／　웅가로는 죽지 않잖아.／　멸망했을 리가 없어.／／',
    '00808': '{FF07}{名}：웅가로의 정체는／　잘 알겠어.／　그 녀석은 어떤 생물이었어？／／',
    '00816': '플라워：장로님들이라면 안 계셔.／　장로님도 츠루모그도 기운을 차려서／　버드를 타고 론도의 숲으로 갔어.／／／',
}
JOSA = [('이', '가'), ('은', '는'), ('을', '를'), ('과', '와'), ('으로', '로'), ('이랑', '랑'), ('이나', '나'), ('이야', '야'), ('이다', '다'), ('이여', '여'), ('아', '야')]


def unify(s):
    for a in ('족장', ):                                                  # 받침 있음 → 장로(받침 없음): 뒤 조사 바꿈
        for j1, j2 in JOSA:
            s = re.sub(a + j1 + r'(?![가-힣])', '장로' + j2, s)
        s = s.replace(a, '장로')
    s = re.sub(r'(?<![가-힣])오사', '장로', s)                           # 오사·장로 둘 다 받침 없음 → 조사 그대로
    return s.replace('프치무타', '푸치무타').replace('츠루모구', '츠루모그')


def tail_split(s):
    m = re.search(r'(／[／　]*)$', s)
    return (s[:m.start()], m.group(1)) if m else (s, '')


def cells(x):
    x = re.sub(r'\{FF[0-9A-F]{2}\}', '', x).replace('{名}', 'ＸＸＸＸ')
    x = re.sub('([%s]) +' % re.escape(PUNCT), r'\1', x)
    return len(x)


DEP = ('수', '것', '거', '줄', '때', '데', '뿐', '만큼', '듯', '적', '척', '채', '김', '바', '터')


def rewrap(content, B, n):
    """content(꼬리 뺀 본문) → n 줄 이하, 각 줄 B 칸 이하로 다시 나눔(줄 길이 고르게, 의존명사 앞 끊기 벌점). 못 하면 None"""
    lines = content.split('／')
    m = re.match(r'(\{FF[0-9A-F]{2}\})?([^：　]{1,12}：)?', lines[0])
    head = (m.group(1) or '') + (m.group(2) or '')
    first_indent = '　' if lines[0][len(head):].startswith('　') else ''
    text = ' '.join(l.strip('　 ') if i else l[len(head):].strip('　 ') for i, l in enumerate(lines))
    text = re.sub('([%s]) +' % re.escape(PUNCT), r'\1', text)
    parts = []
    for w in re.findall(r'[^ ]+ ?', text):
        parts += re.findall(r'[^%s]*[%s]+|[^%s]+' % ((re.escape(PUNCT),) * 3), w)
    N = len(parts); INF = 10 ** 9
    def line(i, j, first): return ((head + first_indent) if first else '　') + ''.join(parts[i:j]).rstrip()
    best = {}
    def go(i, k):                                                          # parts[i:] 를 k 줄 이하로
        if i == N: return (0, [])
        if k == 0: return (INF, None)
        if (i, k) in best: return best[(i, k)]
        res = (INF, None)
        for j in range(i + 1, N + 1):
            L = line(i, j, i == 0)
            if cells(L) > B: break
            cost = (B - cells(L)) ** 2 if j < N else 0
            if j < N and parts[j].strip().rstrip(PUNCT) in DEP: cost += 400   # 의존명사 앞에서 끊기 싫음
            sub = go(j, k - 1)
            if sub[1] is None: continue
            if cost + sub[0] < res[0]: res = (cost + sub[0], [L] + sub[1])
        best[(i, k)] = res; return res
    c, ls = go(0, n)
    return '／'.join(ls) if ls else None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = []
    for f in sorted(glob.glob(os.path.join(SRC, 'll_0*.tsv'))):
        for r in csv.DictReader(open(f, encoding='utf-8-sig'), delimiter='\t', quoting=csv.QUOTE_NONE): rows.append(r)
    short = {r['번호']: r['KO'] for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'ko_short.tsv'), encoding='utf-8'), delimiter='	', quoting=csv.QUOTE_NONE)}
    bota = {r['번호']: r['KO'] for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'text', 'ko_bota.tsv'), encoding='utf-8'), delimiter='	', quoting=csv.QUOTE_NONE)}
    out = []; over = []; rew = 0; changed = 0; err = []; nshort = 0
    for r in rows:
        ko0 = r['KO']; ko = FIX.get(r['번호'], ko0); ko = unify(ko)
        jc, jt = tail_split(r['JP']); kc, kt = tail_split(ko); ko = kc + jt     # 꼬리 = 원문
        if TOK.findall(ko) != TOK.findall(r['JP']): err.append((r['번호'], TOK.findall(r['JP']), TOK.findall(ko))); continue
        B = 16 if re.match(r'\{FF[0-9A-F]{2}\}', r['JP']) else 20
        n = max(len(jc.split('／')), len(kc.split('／')))
        if r['번호'] in bota:                                               # 하스피 2026-10-31: ボタ = 푸치무타(·아기 원숭이) 1인칭 → 나/우리(work/text/ko_bota.tsv)
            kc = bota[r['번호']]; ko = kc + jt
        elif r['번호'] in short:                                              # 줄여도 안 들어가던 메시지 — 줄인 안(ko_short.tsv, 하스피 확인용 비교 파일 my files/링클번역/줄인_대사_비교.txt)
            kc = short[r['번호']]; ko = kc + jt; nshort += 1
        if any(cells(l) > B for l in kc.split('／')):
            w = rewrap(kc, B, len(jc.split('／')))
            if w and TOK.findall(w + jt) == TOK.findall(r['JP']): ko = w + jt; rew += 1
            else: over.append((r['번호'], B, kc))
        if ko != ko0: changed += 1
        out.append((r['번호'], r['위치'], r['JP'], ko))
    if err: raise SystemExit('⛔ 토큰 다름 %d %s' % (len(err), err[:5]))
    with open(os.path.join(ROOT, 'work', 'text', 'ko.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\t위치\tJP\tKO\n')
        for x in out: o.write('\t'.join(x) + '\n')
    with open(os.path.join(ROOT, 'work', 'text', 'overflow.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\t폭\tKO(줄 나눔 그대로)\n')
        for x in over: o.write('%s\t%d\t%s\n' % x)
    it = list(csv.DictReader(open(os.path.join(SRC, 'll_item.tsv'), encoding='utf-8-sig'), delimiter='\t', quoting=csv.QUOTE_NONE))
    with open(os.path.join(ROOT, 'work', 'text', 'ko_item.tsv'), 'w', encoding='utf-8', newline='\n') as o:
        o.write('번호\t위치\tJP\tKO\n')
        for r in it: o.write('\t'.join((r['번호'], r['위치'], r['JP'], unify(r['KO']))) + '\n')
    print('대사 %d · 바뀐 %d · 줄인 안 %d · 줄 다시 나눔 %d · 그래도 넘침 %d → work/text/ko.tsv · overflow.tsv' % (len(out), changed, nshort, rew, len(over)))


if __name__ == '__main__':
    main()
