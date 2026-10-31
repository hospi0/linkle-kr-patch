# -*- coding: utf-8 -*-
r"""링클 리버 스토리 배포 묶음 — dist/LinkleLiverStory_KR_<VER>/ : 트랙 01 xdelta + xdelta.exe + readme.txt(CP949) + 한글패치_적용.bat(CP949)
  (메탈슬러그 tools/make_dist.py 를 옮김, 2026-10-31) 바뀌는 트랙: 트랙 1 만, 크기 그대로(트랙 2·3 = 오디오, cue 그대로)
  검증: 원본 트랙 01 → xdelta 적용 → md5 = 빌드 트랙 01 md5
  python tools/make_dist.py   (먼저 python tools/build.py · tools/discbuild.py --write)"""
import hashlib, os, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

VER = 'v0.9'
XDELTA = r'C:\claude\utils\xdelta.exe'
ROM = 'Linkle Liver Story (Japan)'
SRC = os.path.join(r'C:\claude\roms\ss', ROM)
OUT = os.path.join(ROOT, 'dist', 'build', ROM)
NAME = 'LinkleLiverStory_KR_' + VER
TITLE = '링클 리버 스토리 (Linkle Liver Story, 세가 새턴 일본판) 한글 패치 ' + VER


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


README = """{title}
{line}

3개의 트랙으로 이루어진 {rom} 의
트랙 1번에 패치하시면 됩니다.

원본md5 : {o}
패치md5 : {d}

입니다.


[ 적용 방법 ]

  1) 원본 트랙 1 파일을 이 폴더에 복사
       "{bin}"
  2) 한글패치_적용.bat 실행 → 이름 끝에 [KR] 이 붙은 파일이 만들어집니다
  3) 만든 파일 이름을 원본 트랙 1 이름으로 바꿔 넣고, 트랙 2·3(오디오)과 cue 는 원본 그대로 쓰세요

  직접 적용:
    xdelta.exe -d -s "원본 트랙 1" "{patch}" "결과 파일"
  (Delta Patcher 같은 xdelta3 GUI 도구로 적용해도 됩니다. 원본이 다르면 xdelta 가 적용을 거부합니다.)


[ 바뀌는 것 ]

  - 대사 전체(881종) · 아이템 이름·설명 · 장 제목
  - 메뉴·저장·설정 화면 그림, 월드맵 지명·저장 안내
  - 이름 입력판(한글 음절 160개, 이름 미리보기 포함)
  - 오프닝 동영상 글


[ 알려진 점 ]

  - 타이틀 로고는 원본 그대로입니다.
  - 이름 입력판은 이름에 잘 쓰는 음절 160개로 이루어져 있습니다(자모 조합 입력은 없음).
  - 패치 전 세이브스테이트로는 실행하지 마세요. 처음부터 부팅해 주세요.
"""

BAT = r"""@echo off
chcp 949 >nul
set "XD=%~dp0xdelta.exe"
if not exist "%~dp0{bin}" (
  echo   [오류] 원본 트랙 1 파일을 이 폴더에 넣어 주세요 - readme 참고.
  pause & exit /b 1
)
"%XD%" -d -f -s "%~dp0{bin}" "%~dp0{patch}" "%~dp0{kbin}"
if errorlevel 1 (
  echo   [오류] 패치 실패 - 원본이 다를 수 있습니다 - readme 의 원본md5 확인.
  pause & exit /b 1
)
echo   완료: "{kbin}"
pause
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = os.path.join(ROOT, 'dist', NAME)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    b = '%s (Track 1).bin' % ROM
    src, out = os.path.join(SRC, b), os.path.join(OUT, b)
    patch = NAME + '_Track1.xdelta'; pp = os.path.join(d, patch)
    subprocess.run([XDELTA, '-e', '-9', '-B', '536870912', '-f', '-s', src, out, pp], check=True)
    chk = os.path.join(d, '_check.bin')
    subprocess.run([XDELTA, '-d', '-f', '-s', src, pp, chk], check=True)
    o, want, got = md5(src), md5(out), md5(chk)
    os.remove(chk)
    assert got == want, ('패치 적용 결과가 빌드와 다름', got, want)
    print('트랙 1 원본md5 %s → 패치md5 %s · %s %d B' % (o, want, patch, os.path.getsize(pp)))
    shutil.copy2(XDELTA, os.path.join(d, 'xdelta.exe'))
    kbin = '%s (Track 1) [KR].bin' % ROM
    readme = README.format(title=TITLE, line='=' * 60, rom=ROM, o=o, d=want, bin=b, patch=patch)
    open(os.path.join(d, 'readme.txt'), 'wb').write(readme.replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(d, '한글패치_적용.bat'), 'wb').write(BAT.format(bin=b, patch=patch, kbin=kbin).replace('\n', '\r\n').encode('cp949'))
    z = os.path.join(ROOT, 'dist', NAME + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(d)):
            zf.write(os.path.join(d, f), NAME + '/' + f)
    print('✅', d)
    for f in sorted(os.listdir(d)):
        print('  %-56s %12d' % (f, os.path.getsize(os.path.join(d, f))))
    print('  zip %s %d B · md5 %s' % (os.path.basename(z), os.path.getsize(z), md5(z)))


if __name__ == '__main__':
    main()
