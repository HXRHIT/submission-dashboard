# Weekly Auto Update

The repository now has a weekly automation that runs every Monday at 09:00 KST.

## Trigger

- GitHub Actions schedule: `.github/workflows/weekly-digest.yml`
- Cron: `0 0 * * 1`
- Meaning: every Monday 00:00 UTC, which is Monday 09:00 in Korea.
- Manual trigger: GitHub Actions `workflow_dispatch`.

## What It Updates Automatically

The workflow runs:

```bash
python scripts/weekly_auto_update.py --apply-safe --propose
python scripts/validate_data.py
python scripts/export_calendar.py
python scripts/generate_weekly_digest.py
```

Safe deterministic changes are applied directly to master CSV files. For now:

- `opportunities.csv`: if `status=open` and `paper_deadline` is already past, status is changed to `closed`.
- `last_checked_at` is updated for that safe change.

Uncertain source-page findings are not blindly merged. They are written to:

- `data/proposed_updates/opportunities.csv`
- `data/proposed_updates/watchlist.csv`

Those proposed rows include:

- `ai_confidence`
- `change_note`
- fetched official URL status
- date-like evidence snippets found on the source page

This keeps the dashboard automatic while avoiding bad deadline edits from noisy CFP pages.

## Output

The workflow commits:

- `data/`
- `public/submission_deadlines.ics`
- `public/weekly_digest.md`
- `public/weekly_digest.html`

It also opens a GitHub Issue with the weekly digest.

## Review Flow

In the dashboard, turn on `관리자 도구 표시` in the sidebar and open `AI 제안`.

Accept only proposals whose official-source evidence is clear. Then merge with:

```bash
python scripts/apply_updates.py --apply --decisions data/proposed_updates_decisions.csv
```

## Local Test

Run without network:

```bash
python scripts/weekly_auto_update.py --apply-safe --propose --no-fetch
```

Run with official URL fetches:

```bash
python scripts/weekly_auto_update.py --apply-safe --propose
```
