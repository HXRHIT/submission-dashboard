# -*- coding: utf-8 -*-
"""Weekly automatic maintenance for public submission data.

The script performs two kinds of updates:

1. Safe deterministic updates applied directly to master CSVs.
   Example: an open opportunity with a past paper deadline becomes closed.

2. Source-page research written to data/proposed_updates/*.csv.
   These rows keep the master schema and add ai_confidence/change_note so the
   dashboard can review them before merging. Arbitrary CFP pages are too varied
   to trust with blind deadline edits, so fetched evidence is proposed, not
   applied.
"""
from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROPOSED = DATA / "proposed_updates"

DATE_RE = re.compile(r"\b20\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])\b")
MONTH_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+(?:0?[1-9]|[12]\d|3[01]),?\s+20\d{2}\b",
    re.IGNORECASE,
)
USER_AGENT = "submission-dashboard-weekly-bot/1.0"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], [
            {k: (v or "").strip() for k, v in row.items() if k is not None}
            for row in reader
        ]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in fieldnames})


def upsert_csv(path: Path, key_field: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    old_cols, old_rows = read_csv(path)
    out_cols = list(dict.fromkeys(old_cols + fieldnames))
    index = {row.get(key_field, ""): i for i, row in enumerate(old_rows) if row.get(key_field, "")}
    merged = list(old_rows)
    for row in rows:
        key = row.get(key_field, "")
        if key and key in index:
            merged[index[key]].update(row)
        else:
            merged.append(row)
    write_csv(path, out_cols, merged)


def to_date(value: str):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def clean_text(raw: bytes, content_type: str) -> str:
    encoding = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type or "", re.IGNORECASE)
    if match:
        encoding = match.group(1)
    text = raw.decode(encoding, errors="replace")
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_text(url: str, timeout: int) -> tuple[bool, str]:
    if not url:
        return False, "no_url"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as res:
            raw = res.read(500_000)
            return True, clean_text(raw, res.headers.get("Content-Type", ""))
    except HTTPError as exc:
        return False, f"http_{exc.code}"
    except URLError as exc:
        return False, f"url_error:{exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return False, f"fetch_error:{exc}"


def date_snippets(text: str, limit: int = 8) -> str:
    matches = []
    for pattern in (DATE_RE, MONTH_RE):
        for match in pattern.finditer(text):
            start = max(0, match.start() - 45)
            end = min(len(text), match.end() + 45)
            matches.append(text[start:end].strip())
    deduped = []
    seen = set()
    for item in matches:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return " | ".join(deduped[:limit])


def close_past_open_opportunities(today: date, apply: bool) -> int:
    path = DATA / "opportunities.csv"
    cols, rows = read_csv(path)
    changed = 0
    for row in rows:
        deadline = to_date(row.get("paper_deadline", ""))
        if row.get("status") == "open" and deadline and deadline < today:
            row["status"] = "closed"
            row["last_checked_at"] = today.isoformat()
            note = f"Auto-closed by weekly maintenance on {today.isoformat()} because paper_deadline passed."
            row["notes"] = f"{row.get('notes', '')} {note}".strip()
            changed += 1
    if changed and apply:
        write_csv(path, cols, rows)
    return changed


def due_opportunities(rows: list[dict[str, str]], today: date) -> list[dict[str, str]]:
    due = []
    soon = today + timedelta(days=60)
    for row in rows:
        if row.get("status") not in {"open", "upcoming", "rolling", "unknown"}:
            continue
        deadline = to_date(row.get("paper_deadline", ""))
        needs_verification = row.get("verification_status") == "needs_verification"
        stale = (to_date(row.get("last_checked_at", "")) or date.min) < today - timedelta(days=60)
        deadline_soon = deadline is not None and today <= deadline <= soon
        if needs_verification or stale or deadline_soon:
            due.append(row)
    return due


def due_watchlist(rows: list[dict[str, str]], today: date) -> list[dict[str, str]]:
    return [
        row for row in rows
        if (to_date(row.get("next_check_date", "")) or date.max) <= today
        or row.get("current_status") in {"CFP not released", "unknown"}
    ]


def build_opportunity_proposals(today: date, timeout: int, no_fetch: bool) -> int:
    cols, opps = read_csv(DATA / "opportunities.csv")
    if not opps:
        return 0
    out_cols = list(dict.fromkeys(cols + ["ai_confidence", "change_note"]))
    proposals = []
    for row in due_opportunities(opps, today):
        url = row.get("official_cfp_url") or row.get("deadline_source_url")
        proposed = dict(row)
        proposed["last_checked_at"] = today.isoformat()
        if no_fetch:
            proposed["ai_confidence"] = "low"
            proposed["change_note"] = f"Queued for weekly source check: {url}"
        else:
            ok, text = fetch_text(url, timeout)
            if ok:
                snippets = date_snippets(text)
                proposed["ai_confidence"] = "medium" if snippets else "low"
                proposed["change_note"] = (
                    f"Weekly source fetch OK: {url}. "
                    f"Date evidence candidates: {snippets or 'none found'}"
                )
            else:
                proposed["ai_confidence"] = "low"
                proposed["change_note"] = f"Weekly source fetch failed ({text}): {url}"
        proposals.append(proposed)
    if proposals:
        upsert_csv(PROPOSED / "opportunities.csv", "opportunity_id", out_cols, proposals)
    return len(proposals)


def build_watchlist_proposals(today: date, timeout: int, no_fetch: bool) -> int:
    cols, watch = read_csv(DATA / "watchlist.csv")
    if not watch:
        return 0
    out_cols = list(dict.fromkeys(cols + ["ai_confidence", "change_note"]))
    proposals = []
    for row in due_watchlist(watch, today):
        url = row.get("current_year_homepage_url") or row.get("last_year_cfp_url")
        proposed = dict(row)
        proposed["last_checked_at"] = today.isoformat()
        proposed["next_check_date"] = (today + timedelta(days=7)).isoformat()
        if no_fetch:
            proposed["ai_confidence"] = "low"
            proposed["change_note"] = f"Queued for weekly watchlist check: {url}"
        else:
            ok, text = fetch_text(url, timeout)
            if ok:
                snippets = date_snippets(text)
                if re.search(r"\b(call for papers|cfp|submission|deadline)\b", text, re.IGNORECASE):
                    proposed["current_status"] = "CFP released"
                proposed["ai_confidence"] = "medium" if snippets else "low"
                proposed["change_note"] = (
                    f"Weekly watchlist fetch OK: {url}. "
                    f"Date evidence candidates: {snippets or 'none found'}"
                )
            else:
                proposed["ai_confidence"] = "low"
                proposed["change_note"] = f"Weekly watchlist fetch failed ({text}): {url}"
        proposals.append(proposed)
    if proposals:
        upsert_csv(PROPOSED / "watchlist.csv", "watch_id", out_cols, proposals)
    return len(proposals)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-safe", action="store_true", help="Apply deterministic master CSV updates.")
    parser.add_argument("--propose", action="store_true", help="Write proposed_updates from weekly source checks.")
    parser.add_argument("--no-fetch", action="store_true", help="Do not access source URLs; useful for local tests.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--today", default=None, help="Override date as YYYY-MM-DD for tests.")
    args = parser.parse_args()

    today = to_date(args.today) if args.today else date.today()
    if today is None:
        raise SystemExit("--today must be YYYY-MM-DD")

    closed = close_past_open_opportunities(today, apply=args.apply_safe)
    opp_props = build_opportunity_proposals(today, args.timeout, args.no_fetch) if args.propose else 0
    watch_props = build_watchlist_proposals(today, args.timeout, args.no_fetch) if args.propose else 0

    print(
        "weekly_auto_update:",
        f"safe_closed={closed}{' applied' if args.apply_safe else ' dry-run'}",
        f"opportunity_proposals={opp_props}",
        f"watchlist_proposals={watch_props}",
        f"fetch={'off' if args.no_fetch else 'on'}",
    )


if __name__ == "__main__":
    main()
