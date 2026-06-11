# Data Dictionary

모든 CSV는 UTF-8(BOM), 콤마 구분, 날짜는 YYYY-MM-DD. 빈 값 = 미확인(확정값 아님).

## data/venues.csv — 학회/저널 고정 정보

| 컬럼 | 설명 / 허용값 |
|---|---|
| venue_id | V### (PK) |
| venue_name, acronym | 공식 명칭/약칭 |
| venue_type | conference / journal / journal-style proceedings / workshop / symposium |
| field | HCI, CSCW, Human-AI Interaction, UX Research, Accessibility, Design Research, Multimodal Interaction, Ubiquitous Computing, VR/AR/XR, Information Systems, FinTech 등 |
| publisher | ACM / IEEE / Springer / Elsevier / Taylor & Francis / SAGE / other |
| society | ACM SIGCHI, AIS, BCS 등 |
| official_homepage_url / official_cfp_url / proceedings_url / template_url / submission_system_url | 공개 URL |
| typical_submission_types / typical_page_limit | 통상 제출 형태/분량 |
| priority_scope | **core / secondary / project_specific_only** — 사용자 연구 축(모바일/AI UX/금융 UX) 기준 우선순위. project_specific_only는 삭제하지 않고 낮은 우선순위로 유지 |
| primary_relevance / secondary_relevance | 주/부 관련 분야 (`;` 구분) |
| domain_fit_notes | 도메인 fit 메모 (공개 안전 표현만) |
| source_id | sources.csv FK |
| last_checked_at / verification_status | 확인일 / verified_official·secondary_only·needs_verification |

## data/opportunities.csv — 연도·트랙별 제출 기회

| 컬럼 | 설명 |
|---|---|
| opportunity_id | OPP### (PK) |
| venue_id | venues FK |
| year / track_name | 대상 연도, 트랙명 |
| submission_type | full paper / short paper / poster / demo / late-breaking work / workshop paper / journal article / special issue / industry talk… |
| abstract_deadline / paper_deadline | 날짜만. **deadline_source_url 없으면 비워둔다** |
| deadline_time / deadline_timezone | 시간(있을 때만) / AoE·UTC·local (HST) 등 |
| notification_date / camera_ready_deadline / conference_start / conference_end | 날짜 |
| location_city / location_country / online_hybrid | 장소, in-person/hybrid/online |
| page_limit / word_limit / format | 분량·포맷 |
| official_cfp_url / submission_system_url / template_url | 공개 URL |
| deadline_source_url / location_source_url / page_limit_source_url | 각 값을 본 정확한 URL |
| status | open / upcoming / closed / rolling / unknown |
| source_id / last_checked_at / verification_status / notes | 메타 |

## data/fees.csv — 등록비/APC

fee_id(PK), opportunity_id 또는 venue_id(FK), fee_type(registration/APC/membership/page charge/extra page),
category(student/regular/member/early/late/virtual/in-person…), amount, currency, fee_deadline,
fee_source_url(**amount 있으면 필수**), source_id, last_checked_at, verification_status, notes.

## data/metrics.csv — 수준 지표

metric_id(PK), venue_id(FK), metric_year(**값 있으면 필수**), sci/scie/ssci/ahci/scopus_status,
impact_factor, cite_score, core_ranking, h5_index, acceptance_rate,
metric_source_url(**값 있으면 필수**), metric_source_type(JCR/Scopus/CORE/Google Scholar/official venue report/publisher page/secondary source),
source_id, last_checked_at, verification_status, notes.

## data/sources.csv — 출처 대장

source_id(PK), title, url, source_type(official homepage/official CFP/publisher page/submission system/fee page/proceedings page/JCR/Scopus/CORE/Google Scholar/secondary source),
accessed_date, reliability(high/medium/low), archived_url, notes.

## data/watchlist.csv — CFP 미공개 venue 추적

watch_id(PK), venue_id(FK), expected_cycle, expected_submission_month(YYYY-MM),
last_year_cfp_url, current_year_homepage_url,
current_status(CFP not released/CFP released/deadline announced/closed/unknown),
last_checked_at, next_check_date, notes.

## data/projects.csv — 익명 프로젝트 (민감정보 금지)

project_id(P##, PK), project_alias(위험하면 비움), broad_field, method_type,
data_status(idea/collecting/analyzed/writing/submitted), writing_status, target_year,
owner_initials, notes_public_safe. **금지 컬럼은 docs/security_policy.md 참조.**

## data/project_opportunity_fit.csv — 프로젝트×기회 fit

project_id+opportunity_id(복합키), fit_score(1~5), fit_rationale_public_safe(broad field/method 기준만),
expected_difficulty(low/medium/high), submission_probability(1~5), strategic_value(1~5),
publication_value(1~5), effort_required(1~5), cost_burden(1~5),
priority(앱이 자동 계산 — CSV에선 비워둠), risk_tags(`;` 구분: deadline_tight, needs_more_analysis,
framing_needed, formatting_needed, travel_cost…), next_action_public_safe, internal_deadline,
owner_initials, status(candidate/preparing/submitted/accepted/rejected/dropped), notes_public_safe.

### Fit score 기준 (모바일/AI UX/금융 UX 축)

- **5**: 모바일 앱 인터랙션·AI UX·금융 UX·디지털 서비스 UX 중 하나와 직접 일치하고, HCI/UX 방법론을 명확히 수용하며, 유사 주제 게재 이력이 있고, 과도한 포장 없이 audience가 이해 가능
- **4**: 주제는 맞지만 framing 조정 필요 (예: 금융 UX → general HCI/human-AI/IS/service design 재구성)
- **3**: 직접 분야는 아니나 adjacent field로 제출 가능 (예: 금융 UX → IS/marketing/service venue)
- **2**: 키워드 일부만 일치, 핵심 커뮤니티와 거리 있음 (예: 모바일 연구 → pure AI/ML, XR venue)
- **1**: 현재 분야와 거의 무관 — project_specific_only로 보류

## config/weights.json — Priority Score 가중치

`priority = fit×0.30 + strategic×0.25 + probability×0.20 + publication×0.15 − effort×0.05 − cost×0.05`
(음수 가중치는 JSON에 -0.05로 기재. 수정하면 앱에 즉시 반영.)
