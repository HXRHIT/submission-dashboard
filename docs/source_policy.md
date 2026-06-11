# Source Policy — 출처 정책

핵심 원칙: **값보다 "값 + 출처 URL + 확인일 + 공식/비공식 여부"가 한 세트다.**
마감일·등록비·IF·acceptance rate는 자주 틀리고 자주 바뀌므로, URL 없는 값은 신뢰하지 않는다.

## 1. 출처 등급

| reliability | 기준 | 예 |
|---|---|---|
| high | 공식 학회 사이트, 퍼블리셔 페이지, 공식 제출 시스템 | chi2027.acm.org, link.springer.com, sciencedirect.com |
| medium | 공식이지만 간접 확인(검색 스니펫 등), 학회 SNS | 직접 fetch가 차단된 dl.acm.org 페이지 |
| low | 2차 출처 | WikiCFP, 블로그, 위키, 뉴스레터 |

- `verification_status`:
  - `verified_official` — 공식 페이지에서 값과 URL을 직접 확인
  - `secondary_only` — 2차 출처에서만 확인 (참고용; 공식 확인 전 확정값 금지)
  - `needs_verification` — 미확인. 값은 비워 둠

## 2. 필수 규칙

1. deadline 값이 있으면 `deadline_source_url`(또는 `official_cfp_url`)이 반드시 있어야 한다.
   없으면 deadline을 비우고 notes에 `needs_verification`을 적는다.
2. fee `amount`가 있으면 `fee_source_url`이 반드시 있어야 한다.
3. metric 값(IF/CiteScore/CORE/h5/acceptance rate)이 있으면 `metric_source_url`과
   `metric_year`(기준연도)가 반드시 있어야 한다.
   - 기준연도 라벨을 확인하지 못한 값은 **입력하지 않고** notes에 관찰값만 적는다 (seed data 참고).
4. 비공식 출처(블로그/위키)의 acceptance rate는 `metric_source_type=secondary source`로 표시한다.
5. 날짜는 YYYY-MM-DD로 통일하고, 시간은 `deadline_time`, 타임존은 `deadline_timezone`
   (AoE / UTC / local (HST) 등)에 분리 기록한다.
6. 모든 출처는 `sources.csv`에 등록하고 행마다 `source_id`로 연결한다.
7. 확인할 때마다 `last_checked_at`을 갱신한다. 60일 경과 시 대시보드와 validator가 경고한다.

## 3. 지표 확인처 (공식)

- Impact Factor: JCR (Clarivate) 또는 퍼블리셔 저널 홈페이지의 연도 라벨이 있는 표기
- CiteScore/Scopus 등재: Scopus (scopus.com) 또는 퍼블리셔 insights 페이지
- CORE ranking: portal.core.edu.au
- h5-index: Google Scholar Metrics
- acceptance rate: 공식 proceedings frontmatter, 학회 공식 발표 (블로그 수치는 secondary)

## 4. 아카이브

- 중요한 CFP는 `archived_url`에 web.archive.org 스냅샷을 남겨두면
  마감 연장/변경 분쟁 시 근거가 된다 (선택).
