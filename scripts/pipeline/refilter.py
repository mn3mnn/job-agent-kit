"""Re-run the eligibility filters (language, years, sponsorship) on queued rows.

Usage: refilter.py [search-config.yaml]   (default: search/config.yaml)
Run after changing search/src/filters.py so already-queued jobs get re-checked.
"""
import sys
from types import SimpleNamespace

from _common import jobs, search_config, tracker
from src.filters import eligibility_skip_reason

params = search_config(sys.argv[1] if len(sys.argv) > 1 else "config.yaml")
J = jobs()
rows = tracker.load_tracker()
n = 0
for r in rows:
    if r.status not in ("Searched", "Scored"):
        continue
    j = J.get(r.job_id)
    if not j:
        continue
    why = eligibility_skip_reason(SimpleNamespace(**j), params)
    if why:
        r.status = f"Skipped ({why})"
        n += 1
        print(r.job_id, why, j["title"][:50])
tracker.save_tracker(rows)
print("reskipped", n)
