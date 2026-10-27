"""Rank "Searched" rows by a cheap keyword score so the best fits get looked at first.

Prints: score | job_id | cv hits | min years | senior mentions | missing stack | title | company | location
Optional filters: --where <regex on location>  --easy (Easy Apply only)  --student (working student/intern titles only)
"""
import argparse
import re

from _common import jobs, profile, tracker
from src.filters import min_years_required

ap = argparse.ArgumentParser()
ap.add_argument("--where")
ap.add_argument("--easy", action="store_true")
ap.add_argument("--student", action="store_true")
ap.add_argument("-n", type=int, default=60)
a = ap.parse_args()

stack = profile()["stack"]
J = jobs()
out = []
for r in tracker.load_tracker():
    if r.status != "Searched":
        continue
    j = J.get(r.job_id)
    if not j:
        continue
    if a.where and not re.search(a.where, j["location"], re.I):
        continue
    if a.easy and (j.get("apply_method") or "") != "Easy Apply":
        continue
    if a.student and not re.search(r"werkstudent|working student|intern|praktik|student", j["title"], re.I):
        continue
    d = j["description"].lower()
    hit = sum(1 for k in stack["cv_keywords"] if re.search(r"\b" + re.escape(k) + r"\b", d))
    bad = [k for k in stack["missing_keywords"] if re.search(r"\b" + re.escape(k) + r"\b", d)]
    yrs = min_years_required(j["description"])
    senior = len(re.findall(r"\bsenior\b", d))
    score = hit - 2 * len(bad) - (2 if yrs and yrs >= 3 else 0) - senior
    ea = "EA" if (j.get("apply_method") or "") == "Easy Apply" else "ex"
    out.append((score, j["job_id"], ea, hit, yrs, senior, ",".join(bad)[:30], j["title"][:45], j["company"][:20], j["location"][:24]))
for o in sorted(out, reverse=True)[: a.n]:
    print(*o, sep=" | ")
