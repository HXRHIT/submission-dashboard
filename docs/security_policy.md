# Security Policy — 보안 정책

이 저장소와 대시보드는 **공개 정보 + 익명 프로젝트 코드만** 다룬다.
git 저장소에 한 번 커밋된 내용은 히스토리에 영구히 남고, 웹에 배포하면 누구나 볼 수 있다는 전제로 운영한다.

## 1. Claude(또는 외부 AI 도구)에 입력하면 안 되는 정보

- 실제 프로젝트명, 회사명/고객사명, 내부 과제명
- 미공개 연구 질문, 가설, 실험 설계 상세
- 실험 결과, 데이터 파일, 미공개 데이터 요약
- 논문 초안 전문, 초록 전문, 내부 보고서
- 내부 전략 판단, 경영 관련 정보
- 사내 링크 (Google Drive, Notion, Slack, 사내 위키, 인트라넷 URL 등)
- 개인정보 (참가자 정보, 사번, 연락처 등)

## 2. 안전하게 입력 가능한 정보

- 공개 CFP, 공개 마감일, 공개 등록비, 공개 지표 (모두 공개 URL 기반)
- 익명 프로젝트 코드 (P01, P02 …)와 broad category (HCI, UX Research 등)
- method type (survey, experiment, field study 등 — 일반적 방법론 명칭)
- 진행 단계 (idea / collecting / analyzed / writing / submitted)
- 공개해도 무방한 수준의 next action ("check CFP", "draft abstract" 등)

## 3. 프로젝트 코드명 사용 원칙

- `projects.csv`에는 `project_id`(P01…), broad_field, method_type, 진행 상태만 둔다.
- `project_alias`도 위험하다고 판단되면 비우고 P01/P02만 사용한다.
- 금지 컬럼: 실제 프로젝트명, 고객사명, 내부 과제명, 미공개 연구 질문,
  구체적 실험 결과, 미공개 데이터 요약, 내부 전략, 논문 초록 전문, 사내 문서 링크.

## 4. fit_rationale 작성 원칙

- `fit_rationale_public_safe`에는 **broad field와 method 기준**으로만 쓴다.
  - 좋은 예: "Mobile HCI venue; survey/interview-based applied UX fits LBW track."
  - 나쁜 예: 내부 서비스명, 실험 조건, 결과 수치, 고객사 맥락이 들어간 문장.
- `notes_public_safe`, `next_action_public_safe`도 동일 원칙.

## 5. 공개 URL 기반 정보만 수집하는 원칙

- 모든 deadline/fee/metric은 공개 URL과 함께 기록한다 (`docs/source_policy.md`).
- URL이 없는 값은 입력하지 않거나 `needs_verification`으로 표시한다.
- 회사 내부 링크는 어떤 컬럼에도 넣지 않는다.

## 6. 웹 배포 시 추가 주의 (이 저장소는 웹 배포용)

- **GitHub 저장소는 private**로 유지한다. public으로 전환할 일이 있으면 아래 체크리스트를 먼저 수행.
- Streamlit Community Cloud 배포 시 앱 URL을 아는 사람은 데이터 전체를 볼 수 있다.
  Streamlit Cloud의 viewer 제한(Share 설정에서 이메일 허용 목록) 또는 사내 인증 프록시를 사용한다.
- 커밋 전 `git diff`로 민감 정보 유입 여부를 확인한다. 한 번 push된 민감 정보는
  히스토리 정리(rebase/filter-repo) 전까지 계속 노출된다.
- 대시보드 캡처/공유 시에도 fit 테이블의 notes에 민감 표현이 없는지 확인.

## 7. 대시보드/저장소 공유 전 점검 체크리스트

- [ ] projects.csv에 익명 코드와 broad field만 있는가?
- [ ] fit_rationale/notes에 내부 연구 내용·고객사명·수치가 없는가?
- [ ] 모든 URL이 공개 URL인가? (사내 도메인, drive.google.com 개인 문서, notion.so 등 없음)
- [ ] owner_initials 외의 개인 식별 정보가 없는가?
- [ ] git 히스토리에 과거 민감 커밋이 없는가?
- [ ] 저장소가 private인가? / 앱 viewer 제한이 걸려 있는가?
