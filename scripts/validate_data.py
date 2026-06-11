# -*- coding: utf-8 -*-
"""CSV 데이터 검증 스크립트.

사용법:
    python scripts/validate_data.py            # 저장소 루트에서 실행
    python scripts/validate_data.py --data-dir data

오류(ERROR)가 1건이라도 있으면 exit code 1 — CI(GitHub Actions)에 연결 가능.
"""
import argparse
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

URL_RE = re.compile(r"^https?://[^\s,]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STALE_DAYS = 60

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def read(data_dir: Path, name: str):
    path = data_dir / name
    if not path.exists():
        err(f"[{name}] 파일이 없습니다: {path}")
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for i, r in enumerate(rows):
        if None in r:
            err(f"[{name}] {i + 2}행: 컬럼 수가 헤더보다 많음 (CSV 인용 오류 가능)")
        for k, v in list(r.items()):
            if k is not None:
                r[k] = (v or "").strip()
    return rows


def to_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def check_date(table, rid, field, val):
    if val and not DATE_RE.match(val):
        err(f"[{table}] {rid}: {field} 날짜 형식 오류 (YYYY-MM-DD 필요): {val!r}")


def check_url(table, rid, field, val, required=False):
    if val:
        if not URL_RE.match(val):
            err(f"[{table}] {rid}: {field} URL 형식 오류: {val!r}")
    elif required:
        err(f"[{table}] {rid}: {field} 누락")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    data_dir = Path(args.data_dir) if args.data_dir else root / "data"
    today = date.today()

    venues = read(data_dir, "venues.csv")
    opps = read(data_dir, "opportunities.csv")
    fees = read(data_dir, "fees.csv")
    metrics = read(data_dir, "metrics.csv")
    sources = read(data_dir, "sources.csv")
    projects = read(data_dir, "projects.csv")
    fits = read(data_dir, "project_opportunity_fit.csv")
    watch = read(data_dir, "watchlist.csv")

    vids = {r["venue_id"] for r in venues}
    oids = [r["opportunity_id"] for r in opps]
    pids = {r["project_id"] for r in projects}
    sids = {r["source_id"] for r in sources}

    # --- duplicates / FK ---
    seen = set()
    for o in oids:
        if o in seen:
            err(f"[opportunities] 중복 opportunity_id: {o}")
        seen.add(o)
    oid_set = set(oids)

    dup_v = set()
    for r in venues:
        if r["venue_id"] in dup_v:
            err(f"[venues] 중복 venue_id: {r['venue_id']}")
        dup_v.add(r["venue_id"])

    # --- opportunities ---
    for r in opps:
        rid = r.get("opportunity_id", "?")
        if r.get("venue_id") and r["venue_id"] not in vids:
            err(f"[opportunities] {rid}: venue_id FK 불일치: {r['venue_id']}")
        if r.get("source_id") and r["source_id"] not in sids:
            err(f"[opportunities] {rid}: source_id FK 불일치: {r['source_id']}")
        for f in ["abstract_deadline", "paper_deadline", "notification_date",
                  "camera_ready_deadline", "conference_start", "conference_end"]:
            check_date("opportunities", rid, f, r.get(f, ""))
        for f in ["official_cfp_url", "submission_system_url", "template_url",
                  "deadline_source_url", "location_source_url", "page_limit_source_url"]:
            check_url("opportunities", rid, f, r.get(f, ""))
        has_dl = r.get("abstract_deadline") or r.get("paper_deadline")
        if has_dl and not (r.get("deadline_source_url") or r.get("official_cfp_url")):
            err(f"[opportunities] {rid}: deadline이 있는데 deadline_source_url/official_cfp_url 없음")
        ad, pdl = to_date(r.get("abstract_deadline", "")), to_date(r.get("paper_deadline", ""))
        if ad and pdl and pdl < ad:
            err(f"[opportunities] {rid}: paper_deadline({pdl}) < abstract_deadline({ad})")
        cs, ce = to_date(r.get("conference_start", "")), to_date(r.get("conference_end", ""))
        if cs and ce and ce < cs:
            err(f"[opportunities] {rid}: conference_end({ce}) < conference_start({cs})")
        if r.get("status") == "open" and pdl and pdl < today:
            warn(f"[opportunities] {rid}: 마감({pdl})이 지났는데 status=open")
        if r.get("status") in ("open", "upcoming"):
            if not r.get("location_city") and r.get("submission_type") not in ("journal article", "special issue"):
                warn(f"[opportunities] {rid}: location 비어 있음")
            if not r.get("page_limit") and not r.get("word_limit"):
                warn(f"[opportunities] {rid}: page/word limit 비어 있음")

    # --- fees ---
    for r in fees:
        rid = r.get("fee_id", "?")
        if r.get("venue_id") and r["venue_id"] not in vids:
            err(f"[fees] {rid}: venue_id FK 불일치: {r['venue_id']}")
        if r.get("opportunity_id") and r["opportunity_id"] not in oid_set:
            err(f"[fees] {rid}: opportunity_id FK 불일치: {r['opportunity_id']}")
        check_url("fees", rid, "fee_source_url", r.get("fee_source_url", ""))
        if r.get("amount") and not r.get("fee_source_url"):
            err(f"[fees] {rid}: amount가 있는데 fee_source_url 없음")
        if not r.get("amount"):
            warn(f"[fees] {rid}: 금액 비어 있음 (출처 페이지에서 확인 필요)")
        check_date("fees", rid, "fee_deadline", r.get("fee_deadline", ""))

    # --- metrics ---
    for r in metrics:
        rid = r.get("metric_id", "?")
        if r.get("venue_id") and r["venue_id"] not in vids:
            err(f"[metrics] {rid}: venue_id FK 불일치: {r['venue_id']}")
        check_url("metrics", rid, "metric_source_url", r.get("metric_source_url", ""))
        has_val = any(r.get(f) for f in ["impact_factor", "cite_score", "core_ranking",
                                         "h5_index", "acceptance_rate"])
        if has_val and (not r.get("metric_source_url") or not r.get("metric_year")):
            err(f"[metrics] {rid}: 지표 값이 있는데 metric_source_url 또는 metric_year 없음")

    # --- fit ---
    for i, r in enumerate(fits):
        rid = f"{r.get('project_id', '?')}→{r.get('opportunity_id', '?')}"
        if r.get("project_id") not in pids:
            err(f"[fit] {i + 2}행: project_id FK 불일치: {r.get('project_id')}")
        if r.get("opportunity_id") not in oid_set:
            err(f"[fit] {rid}: opportunity_id FK 불일치")
        fs = r.get("fit_score", "")
        if fs:
            try:
                v = float(fs)
                if not (1 <= v <= 5):
                    err(f"[fit] {rid}: fit_score 1~5 범위 벗어남: {fs}")
            except ValueError:
                err(f"[fit] {rid}: fit_score 숫자 아님: {fs!r}")
        check_date("fit", rid, "internal_deadline", r.get("internal_deadline", ""))

    # --- venues / sources / watchlist ---
    for r in venues:
        rid = r.get("venue_id", "?")
        for f in ["official_homepage_url", "official_cfp_url", "proceedings_url",
                  "template_url", "submission_system_url"]:
            check_url("venues", rid, f, r.get(f, ""))
        if r.get("source_id") and r["source_id"] not in sids:
            err(f"[venues] {rid}: source_id FK 불일치: {r['source_id']}")
    for r in sources:
        rid = r.get("source_id", "?")
        check_url("sources", rid, "url", r.get("url", ""), required=True)
        if r.get("reliability") == "low":
            warn(f"[sources] {rid}: reliability=low — 공식 출처로 교체 권장")
    for r in watch:
        rid = r.get("watch_id", "?")
        if r.get("venue_id") and r["venue_id"] not in vids:
            err(f"[watchlist] {rid}: venue_id FK 불일치: {r['venue_id']}")
        for f in ["last_year_cfp_url", "current_year_homepage_url"]:
            check_url("watchlist", rid, f, r.get(f, ""))
        nc = to_date(r.get("next_check_date", ""))
        if nc and nc <= today:
            warn(f"[watchlist] {rid}: next_check_date({nc}) 도래 — 재확인 필요")

    # --- staleness ---
    for name, rows, idf in [("venues", venues, "venue_id"), ("opportunities", opps, "opportunity_id"),
                            ("fees", fees, "fee_id"), ("metrics", metrics, "metric_id"),
                            ("watchlist", watch, "watch_id")]:
        for r in rows:
            lc = to_date(r.get("last_checked_at", ""))
            if lc and (today - lc).days > STALE_DAYS:
                warn(f"[{name}] {r.get(idf, '?')}: last_checked_at {lc} — {STALE_DAYS}일 경과")
            if r.get("verification_status") == "needs_verification":
                warn(f"[{name}] {r.get(idf, '?')}: needs_verification")

    # --- report ---
    print(f"=== validate_data.py — {today.isoformat()} ===")
    print(f"ERRORS: {len(errors)}")
    for e in errors:
        print("  ERROR:", e)
    print(f"WARNINGS: {len(warnings)}")
    for w in warnings:
        print("  WARN :", w)
    if errors:
        sys.exit(1)
    print("OK — 필수 오류 없음")


if __name__ == "__main__":
    main()
