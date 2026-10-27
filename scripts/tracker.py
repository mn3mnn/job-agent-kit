#!/usr/bin/env python3
"""Canonical read/write path for data/tracker.md.

Mirrors career-ops's own rule ("UPDATE status/notes of existing entries via
the canonical script; do not hand-edit the table") — freeform markdown-table
edits are exactly how a tracker silently corrupts. This script is the only
thing that should touch data/tracker.md.

Usage:
    python scripts/tracker.py sync                # add new jobs.jsonl rows as "Searched"
    python scripts/tracker.py mark <job_id> --status Scored --score 4.2 --notes "..."
    python scripts/tracker.py mark <job_id> --status "Skipped (Easy Apply)"
    python scripts/tracker.py list [--min-score N]  # print sorted, score desc
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
JOBS_JSONL = REPO_ROOT / "search" / "output" / "jobs.jsonl"
TRACKER_PATH = REPO_ROOT / "data" / "tracker.md"

COLUMNS = ["Date", "Company", "Role", "Location", "Score", "Status", "Job ID", "Apply URL", "Notes"]


@dataclass
class Row:
    date: str
    company: str
    role: str
    location: str
    score: str
    status: str
    job_id: str
    apply_url: str
    notes: str

    def to_cells(self):
        return [self.date, self.company, self.role, self.location, self.score, self.status, self.job_id, self.apply_url, self.notes]


def load_tracker() -> list[Row]:
    if not TRACKER_PATH.exists():
        return []
    rows = []
    for line in TRACKER_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", " "}:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells == COLUMNS:
            continue
        if len(cells) != len(COLUMNS):
            continue
        rows.append(Row(*cells))
    return rows


def save_tracker(rows: list[Row]) -> None:
    def sort_key(r: Row):
        try:
            return -float(r.score)
        except ValueError:
            return 0.0  # unscored rows (blank score) sort together, after any real score

    rows_sorted = sorted(rows, key=sort_key)
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "|".join(["---"] * len(COLUMNS)) + "|"]
    for r in rows_sorted:
        lines.append("| " + " | ".join(c.replace("|", "/") for c in r.to_cells()) + " |")
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_PATH.write_text("# Job Search Tracker\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


def sync() -> None:
    if not JOBS_JSONL.exists():
        print(f"No search results yet at {JOBS_JSONL}")
        return
    rows = load_tracker()
    known_ids = {r.job_id for r in rows}
    added = 0
    for line in JOBS_JSONL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            job = json.loads(line)
        except json.JSONDecodeError:
            continue  # line still being written by a running search
        if job["job_id"] in known_ids:
            continue
        status = f"Skipped ({job['skip_reason']})" if job.get("skip_reason") else "Searched"
        rows.append(Row(
            date=job.get("scraped_at", "")[:10],
            company=job.get("company", ""),
            role=job.get("title", ""),
            location=job.get("location", ""),
            score="",
            status=status,
            job_id=job["job_id"],
            apply_url=job.get("apply_url") or "",
            notes="",
        ))
        known_ids.add(job["job_id"])
        added += 1
    save_tracker(rows)
    print(f"Added {added} new row(s) to {TRACKER_PATH}")


def mark(job_id: str, status: Optional[str], score: Optional[str], notes: Optional[str]) -> None:
    rows = load_tracker()
    for r in rows:
        if r.job_id == job_id:
            if status is not None:
                r.status = status
            if score is not None:
                r.score = score
            if notes is not None:
                r.notes = notes
            save_tracker(rows)
            print(f"Updated {job_id}")
            return
    print(f"No tracker row for job_id={job_id}. Run `sync` first.")


def list_rows(min_score: Optional[float]) -> None:
    rows = load_tracker()
    for r in rows:
        if min_score is not None:
            try:
                if float(r.score) < min_score:
                    continue
            except ValueError:
                continue
        print(f"{r.score or '?':>5}  {r.status:<24}  {r.company} — {r.role}  [{r.job_id}]")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sync")

    p_mark = sub.add_parser("mark")
    p_mark.add_argument("job_id")
    p_mark.add_argument("--status")
    p_mark.add_argument("--score")
    p_mark.add_argument("--notes")

    p_list = sub.add_parser("list")
    p_list.add_argument("--min-score", type=float, default=None)

    args = parser.parse_args()
    if args.cmd == "sync":
        sync()
    elif args.cmd == "mark":
        mark(args.job_id, args.status, args.score, args.notes)
    elif args.cmd == "list":
        list_rows(args.min_score)


if __name__ == "__main__":
    main()
