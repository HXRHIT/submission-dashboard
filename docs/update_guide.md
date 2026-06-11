# Update Guide — 유지보수 가이드

이 저장소는 git으로 관리하고 Streamlit Community Cloud로 배포한다.
**CSV만 수정하면 대시보드가 자동 갱신**된다 (push → 자동 재배포).

## 1. 일상 업데이트 루틴

```bash
# 1) 값 수정 (Excel로 열어도 되지만 UTF-8 CSV 유지 주의 — 권장: VS Code)
#    수정 시 반드시: 값 + 출처 URL + last_checked_at 갱신 + verification_status

# 2) 검증
python scripts/validate_data.py

# 3) 커밋/푸시 (ERROR 0건일 때만)
git add data/
git commit -m "update: OzCHI LBW deadline confirmed"
git push
# → Streamlit Cloud 자동 재배포 (1~2분)
```

## 2. 주기별 체크리스트

**매주 (10분)**
- `python scripts/validate_data.py --weekly` → urgent 큐(마감 지난 open, watchlist 도래,
  open인데 needs_verification)만 출력됨 — 이것만 처리
- 대시보드 "URL 검증" 탭에서 ⑧(마감 지난 open) 정리 → status를 closed로
- "Watchlist" 탭에서 `next_check_date` 도래 항목의 공식 페이지 방문 →
  CFP 떴으면 opportunities.csv에 행 추가, watchlist의 current_status/last_checked_at/next_check_date 갱신

**매월 (30분)**
- needs_verification 항목 중 우선순위 높은 것(core venue) 공식 페이지 재확인
- 마감 4주 이내 항목의 deadline을 공식 페이지에서 재검증 (연장/변경 잦음)
- last_checked_at 60일 경과 경고 항목 갱신

**분기 (1시간)**
- metrics.csv: JCR/Scopus/CORE에서 지표 확인 (6월 JCR 발표 직후 권장)
- fees.csv: 다가오는 학회의 등록비를 fee page에서 채움
- 새 special issue 스캔 (관심 저널 홈페이지)

## 3. 새 opportunity 추가 절차

1. 공식 CFP 페이지 확인 → `sources.csv`에 출처 등록 (S### 부여)
2. `opportunities.csv`에 행 추가 — deadline_source_url 필수, 날짜 YYYY-MM-DD, 타임존 분리
3. 필요 시 `fees.csv`/`metrics.csv` 행 추가
4. `python scripts/validate_data.py` → ERROR 0 확인 → commit/push

## 3b. AI 수정 파이프라인 (권장)

AI에게 CFP 조사·갱신을 시킬 때는 master CSV를 직접 고치게 하지 말고:

1. AI가 `data/proposed_updates/<테이블명>.csv` 초안 생성
   (master 스키마 + `ai_confidence`, `change_note` — 형식: data/proposed_updates/README.md)
2. 대시보드 "🤖 AI 제안 검토" 탭에서 행별 diff·출처·confidence 확인 후
   각 행에 `accept / skip / needs_check` 선택 → "결정 CSV 다운로드"
3. 결정 파일을 `data/proposed_updates_decisions.csv`로 두고 병합
   (자동 백업 → 자동 검증 → ERROR 시 자동 롤백, accept만 반영·나머지는 패치에 유지):
   ```bash
   python scripts/apply_updates.py --apply --decisions data/proposed_updates_decisions.csv
   # 또는 키 직접 지정: --table opportunities --apply --only OPP041
   ```
4. commit/push

전체 흐름: **Collect(AI 조사) → Draft(proposed_updates) → Review(탭에서 decision) →
Validate(자동) → Publish(merge+push) → Notify(주간 digest/ICS)**

## 4. 캘린더 — 구독형 (매번 import 금지)

```bash
python scripts/export_calendar.py    # public/submission_deadlines.ics 갱신
```

이 파일은 **항상 같은 경로에 재생성**되며, 매주 GitHub Actions(weekly-digest)가 자동 갱신·커밋한다.
구독 설정 (1회):

1. ICS를 공개 URL로 노출 — ICS에는 **공개 CFP 정보만** 들어 있으므로 공개해도 안전:
   - 옵션 A: 저장소가 public이면 raw URL 그대로 사용
     (`https://raw.githubusercontent.com/<계정>/submission-dashboard/main/public/submission_deadlines.ics`)
   - 옵션 B: 저장소가 private이면(권장 상태) ICS만 담는 **public gist** 또는 별도 public 저장소에
     워크플로가 push하도록 한 단계 추가 (또는 GitHub Pages)
2. 공개 URL을 `config/calendar.json`의 `ics_public_url`에 입력 → 앱 캘린더 탭에 구독 링크 표시
3. Google Calendar: 설정 → 캘린더 추가 → "URL로 추가" / Outlook: 일정 구독

## 4b. 주간 digest 자동 발송

```bash
python scripts/generate_weekly_digest.py   # public/weekly_digest.md / .html 생성
```

`.github/workflows/weekly-digest.yml`이 **매주 월요일 09:00 KST**에:
validate → ICS 재생성 → digest 생성 → `public/` 커밋 → **GitHub Issue로 발송** (제목 "📬 Weekly submission digest").
GitHub 알림을 메일로 받으면 그대로 메일 배달이 된다.
SMTP 메일/Slack webhook 발송은 워크플로 주석 처리된 단계에 secrets만 넣고 활성화.

digest 내용 = Inbox 탭과 동일: urgent 큐, 30일 이내 마감, watchlist 도래, AI 제안 대기.

## 5. 가중치 변경

`config/weights.json` 수정 → push. 음수 가중치(effort, cost)는 -0.05 형식.

## 6. 배포 (최초 1회)

1. GitHub에 **private** 저장소 생성 후 push
   ```bash
   git init && git add . && git commit -m "init: submission dashboard"
   git remote add origin https://github.com/<계정>/submission-dashboard.git
   git push -u origin main
   ```
2. https://share.streamlit.io → New app → 저장소 선택 →
   **Main file path: `dashboard/app.py`** → Deploy
3. App settings → Sharing에서 viewer 이메일 제한 설정 (보안 정책 §6)

## 7. 주의

- 웹 앱에서의 fit 테이블 편집은 **저장되지 않는다** (클라우드 파일시스템 휘발).
  편집 → "저장용 CSV 다운로드"(원본 스키마 그대로 export됨) →
  `data/project_opportunity_fit.csv`에 덮어쓰기 → validate → push가 정석.
  프로젝트 필터를 건 상태에서 받으면 해당 프로젝트 행만 들어 있으니 전체 덮어쓰기 금지.
- Excel로 CSV 저장 시 인코딩이 깨질 수 있음 — "CSV UTF-8" 형식으로 저장.
- 민감정보 점검 없이 push 금지 (docs/security_policy.md 체크리스트).
