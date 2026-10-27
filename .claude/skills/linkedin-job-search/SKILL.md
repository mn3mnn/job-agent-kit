---
name: linkedin-job-search
description: Process LinkedIn search results end to end - filter and rank jobs from search/output/jobs.jsonl against the candidate's cv.md, tailor a resume (and cover letter) with resume-gen, and apply through LinkedIn Easy Apply or the company's ATS with playwright-cli. Use after run_search.py has produced rows, or when asked to "process the search results", "apply to N jobs", or "find and apply to jobs".
---

# LinkedIn Job Search + Apply

`search/run_search.py` only collects postings (no judgment). This skill does
everything that needs judgment: picking jobs, tailoring, filling forms.

## Sources of truth

- `cv.md` (repo root): every fact on a resume, cover letter or form answer.
  Its "Application Details" section answers form questions (salary, notice,
  availability, work authorization table, self-identification).
- `profile.yaml` (repo root): contact details and resume layout facts.
- `config.yaml` (this folder): `min_score_to_apply`, `auto_submit`,
  `easy_apply_daily_cap`.
- `data/tracker.md`: application status. Only touch it via `scripts/tracker.py`.

## Hard rules

- **Never fabricate.** If cv.md doesn't answer a required question, ask the
  user. Personal choices (e.g. "willing to work on military projects?",
  permit expiry dates, personality tests) are always the user's call: park the
  job as `Needs input` and keep going with others.
- **Screen before you apply, as a separate step.** Read the brief (language,
  years, location, sponsorship) and decide; never chain the screen and the
  submit in one command, or a disqualifier can slip through unread.
- **Eligibility** (also in `search/src/filters.py`, configured per search
  config): skip jobs requiring a language not in `allowed_languages`, more
  than `max_years_experience`, or that explicitly refuse sponsorship outside
  `work_authorized_countries`. Silence on sponsorship is fine.
- **Skip, don't fight:** CAPTCHAs, "transcript required" when none exists,
  account walls you can't pass, roles requiring residence in a city the user
  can't commute to (cv.md lists commutable cities).
- **Answer truthfully on authorization**, per cv.md's legal table. Don't claim
  a permit or citizenship the candidate doesn't have.
- **Pacing:** stay under `easy_apply_daily_cap` Easy Apply submissions a day.
- If `auto_submit` is false, stop on the final page and list what's ready.

## Step 1: Refresh the queue

```bash
python3 scripts/tracker.py sync               # jobs.jsonl -> tracker rows
python3 scripts/pipeline/refilter.py          # re-apply eligibility filters
python3 scripts/pipeline/triage.py > /dev/null  # auto-skip stack mismatches (profile.yaml stack.*)
python3 scripts/pipeline/rank.py --where Germany --student   # examples of priority slices
python3 scripts/pipeline/rank.py --easy -n 40
```

Work in the priority order the user asks for (e.g. working student roles in
country X, then full-time in X, then other countries), Easy Apply first
within each slice since it's fastest.

## Step 2: Screen

```bash
python3 scripts/pipeline/brief.py <job_id> [<job_id> ...]
```

Check: required languages, years, location/on-site policy, sponsorship or
residency wording, required documents. Skip with a reason:

```bash
python3 scripts/tracker.py mark <job_id> --status "Skipped (requires German)" --notes "..."
```

If the filters missed a phrasing, add it to `search/src/filters.py` (with a
quick test) so it's caught next time.

## Step 3: Tailor (resume-gen)

Write an overrides JSON (summary, skills, `jobs_patch` for reordered/rephrased
bullets, optional `cover_letter`) and render:

```bash
python3 scripts/pipeline/mkspec.py <job_id>-<key> overrides.json
```

It must print `OK` (one page). Rules are in the resume-gen skill: only cv.md
facts, up to 4 JD keywords that are close neighbours of cv.md skills, no em
dashes. Write a cover letter whenever the form has a slot for one, even optional.

## Step 4: Apply

Open the browser session once (log in to LinkedIn in it the first time):

```bash
playwright-cli -s=apply open --headed --profile=search/chrome_profile/apply_profile https://www.linkedin.com/feed/
source scripts/apply-helpers.sh
resolve <job_id>      # EASY <ref> | EXT <url> | APPLIED | CLOSED | LOGGED_OUT
```

**Easy Apply:** `a1 <job_id> <key>` runs the autopilot (uploads the tailored
resume, unticks "Follow company", fills city). It prints `SENT`, `CLOSED`, or
`NEEDS INPUT:` with the unanswered fields. Answer with `pick "<question>"
"<option>"`, `$P fill <ref> <text>`, `$P select <ref> <option>`, then `fin`.
Read radio options first with `pick "<question>" zz` (prints the choices).

**External ATS:** helpers for the common ones:
- Ashby: `ashby <url>/application <resume>`, then fill the rest, `ayn
  "<question>" Yes`, `ashby_submit`. Yes/No buttons can reset when another
  field re-renders; re-click them right before submitting.
- Personio: `personio <url> <resume> [cover]`. Uploads first, then text
  fields (the form re-renders on upload). Submit stays disabled until every
  required field, including a required cover letter, is filled.
- Greenhouse: fill by ref; `gp <ref> <option> [typed]` for dropdowns; files
  via `upload_file <path>`. Some boards email a security code before submit:
  ask the user for it.
- Lever / Recruitee / SmartRecruiters often show hCaptcha or slider captchas
  on submit: skip them.
- Workday / SuccessFactors need an account (generated password, stored outside
  the repo) and often email a code.

After every submit, confirm the success message, then:

```bash
python3 scripts/tracker.py mark <job_id> --status Applied --notes "Submitted <date> via <route>. Resume: <path>"
```

If `resolve` prints `LOGGED_OUT`, stop and ask the user to log in again in
the browser window.

## Step 5: Report

Count of submissions, list by priority slice, anything parked with exactly
what's needed from the user, skips with reasons, and any answer you weren't
sure about.
