# -*- coding: utf-8 -*-
"""opportunities.csv → ICS 캘린더 내보내기.

사용법:
    python scripts/export_calendar.py                  # submission_deadlines.ics 생성
    python scripts/export_calendar.py --out my.ics --status open upcoming rolling

생성된 .ics 파일은 Outlook/Google Calendar에서 가져오기 하면 됩니다.
마감일은 종일(all-day) 이벤트로 만들고 제목에 타임존(AoE 등)을 표기합니다.
"""
import argparse
import csv
from datetime import datetime
from pathlib import Path

EVENT_FIELDS = [
    ("abstract_deadline", "Abstract deadline"),
    ("paper_deadline", "Paper deadline"),
    ("notification_date", "Notification"),
    ("camera_ready_deadline", "Camera-ready"),
    ("conference_start", "Conference start"),
]


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="submission_deadlines.ics")
    ap.add_argument("--status", nargs="*", default=["open", "upcoming", "rolling"])
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    with open(root / "data" / "opportunities.csv", encoding="utf-8-sig", newline="") as f:
        opps = list(csv.DictReader(f))
    with open(root / "data" / "venues.csv", encoding="utf-8-sig", newline="") as f:
        venues = {r["venue_id"]: r for r in csv.DictReader(f)}

    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//submission-dashboard//export_calendar//KO", "CALSCALE:GREGORIAN"]
    n = 0
    for r in opps:
        if args.status and r.get("status", "") not in args.status:
            continue
        acro = venues.get(r.get("venue_id", ""), {}).get("acronym", r.get("venue_id", ""))
        for field, label in EVENT_FIELDS:
            val = (r.get(field) or "").strip()
            if not val:
                continue
            try:
                d = datetime.strptime(val, "%Y-%m-%d").date()
            except ValueError:
                continue
            tz = (r.get("deadline_timezone") or "").strip()
            tz_str = f" ({tz})" if tz and "deadline" in field else ""
            summary = f"[{acro}] {label}{tz_str} — {r.get('track_name', '')}"
            desc_parts = [
                f"Track: {r.get('track_name', '')}",
                f"Type: {r.get('submission_type', '')}",
                f"Status: {r.get('status', '')}",
                f"CFP: {r.get('official_cfp_url', '')}",
                f"Deadline source: {r.get('deadline_source_url', '')}",
                f"Verification: {r.get('verification_status', '')}",
            ]
            uid = f"{r.get('opportunity_id', n)}-{field}@submission-dashboard"
            n += 1
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
                f"SUMMARY:{esc(summary)}",
                f"DESCRIPTION:{esc(' | '.join(desc_parts))}",
                f"URL:{r.get('official_cfp_url', '')}",
                "END:VEVENT",
            ]
    lines.append("END:VCALENDAR")
    out = Path(args.out)
    out.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(f"wrote {out} ({n} events)")


if __name__ == "__main__":
    main()
