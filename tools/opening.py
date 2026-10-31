# -*- coding: utf-8 -*-
r"""오프닝 동영상 AZZZ.CPK 글 카드 8장 한글화(2026-10-31)
  원본 프레임 work/movie/fr/f####.png(ffmpeg -fps_mode passthrough, 1969장 = FILM 영상 항목 차례)
  카드마다: 글자는 프레임 사이 고정·바탕(별·벽)은 움직임 → «가장 진한 프레임들의 최솟값»으로 글자 화소(M) 판정
    프레임별 진하기 α = M 화소의 (밝기 − 주변) / 최대 → 지우기(M 넓혀 cv2.inpaint) → 한글을 같은 α·같은 색으로(줄 왼쪽 시작·줄 높이 = 원문)
  → work/movie/kr/f####.png → tools/movenc.py(바뀐 키 구간만 cinepak 다시 굽기, 구간마다 원래 바이트 이하) → work/build/AZZZ.CPK
  미리보기 my files/movie/AZZZ_kr.mp4 · 문장부호 뒤 공백 없음
  python tools/opening.py [--frames-only]"""
import glob, os, re, shutil, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
FR = os.path.join(ROOT, 'work', 'movie', 'fr'); KR = os.path.join(ROOT, 'work', 'movie', 'kr')
FONT = ImageFont.truetype(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.ttf', 12)
FF = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'
Y0, Y1 = 170, 210                                                       # 글 띠(320×224)

CARDS = [   # (시작, 끝 프레임(1부터), 한글 줄) — 원문 줄 수와 같게
    (168, 268, ['행성 [ 마무나 ]가 탄생했을 때', '모든 생명은 아직 존재하지 않았다']),
    (273, 373, ['그곳에는 살벌한 세계가 펼쳐지고', '영원처럼 느껴지는 긴 시간이 흐르고 있었다']),
    (378, 440, ['어느 날,깊은 바다 밑에 한 송이 꽃이 피어난다']),
    (446, 545, ['그 꽃은 별의 사명을 받은 듯이', '잇달아 새로운 생명을 탄생시켜 갔다']),
    (551, 613, ['생명을 낳는 그 꽃을', '[ 마더 플라워 ]라고 한다']),
    (765, 848, ['이곳은 바다 밑 깊은 곳', '마더 플라워가 피는 토템의 세계']),
    (853, 945, ['아득한 옛날부터 존재하면서도', '이 세계는 전설 속에서만 전해지고 있다']),
    (951, 1060, ['지금,이 토템에', '커다란 이변이 일어나려 하고 있었다']),
]
PUNCT = ',.!?…:;~、。'


def load(i):
    return np.asarray(Image.open(os.path.join(FR, 'f%04d.png' % i)).convert('RGB'))


def lift(a):
    g = a.astype(np.float32).mean(2)
    return g - cv2.medianBlur(g.astype(np.uint8), 9).astype(np.float32), a.max(2).astype(int) - a.min(2)


def glyph_mask(a0, a1):
    """카드 구간에서 글자 화소: 진한 프레임들의 «주변보다 밝음» 최솟값"""
    lifts = [lift(load(i))[0] for i in range(a0, a1 + 1)]
    band = np.zeros(lifts[0].shape, bool); band[Y0:Y1] = True
    score = np.array([np.clip(l[band], 0, None).mean() for l in lifts])
    top = np.argsort(score)[-max(5, len(score) // 4):]
    mn = np.min([lifts[k] for k in top], 0)
    sat = np.max([lift(load(a0 + k))[1] for k in top], 0)
    m = (mn > 22) & band & (sat < 90)
    return m, lifts


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if os.path.isdir(KR): shutil.rmtree(KR)
    os.makedirs(KR)
    for a0, a1, lines in CARDS:
        lines = [re.sub('([%s]) +' % re.escape(PUNCT), r'\1', l) for l in lines]
        m, lifts = glyph_mask(a0, a1)
        rows = np.where(m.any(1))[0]
        bands = []                                                      # 원문 줄(연속 행 묶음)
        for y in rows:
            if bands and y - bands[-1][1] <= 2: bands[-1][1] = y
            else: bands.append([y, y])
        bands = [b for b in bands if b[1] - b[0] >= 6]
        assert len(bands) == len(lines), (a0, bands, lines)
        x0 = [int(np.where(m[b0:b1 + 1].any(0))[0].min()) for b0, b1 in bands]
        peak = max(float(l[m].mean()) for l in lifts)
        # 글자 색: 가장 진한 프레임의 글자 화소 평균
        k = int(np.argmax([l[m].mean() for l in lifts])); col = load(a0 + k)[m].reshape(-1, 3).mean(0)
        er = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8))
        txt = Image.new('L', (320, 224), 0); d = ImageDraw.Draw(txt)
        for (b0, b1), x, l in zip(bands, x0, lines):
            d.text((x, b0 - 1), l, font=FONT, fill=255)
        T = np.asarray(txt).astype(np.float32) / 255
        if T[:, 318:].any(): sys.exit('⛔ 화면 폭 넘침: %s' % lines)
        for i in range(a0, a1 + 1):
            a = load(i); al = float(np.clip(lifts[i - a0][m].mean() / peak, 0, 1))
            if al < 0.03: continue
            b = cv2.inpaint(a, er, 3, cv2.INPAINT_TELEA).astype(np.float32)
            w = (T * al)[..., None]
            out = b * (1 - w) + col[None, None, :] * w
            Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).save(os.path.join(KR, 'f%04d.png' % i))
        print('카드 %4d~%4d 줄 %d · 글자 화소 %d · 색 %s · %s' % (a0, a1, len(lines), m.sum(), col.astype(int).tolist(), ' / '.join(lines)))
    # 미리보기 mp4(원본 프레임 + 바뀐 프레임)
    tmp = os.path.join(ROOT, 'work', 'movie', '_pv'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    for p in sorted(glob.glob(os.path.join(FR, 'f*.png'))):
        n = os.path.basename(p); q = os.path.join(KR, n)
        shutil.copyfile(q if os.path.exists(q) else p, os.path.join(tmp, n))
    out = os.path.join(ROOT, 'my files', 'movie', 'AZZZ_kr.mp4')
    subprocess.run([FF, '-v', 'error', '-y', '-framerate', '15', '-i', os.path.join(tmp, 'f%04d.png'), '-i', os.path.join(ROOT, 'work', 'disc0', 'AZZZ.CPK'),
                    '-map', '0:v', '-map', '1:a', '-af', 'aresample=44100', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', out], check=True)
    shutil.rmtree(tmp)
    print('미리보기 →', out)
    if '--frames-only' in sys.argv: return
    import movenc
    movenc.TMP = os.path.join(ROOT, 'work', 'movie', '_gop')
    src = os.path.join(ROOT, 'work', 'disc0', 'AZZZ.CPK')
    movenc.reencode(src, FR, KR, os.path.join(ROOT, 'work', 'build', 'AZZZ.CPK'), os.path.getsize(src))


if __name__ == '__main__':
    main()
