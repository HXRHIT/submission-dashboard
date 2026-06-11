# -*- coding: utf-8 -*-
"""AI 제안(proposed_updates) 검토 후 master CSV에 병합하는 스크립트.

워크플로:
  1. AI가 data/proposed_updates/<테이블명>.csv 에 초안을 만든다
     (스키마 = master와 동일 + 선택 컬럼 ai_confidence, change_note).
  2. 대시보드 "AI 제안 검토" 탭(또는 --list)에서 diff 확인.
  3. 로컬에서 병합:
       python scripts/apply_updates.py --list
       python scripts/apply_updates.py --table opportunities --apply
       python scripts/apply_updates.py --table opportunities --apply --only OPP041,OPP042
       python scripts/apply_updates.py --table opportunities --apply --drop OPP043
       # 대시보드 "AI 제안 검토" 탭에서 받은 결정 CSV 기반 (accept만 반영):
       python scripts/apply_updates.py --apply --decisions data/proposed_updates_decisions.csv

동작:
  - 키 일치 행은 update(패치에 있는 컬럼만 덮어씀), 없는 키는 append.
  - 병합 전 master를 data/backups/ 에 백업.
  - 병합 후 validate_data.py 자동 실행 — ERROR 발생 시 백업으로 자동 롤백.
  - 성공 시 패치 파일을 data/proposed_updates/applied/ 로 이동.

fit 테이블 키는 "P01->OPP001" 형식 (project_id->opportunity_id).
"""
import argparse
import csv
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PU = DATA / "proposed_updates"
BACKUPS = DATA / "backups"

KEYS = {"venues": "venue_id", "opportunities": "opportunity_id", "fees": "fee_id",
        "metrics": "metric_id", "sources": "source_id", "watchlist": "watch_id",
        "projects": "project_id", "project_opportunity_fit": None}
EXTRA_COLS = {"ai_confidence", "change_note"}


def row_key(row, table):
    if table == "project_opportunity_fit":
        return f"{row.get('project_id', '')}->{row.get('opportunity_id', '')}"
    return row.get(KEYS[table], "")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], [
            {k: (v or "").strip() for k, v in r.items() if k is not None} for r in reader
        ]


def write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in fieldnames})


def list_patches():
    patches = sorted(PU.glob("*.csv")) if PU.exists() else []
    if not patches:
        print("대기 중인 제안 파일 없음 (data/proposed_updates/*.csv)")
        return
    for p in patches:
        table = p.stem
        if table not in KEYS:
            print(f"- {p.name}: 알 수 없는 테이블명 (무시됨)")
            continue
        _, prop = read_csv(p)
        master_path = DATA / f"{table}.csv"
        _, master = read_csv(master_path) if master_path.exists() else ([], [])
        mkeys = {row_key(r, table) for r in master}
        upd = sum(1 for r in prop if row_key(r, table) in mkeys)
        print(f"- {p.name}: {len(prop)}행 (update {upd} / add {len(prop) - upd})")
        for r in prop:
            k = row_key(r, table)
            kind = "update" if k in mkeys else "add   "
            note = r.get("change_note", "")
            conf = r.get("ai_confidence", "")
            print(f"    [{kind}] {k}  conf={conf}  {note}")


def apply_table(table, only, drop):
    patch_path = PU / f"{table}.csv"
    master_path = DATA / f"{table}.csv"
    if not patch_path.exists():
        print(f"패치 파일 없음: {patch_path}")
        sys.exit(1)
    if not master_path.exists():
        print(f"master 없음: {master_path}")
        sys.exit(1)

    master_cols, master = read_csv(master_path)
    _, prop = read_csv(patch_path)

    only_set = {s.strip() for s in only.split(",")} if only else None
    drop_set = {s.strip() for s in drop.split(",")} if drop else set()

    selected = []
    for r in prop:
        k = row_key(r, table)
        if k in drop_set:
            continue
        if only_set is not None and k not in only_set:
            continue
        selected.append(r)
    if not selected:
        print("반영할 행이 없습니다 (--only/--drop 필터 확인).")
        sys.exit(1)

    # backup
    BACKUPS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUPS / f"{ts}_{table}.csv"
    shutil.copy2(master_path, backup_path)

    # merge
    index = {row_key(r, table): i for i, r in enumerate(master)}
    n_upd = n_add = 0
    for r in selected:
        k = row_key(r, table)
        clean = {c: v for c, v in r.items() if c in master_cols}
        if k in index:
            master[index[k]].update(clean)
            n_upd += 1
        else:
            master.append({c: clean.get(c, "") for c in master_cols})
            n_add += 1
    write_csv(master_path, master_cols, master)
    print(f"병합 완료: update {n_upd}, add {n_add} (백업: {backup_path.name})")

    # validate; rollback on error
    rc = subprocess.call([sys.executable, str(ROOT / "scripts" / "validate_data.py")])
    if rc != 0:
        shutil.copy2(backup_path, master_path)
        print("검증 ERROR — master를 백업으로 롤백했습니다. 패치 파일을 수정 후 재시도하세요.")
        sys.exit(1)

    # archive patch (일부만 반영한 경우 남은 행은 패치에 유지)
    remaining = [r for r in prop if r not in selected]
    applied_dir = PU / "applied"
    applied_dir.mkdir(parents=True, exist_ok=True)
    if remaining:
        prop_cols = list(selected[0].keys()) if selected else master_cols
        all_cols = list(dict.fromkeys(list(prop[0].keys()) if prop else prop_cols))
        write_csv(applied_dir / f"{ts}_{table}_partial.csv",
                  all_cols, selected)
        write_csv(patch_path, all_cols, remaining)
        print(f"일부 반영 — 남은 {len(remaining)}행은 패치 파일에 유지, "
              f"반영분은 applied/{ts}_{table}_partial.csv 보관.")
    else:
        shutil.move(str(patch_path), str(applied_dir / f"{ts}_{table}.csv"))
        print(f"패치 전체 반영 — applied/{ts}_{table}.csv 로 이동.")
    print("git add/commit/push 잊지 마세요.")


def apply_decisions(decisions_path, table_filter=None):
    """결정 CSV(table,key,decision,...)에서 decision==accept 인 키만 테이블별 반영."""
    path = Path(decisions_path)
    if not path.exists():
        print(f"결정 파일 없음: {path}")
        sys.exit(1)
    _, rows = read_csv(path)
    tables = sorted({r.get("table", "") for r in rows if r.get("table")})
    if table_filter:
        tables = [t for t in tables if t == table_filter]
    if not tables:
        print("결정 파일에 대상 테이블이 없습니다.")
        sys.exit(1)
    for t in tables:
        if t not in KEYS:
            print(f"건너뜀 — 알 수 없는 테이블: {t}")
            continue
        accept = [r["key"] for r in rows
                  if r.get("table") == t and r.get("decision") == "accept" and r.get("key")]
        n_skip = sum(1 for r in rows if r.get("table") == t and r.get("decision") == "skip")
        n_chk = sum(1 for r in rows if r.get("table") == t and r.get("decision") == "needs_check")
        print(f"[{t}] accept {len(accept)} / skip {n_skip} / needs_check {n_chk}")
        if not accept:
            print(f"[{t}] accept된 키 없음 — 건너뜀 (skip/needs_check 행은 패치에 유지)")
            continue
        try:
            apply_table(t, only=",".join(accept), drop=None)
        except SystemExit:
            print(f"[{t}] 반영 실패 — 다음 테이블 진행")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="대기 중인 패치와 diff 요약 출력")
    ap.add_argument("--table", help="대상 테이블명 (예: opportunities)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", help="이 키들만 반영 (콤마 구분)")
    ap.add_argument("--drop", help="이 키들은 제외 (콤마 구분)")
    ap.add_argument("--decisions", help="결정 CSV 경로 — decision=accept 행만 반영")
    args = ap.parse_args()

    if args.apply and args.decisions:
        apply_decisions(args.decisions, args.table)
        return
    if args.list or not (args.table and args.apply):
        list_patches()
        return
    if args.table not in KEYS:
        print(f"알 수 없는 테이블: {args.table} (가능: {sorted(KEYS)})")
        sys.exit(1)
    apply_table(args.table, args.only, args.drop)


if __name__ == "__main__":
    main()
