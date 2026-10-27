"""Auto-skip obvious stack mismatches among "Searched" rows; print the rest.

Uses profile.yaml's stack.good (description must match) and stack.bad_title.
"""
import re

from _common import jobs, profile, tracker

stack = profile()["stack"]
GOOD = re.compile(stack["good"], re.I)
BAD_TITLE = re.compile(rf"\b(?:{stack['bad_title']})\b", re.I)
J = jobs()
rows = tracker.load_tracker()
keep = []
for r in rows:
    if r.status != "Searched":
        continue
    j = J.get(r.job_id)
    if not j:
        continue
    if BAD_TITLE.search(j["title"]):
        r.status, r.notes = "Skipped (low fit)", "auto: title stack mismatch"
        continue
    if not GOOD.search(j["description"]):
        r.status, r.notes = "Skipped (low fit)", "auto: none of profile stack.good in description"
        continue
    keep.append(j)
tracker.save_tracker(rows)
print(len(keep), "kept")
for j in keep:
    print(f"{j['job_id']} | {j['title'][:60]} | {j['company'][:25]} | {j['location'][:30]} | {j.get('apply_method') or ''}")
