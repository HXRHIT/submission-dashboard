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

## 4. 캘린더 내보내기

```bash
python scripts/export_calendar.py            # submission_deadlines.ics
python scripts/export_calendar.py --status open
```
생성된 .ics를 Outlook/Google Calendar로 가져오기.

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
  편집 → "수정본 CSV 다운로드" → 로컬에서 data/에 반영 → push가 정석.
- Excel로 CSV 저장 시 인코딩이 깨질 수 있음 — "CSV UTF-8" 형식으로 저장.
- 민감정보 점검 없이 push 금지 (docs/security_policy.md 체크리스트).
