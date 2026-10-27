# Job Agent Kit

Find jobs on LinkedIn, tailor a one-page resume and a short cover letter for
each, and apply through LinkedIn Easy Apply or the company's own ATS, driven
by [Claude Code](https://claude.com/claude-code) and `playwright-cli`.

## Quick start: paste this into Claude Code

Open Claude Code in this folder, fill in the brackets, and send:

```
Set up this repo for me and then start applying to jobs. Follow README.md and the skills in .claude/skills/.

1. Setup
- Install everything from the README: the search venv, patchright chromium, the npm packages for resume-gen, and check that playwright-cli works.
- Create profile.yaml and cv.md from the examples using my CV, attached/pasted below. Ask me about anything the examples need that my CV doesn't cover (salary, notice period, work authorization per country, commutable cities, which questions to always ask me about). Don't guess any of it.
- Replace templates/base-spec.json with my real default resume content, render a test resume, and show me the PDF before going on.

2. Search
- Target roles: [e.g. Junior Backend Engineer, Python Developer, Working Student Software]
- Locations, in priority order: [e.g. working student in Berlin, then full-time in Germany, then remote EU]
- Languages I can work in: [e.g. English, Spanish]
- Countries where I don't need sponsorship: [e.g. Germany]
- Max years of experience to consider: [e.g. 3]
- Time window: [past week / past month]
Write a search config per priority slice and run them in that order. Start the browser so I can log in to LinkedIn once, then copy the profile to apply_profile.

3. Apply
- Goal: [N] applications today, working through the priority slices in order, Easy Apply first within each slice.
- Screen every job before applying (language, years, location, sponsorship) and tell me why you skipped any.
- Tailor a resume for every job, and a short cover letter wherever the form has a slot for one.
- auto_submit: [false = stop on the last page so I can review the first few | true = submit yourself]
- Ask me only for OTP/security codes and answers that aren't in cv.md. Skip captchas.
- Log everything with scripts/tracker.py. Send me a short progress line every ~5 applications and a summary at the end: submitted, skipped with reasons, and anything waiting on me.

My CV:
[paste CV text or attach the PDF]
```

Start with `auto_submit: false` and approve the first 5 to 10 applications
yourself, then switch it to `true`. On later days a short prompt is enough:
"Run the searches again and apply to 20 more jobs, same priority as last time."

```
search/run_search.py            collects postings into search/output/jobs.jsonl
                                (guest API, eligibility filters, apply-route detection)
scripts/tracker.py              data/tracker.md is the application log
scripts/pipeline/*.py           refilter, triage, rank, brief, mkspec
.claude/skills/resume-gen       tailored resume + cover letter PDFs from cv.md
.claude/skills/linkedin-job-search  the playbook Claude follows to screen and apply
scripts/apply-helpers.sh        Easy Apply autopilot + Ashby/Personio/Greenhouse helpers
```

## Read this first

- **LinkedIn's User Agreement prohibits automated scraping and automated
  applications.** Using this can get your account restricted. Run it under
  your own account only if you accept that risk, and keep the pace human
  (`easy_apply_daily_cap` in the skill config).
- **You are responsible for what gets submitted in your name.** By default
  `auto_submit: false` (`.claude/skills/linkedin-job-search/config.yaml`):
  Claude fills everything and stops on the final page. Set it to `true` only
  once you trust the output.
- The resume rules forbid inventing anything: every claim comes from your
  `cv.md`. Keep it complete and honest.

## Setup

Requirements: Python 3.11+, Node 18+, Claude Code, and
[playwright-cli](https://github.com/microsoft/playwright-cli) on your PATH.

```bash
# 1. Your data (both files are gitignored)
cp profile.example.yaml profile.yaml   # contact details, jobs/dates, education, stack keywords
cp cv.example.md cv.md                 # full CV + application answers + work authorization table

# 2. Search
cd search
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m patchright install chromium
cd ..

# 3. PDF rendering
cd .claude/skills/resume-gen && npm install && npx playwright install chromium && cd -

# 4. One-time: replace templates/base-spec.json's placeholder text with your own
#    default resume content (company keys must match profile.yaml experience).
#    Then check the render:
python3 scripts/pipeline/mkspec.py 0-test /dev/stdin <<< '{}'
```

Edit `search/config.yaml` (positions, locations, languages you speak,
`work_authorized_countries`, `max_years_experience`). Two more examples:
`search/config-working-student.example.yaml`, `search/config-europe.example.yaml`.

## Use

```bash
cd search && .venv/bin/python run_search.py --config config.yaml && cd ..
```

The first run opens a browser: log in to LinkedIn once; the profile in
`search/chrome_profile/` keeps you logged in. For applying, copy it so search
and apply never share a profile:

```bash
cp -r search/chrome_profile/linkedin_profile search/chrome_profile/apply_profile
```

Then open Claude Code in the repo root and ask, for example:

> Process the search results and apply to 20 jobs: working student roles in
> Germany first, then full-time in Germany, then the rest of Europe.

Claude follows `.claude/skills/linkedin-job-search/SKILL.md`: refilters and
ranks the queue, screens each job, tailors a resume (and cover letter), applies,
and logs everything in `data/tracker.md`. It will ask you for OTP codes,
security codes, and answers that aren't in `cv.md`.

## License

`search/` derives from [AutoApplyAI](https://github.com/mn3mnn/AutoApplyAI),
itself a fork of AIHawk, under AGPL-3.0 (see `LICENSE`). The rest is new code
under the same license.
