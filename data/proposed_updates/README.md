# proposed_updates — AI 수정 초안 폴더

AI(또는 사람)가 master CSV를 **직접 수정하지 않고** 여기에 초안을 둔다.

## 규칙

- 파일명 = master CSV와 동일: `opportunities.csv`, `fees.csv`, `metrics.csv`,
  `sources.csv`, `venues.csv`, `watchlist.csv`, `projects.csv`, `project_opportunity_fit.csv`
- 스키마 = master와 동일 컬럼 + 선택 컬럼 2개:
  - `ai_confidence` — high / medium / low
  - `change_note` — 변경 이유 (출처 URL 포함 권장)
- 키가 master에 있으면 update(패치에 적은 컬럼만 덮어씀), 없으면 add.
- deadline/fee/metric 값은 **공식 URL 없으면 비워두고 needs_verification** (source policy 동일).

## 검토/반영

1. 대시보드 "🤖 AI 제안 검토" 탭에서 diff 확인
2. `python scripts/apply_updates.py --list`
3. `python scripts/apply_updates.py --table opportunities --apply [--only KEY1,KEY2] [--drop KEY3]`
   - 병합 전 자동 백업(data/backups/), 병합 후 자동 검증, ERROR 시 자동 롤백
   - 반영된 패치는 `applied/`로 이동

fit 테이블의 키는 `P01->OPP001` 형식.
