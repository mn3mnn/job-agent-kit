"""Print a compact brief (intro + requirements) for given job ids, or all "Searched" rows.

Usage: brief.py [job_id ...] [--chars N]
"""
import re
import sys

from _common import jobs, tracker
from src.filters import min_years_required, required_language

args = [x for x in sys.argv[1:] if not x.startswith("--")]
n = 1400
if "--chars" in sys.argv:
    n = int(sys.argv[sys.argv.index("--chars") + 1])
    args = [x for x in args if x != str(n)]
J = jobs()
ids = args or [r.job_id for r in tracker.load_tracker() if r.status == "Searched"]
REQ = re.compile(r"(requirements|qualifications|you bring|what you.{0,20}bring|who you are|your profile|"
                 r"what we.{0,10}looking for|must have|about you|you have|skills)", re.I)
for i in ids:
    j = J.get(i)
    if not j:
        continue
    d = j["description"]
    m = REQ.search(d)
    body = d[m.start():] if m else d
    print(f"\n##### {i} | {j['title']} | {j['company']} | {j['location']} | {j.get('apply_method') or 'external'}")
    print(f"lang-required: {required_language(d, ['English'])} | min-years: {min_years_required(d)}")
    print(re.sub(r"\n+", " / ", d[:250]))
    print("REQ:", re.sub(r"\n+", " / ", body[:n]))
