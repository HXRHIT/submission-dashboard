# -*- coding: utf-8 -*-
"""opportunities.csv → ICS 캘린더 내보내기 (구독용 고정 경로).

사용법:
    python scripts/export_calendar.py                  # public/submission_deadlines.ics 생성
    python scripts/export_calendar.py --out my.ics --status open upcoming rolling

기본 출력은 항상 같은 경로(public/submission_deadlines.ics)에 덮어쓰므로,
이 파일을 공개 URL로 노출하면 Google Calendar/Outlook에서 "URL로 구독"이 가능하다
(매주 GitHub Actions가 재생성 — .github/workflows/weekly-digest.yml).
ICS에는 공개 CFP 정보만 들어가므로 공개해도 안전하다 (security policy).
마감일은 종일(all-day) 이벤트로 만들고 제목에 타임존(AoE 등)을 표기한다.
"""
import argparse
import csv
from datetime import datetime, timedelta
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


def fold(line: str) -> str:
    """RFC 5545 줄접기: 한 줄 최대 75옥텟, 이어지는 줄은 공백으로 시작.
    Google Calendar는 길게 이어진 줄을 조용히 거부할 수 있어 필수."""
    b = line.encode("utf-8")
    if len(b) <= 73:
        return line
    parts = []
    first = True
    while b:
        limit = 73 if first else 72
        cut = min(limit, len(b))
        while cut < len(b) and (b[cut] & 0xC0) == 0x80:  # UTF-8 문자 중간에서 자르지 않기
            cut -= 1
        parts.append(b[:cut].decode("utf-8"))
        b = b[cut:]
        first = False
    return "\r\n ".join(parts)


def main():
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(root / "public" / "submission_deadlines.ics"))
    ap.add_argument("--status", nargs="*", default=["open", "upcoming", "rolling"])
    args = ap.parse_args()
    with open(root / "data" / "opportunities.csv", encoding="utf-8-sig", newline="") as f:
        opps = list(csv.DictReader(f))
    with open(root / "data" / "venues.csv", encoding="utf-8-sig", newline="") as f:
        venues = {r["venue_id"]: r for r in csv.DictReader(f)}

    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//submission-dashboard//export_calendar//KO",
             "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH",
             "X-WR-CALNAME:Submission Deadlines",
             "X-WR-TIMEZONE:Asia/Seoul",
             "REFRESH-INTERVAL;VALUE=DURATION:P1D",
             "X-PUBLISHED-TTL:P1D"]
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
                f"DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime('%Y%m%d')}",
                f"SUMMARY:{esc(summary)}",
                f"DESCRIPTION:{esc(' | '.join(desc_parts))}",
                f"URL:{r.get('official_cfp_url', '')}",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ]
    lines.append("END:VCALENDAR")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\r\n".join(fold(ln) for ln in lines) + "\r\n", encoding="utf-8")
    print(f"wrote {out} ({n} events)")


if __name__ == "__main__":
    main()
