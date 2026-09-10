# ML Radar

큐레이션된 소스만 모아 하루 한 번 보는 개인용 정적 페이지.
순위·점수·요약·검색 없음. 가져와서 배치만 한다.

## 구조

```
.github/workflows/update.yml   매일 06:20 UTC 크론 → fetch.py → data/ 커밋
scripts/sources.py             소스 목록. 여기만 고치면 된다.
scripts/fetch.py               수집기. 표준 라이브러리만 사용 (pip install 없음).
data/status.json               소스별 성공/실패·마지막 성공 시각
data/papers.json               HF Daily Papers 누적본
data/feeds/<slug>.json         RSS 소스별 누적본
index.html                     페이지. 빌드 스텝 없음.
```

## 3년 뒤의 당신에게

**소스 추가/삭제** — `scripts/sources.py`의 `FEEDS` 리스트에서 한 줄 추가하거나 지운다.
그 외 어떤 파일도 건드릴 필요 없다. 화면에서 잠깐 끄고 싶을 뿐이라면 코드 대신
페이지의 `소스` 버튼을 쓴다 (localStorage에만 저장되므로 브라우저별로 따로 논다).

**한 소스가 죽었을 때** — 아무것도 안 해도 된다. 나머지는 그대로 나오고, 그 소스는
이전 데이터를 유지한 채 `N일째 갱신 없음` 배지가 붙는다. 며칠 지켜보다 영영 안 살아나면
`sources.py`에서 지운다.

**전부 안 나올 때** — Actions 로그를 본다. 모든 소스가 실패했을 때만 워크플로가 빨간불이 된다.
하나만 실패하면 초록불이며, 이는 의도된 동작이다.

**피드가 짧아도 괜찮은 이유** — Apple ML은 10건(약 13일치)만 싣는다. 매일 받아 누적하므로
30일 창이 채워진다. 회전율이 하루치를 넘는 피드만 위험한데, 실측상 가장 빠른 게
NVIDIA Developer 2.9건/일이라 여유가 있다.

## 보존 기간

JSON에 논문 21일 / 글 60일을 보관하고, 화면에는 논문 7일 / 글 30일을 보여준다.
바꾸려면 `sources.py`의 `KEEP_DAYS_*`와 `index.html` 상단의 `PAPER_DAYS`/`ARTICLE_DAYS`.

## 소스 (2026-09-10 전부 실측 확인)

뉴스레터 3 · 랩/연구 10 · 엔지니어링 5 · HF Daily Papers.

RSS가 없어 넣지 못한 곳: The Batch, Anthropic, Meta AI, Samsung Research, NAVER LABS,
LG AI Research, AI2, Mistral, Cohere, IBM Research.
응답은 하지만 사실상 멈춘 곳: Meta Research(2023-05), Stanford AI Lab(2022-05), Qwen(2025-09).

## GitHub Pages

Settings → Pages → Source: `main` 브랜치 루트.
`data/`는 워크플로가 커밋하므로 별도 빌드가 없다.
