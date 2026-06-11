# Submission Dashboard — 학회/저널 투고 후보 대시보드

HCI · Mobile UX · AI UX · 금융/디지털 서비스 UX 중심의 학회/저널/트랙 투고 후보를
**공개 정보 + 출처 URL 기반**으로 관리하는 Streamlit 대시보드.

- 모든 deadline/fee/metric은 출처 URL·확인일·공식 여부와 함께 기록 (URL 없으면 `needs_verification`)
- 프로젝트는 익명 코드(P01…)와 broad field만 사용 — 내부 연구 내용 입력 금지
- CSV만 수정해서 유지보수, git push로 자동 재배포

## 빠른 시작 (로컬)

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
python scripts/validate_data.py             # 데이터 검증 (urgent/normal/backlog 분류)
python scripts/validate_data.py --weekly    # 이번 주 작업 큐만
python scripts/export_calendar.py           # public/submission_deadlines.ics (구독용 고정 경로)
python scripts/generate_weekly_digest.py    # public/weekly_digest.md/html
python scripts/apply_updates.py --list      # AI 제안(proposed_updates) 검토/병합
```

**자동화**: `.github/workflows/weekly-digest.yml` — 매주 월요일 digest+ICS 재생성·커밋,
GitHub Issue로 발송 (메일/Slack은 워크플로 주석 단계 활성화). 캘린더는 import가 아니라
공개 ICS URL **구독** 방식 — 설정은 `docs/update_guide.md` §4.

## 웹 배포 (Streamlit Community Cloud)

1. GitHub **private** 저장소로 push
2. share.streamlit.io → New app → Main file path: `dashboard/app.py`
3. Sharing 설정에서 viewer 제한 (자세한 절차: `docs/update_guide.md` §6, 보안: `docs/security_policy.md` §6)

## 구조

```
data/        projects, venues, opportunities, project_opportunity_fit,
             fees, metrics, sources, watchlist (CSV — 단일 진실 원천)
dashboard/   app.py — 첫 탭은 "📥 Inbox"(이번 주 할 일만), 이어서 캘린더(구독 링크)·
             비교표·Fit·URL검증·비용·지표·Watchlist·AI 제안 검토
scripts/     validate_data.py, export_calendar.py, generate_weekly_digest.py, apply_updates.py
public/      submission_deadlines.ics(구독용), weekly_digest.md/html — Actions가 매주 갱신
data/proposed_updates/   AI 수정 초안 (탭에서 accept/skip 결정 → apply_updates.py로 병합)
config/      weights.json (priority score 가중치)
docs/        data_dictionary, source_policy, security_policy, update_guide
```

## 데이터 현황 (2026-06-10 기준 seed)

- venues 51개 (core / secondary / project_specific_only 우선순위 구분)
- opportunities 40건 — 2026-06-10 현재 open/rolling/upcoming 위주, 전부 공식 URL 첨부
- 미확인 값은 비워두고 `needs_verification` 처리 (대시보드 "URL 검증" 탭에서 추적)
- 임박 마감 예시: OzCHI long papers 6/12 · HICSS 6/15 · BritCHI workshops 6/18 ·
  ICMI LBR 6/21 · ASSETS posters & CSCW Industry 7/1 · UIST posters/demos 7/10 ·
  RecSys demos 7/15 · CHI 2027 papers 9/10 — **제출 전 반드시 공식 페이지에서 재확인**

## 문서

| 문서 | 내용 |
|---|---|
| `docs/data_dictionary.md` | 모든 CSV 컬럼 정의, fit score 기준 |
| `docs/source_policy.md` | 출처 URL 규칙, 지표 확인처 |
| `docs/security_policy.md` | AI 도구 입력 금지 정보, 공유 전 체크리스트 |
| `docs/update_guide.md` | 주간/월간 유지보수 루틴, 배포 절차 |
