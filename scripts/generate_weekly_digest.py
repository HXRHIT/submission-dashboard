# -*- coding: utf-8 -*-
"""주간 다이제스트 생성 — "연구자에게 일을 배달하는" 단계.

생성물:
    public/weekly_digest.md    (GitHub Issue/메일/Slack 본문용)
    public/weekly_digest.html  (메일 HTML/브라우저용)

내용: urgent 작업 큐(validate --weekly와 동일) + 30일 이내 마감 + watchlist 도래
      + AI 제안(proposed_updates) 대기 현황.

매주 자동 실행/발송: .github/workflows/weekly-digest.yml
(digest 커밋 + GitHub Issue 생성. 메일/Slack을 원하면 워크플로에 단계 추가 —
 docs/update_guide.md 참고.)
"""
import csv
import html
import sys
from datetime import date, datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUBLIC = ROOT / "public"
sys.path.insert(0, str(ROOT / "scripts"))
from validate_data import run_checks, to_date  # noqa: E402


def read_csv(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items() if k is not None}
                for r in csv.DictReader(f)]


def main():
    today = date.today()
    errs, warns = run_checks(DATA, today)
    urgent = [m for s, m in warns if s == "urgent"]
    normal = [m for s, m in warns if s == "normal"]
    backlog = [m for s, m in warns if s == "backlog"]

    opps = read_csv(DATA / "opportunities.csv")
    venues = {r["venue_id"]: r for r in read_csv(DATA / "venues.csv")}
    watch = read_csv(DATA / "watchlist.csv")

    # 30일 이내 마감 (open/upcoming)
    soon = []
    for r in opps:
        if r.get("status") not in ("open", "upcoming"):
            continue
        for field, label in [("abstract_deadline", "abstract"), ("paper_deadline", "paper")]:
            d = to_date(r.get(field, ""))
            if d and 0 <= (d - today).days <= 30:
                acro = venues.get(r.get("venue_id", ""), {}).get("acronym", r.get("venue_id", ""))
                soon.append({
                    "dday": (d - today).days, "date": d.isoformat(), "kind": label,
                    "venue": acro, "track": r.get("track_name", ""),
                    "tz": r.get("deadline_timezone", ""),
                    "url": r.get("official_cfp_url", "") or r.get("deadline_source_url", ""),
                    "verif": r.get("verification_status", ""),
                })
    soon.sort(key=lambda x: x["dday"])

    # watchlist 도래
    due = []
    for r in watch:
        nc = to_date(r.get("next_check_date", ""))
        if nc and nc <= today:
            due.append({
                "watch_id": r.get("watch_id", ""), "venue_id": r.get("venue_id", ""),
                "status": r.get("current_status", ""),
                "url": r.get("current_year_homepage_url", "") or r.get("last_year_cfp_url", ""),
                "notes": r.get("notes", ""),
            })

    # AI 제안 대기
    pu = DATA / "proposed_updates"
    proposals = []
    for p in sorted(pu.glob("*.csv")) if pu.exists() else []:
        proposals.append((p.name, len(read_csv(p))))

    # ---------- markdown ----------
    md = [f"# 📬 Weekly Submission Digest — {today.isoformat()}", ""]
    md.append(f"요약: ERROR {len(errs)} · urgent {len(urgent)} · "
              f"30일 이내 마감 {len(soon)} · watchlist 도래 {len(due)} · "
              f"AI 제안 대기 {sum(n for _, n in proposals)}행")
    md.append("")
    md.append("## 🔥 이번 주 작업 큐 (urgent)")
    md += [f"- [ ] {m}" for m in urgent] or ["- 없음 🎉"]
    md.append("")
    md.append("## 🗓 30일 이내 마감")
    if soon:
        md.append("| D-day | 날짜 | 종류 | venue | track | TZ | 검증 | CFP |")
        md.append("|---|---|---|---|---|---|---|---|")
        for s in soon:
            md.append(f"| D-{s['dday']} | {s['date']} | {s['kind']} | {s['venue']} "
                      f"| {s['track']} | {s['tz']} | {s['verif']} | {s['url']} |")
    else:
        md.append("- 없음")
    md.append("")
    md.append("## 👀 Watchlist 확인 도래")
    md += [f"- [ ] {d['watch_id']} ({d['venue_id']}, {d['status']}) — {d['url']} — {d['notes']}"
           for d in due] or ["- 없음"]
    md.append("")
    md.append("## 🤖 AI 제안 대기 (proposed_updates)")
    md += [f"- {name}: {n}행 → 대시보드 'AI 제안 검토' 탭에서 확인" for name, n in proposals] \
        or ["- 없음"]
    md.append("")
    if errs:
        md.append("## ❌ 데이터 ERROR (즉시 수정)")
        md += [f"- {e}" for e in errs]
        md.append("")
    md.append(f"_normal 경고 {len(normal)}건 / backlog {len(backlog)}건 — "
              "`python scripts/validate_data.py`로 전체 확인._")
    md_text = "\n".join(md) + "\n"

    # ---------- html ----------
    def li(items):
        return "".join(f"<li>{html.escape(i)}</li>" for i in items) or "<li>없음</li>"

    rows = "".join(
        f"<tr><td>D-{s['dday']}</td><td>{s['date']}</td><td>{s['kind']}</td>"
        f"<td>{html.escape(s['venue'])}</td><td>{html.escape(s['track'])}</td>"
        f"<td>{html.escape(s['tz'])}</td><td>{html.escape(s['verif'])}</td>"
        f"<td><a href='{html.escape(s['url'])}'>CFP</a></td></tr>"
        for s in soon)
    html_text = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>Weekly Submission Digest {today.isoformat()}</title>
<style>body{{font-family:sans-serif;max-width:880px;margin:2em auto;padding:0 1em}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:4px 8px;font-size:14px}}
h2{{border-bottom:2px solid #2563eb;padding-bottom:4px}}</style></head><body>
<h1>📬 Weekly Submission Digest — {today.isoformat()}</h1>
<p>ERROR {len(errs)} · urgent {len(urgent)} · 30일 이내 마감 {len(soon)} ·
watchlist 도래 {len(due)} · AI 제안 대기 {sum(n for _, n in proposals)}행</p>
<h2>🔥 이번 주 작업 큐</h2><ul>{li(urgent)}</ul>
<h2>🗓 30일 이내 마감</h2>
<table><tr><th>D-day</th><th>날짜</th><th>종류</th><th>venue</th><th>track</th>
<th>TZ</th><th>검증</th><th>CFP</th></tr>{rows or "<tr><td colspan='8'>없음</td></tr>"}</table>
<h2>👀 Watchlist 확인 도래</h2>
<ul>{li([f"{d['watch_id']} ({d['venue_id']}, {d['status']}) — {d['url']}" for d in due])}</ul>
<h2>🤖 AI 제안 대기</h2>
<ul>{li([f"{name}: {n}행" for name, n in proposals])}</ul>
{"<h2>❌ 데이터 ERROR</h2><ul>" + li(errs) + "</ul>" if errs else ""}
<p><small>generated {datetime.now().strftime("%Y-%m-%d %H:%M")} ·
normal {len(normal)} / backlog {len(backlog)} — validate_data.py로 전체 확인</small></p>
</body></html>"""

    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "weekly_digest.md").write_text(md_text, encoding="utf-8")
    (PUBLIC / "weekly_digest.html").write_text(html_text, encoding="utf-8")
    print(f"wrote public/weekly_digest.md / .html "
          f"(urgent {len(urgent)}, soon {len(soon)}, watchlist {len(due)}, "
          f"proposals {sum(n for _, n in proposals)})")


if __name__ == "__main__":
    main()
