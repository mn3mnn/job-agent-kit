# Job Agent Kit

Find jobs on LinkedIn, tailor a one-page resume and a short cover letter for
each, and apply through LinkedIn Easy Apply or the company's own ATS, driven
by [Claude Code](https://claude.com/claude-code) and `playwright-cli`.

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
