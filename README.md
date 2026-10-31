# 링클 리버 스토리 (세가 새턴 일본판) 한글 패치

> **내려받기:** [릴리즈 페이지](https://github.com/hospi0/linkle-kr-patch/releases/latest) — 최신 v0.9. 적용 방법·원본 MD5 는 패치 묶음의 readme 에 있습니다.
>
> 이 저장소에는 도구·번역 텍스트·작업 문서만 있습니다(ROM·빌드 결과물 없음).

## 한글화 범위
- 대사 전체(881종), 아이템 이름·설명
- 메뉴·저장·설정·장 제목 그림, 월드맵 지명·저장 안내
- 이름 입력판(한글 음절 160개, 이름 미리보기 포함)
- 오프닝 동영상 글 카드 8장

## 구조 메모
- 대사 = `DATA##.BIN`(WorkRAML 0x200000) u16 코드, 글꼴 14×14 4bpp가 파일 안에 함께 — 공통 칸 0x000~0x106 + 파일별 칸
- 메뉴 그림 = `IKECG\*.XGD`지만 게임은 `XCGALL.BIN`·`TICGALL.BIN` 안 사본을 읽음(`tools/gfx_pack.py`)
- 이름 입력표 = AUTOEXEC·TITLE·GAME2 세 곳, 월드맵 지명 = `AMAP.BIN` 8bpp 그림 사슬
- 자세한 조사·빌드 기록: `docs/00_초기조사.md`

## 빌드
`tools/merge_ko.py` → `tools/build.py work/text/ko.tsv --name` → `tools/gfx_menu.py` → `tools/nameentry.py` → `tools/gfx_pack.py` → `tools/gfx_amap.py` → `tools/opening.py` → `tools/discbuild.py --write` → `tools/make_dist.py`
