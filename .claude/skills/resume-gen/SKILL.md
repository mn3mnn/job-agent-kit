---
name: resume-gen
description: Generate a one-page, ATS-safe, tailored resume PDF in the style of the candidate's reference resume (plus a short, natural cover letter whenever the application has a place for one) from cv.md and a job description. Use when linkedin-job-search needs a tailored resume for a job it decided to pursue, or when invoked directly with a job description and a cv.md path.
---

# Resume Generation

Read `cv.md` as the only source of truth, map its facts onto the job
description's language, keep it to one page, and never invent a skill the
candidate doesn't have.

## Inputs

- `cv_md_path` — the candidate's CV (`cv.md` at the repo root; see
  `cv.example.md` for the shape).
- `profile.yaml` (repo root) — contact details, job titles/dates, education,
  certifications and the default header location. build_resume.py reads it;
  never hardcode personal details anywhere else.
- `header_location` — optional per-application override of the header
  location (city and country only, never a street address).
- `job` — title, company, location, and full description text of the target
  posting.
- `cover_letter_required` — boolean. True whenever the posting asks for one or
  the application form has a cover-letter field/upload or a free-text message
  box (Easy Apply often does). Follow `templates/cover-letter-base.md`.

## Hard rules (non-negotiable, not just a style preference)

1. **Never fabricate.** Every skill, tool, and claim in the output must trace
   back to `cv.md` or to something the invoking context explicitly confirmed
   as true for this run (e.g. "the candidate confirmed real TypeScript
   experience not yet in cv.md"). If a job's requirement isn't backed by
   `cv.md` and nothing in the current run confirms it, leave it out — do not
   guess, and do not silently add it to close the gap. At most a handful of
   clearly-labeled new keywords may be added per resume, and only when the
   invoking context has explicitly said this specific fact is true; if that
   confirmation isn't available, skip the keyword and note the gap instead of
   inventing one.
   **ATS keyword exception:** to raise ATS match,
   you may add up to 4 of the job description's own keywords to the Skills
   section when they are a close neighbour of something in cv.md (e.g.
   "CI/CD" from GitHub Actions, "Microservices architecture", "REST API
   design", "SQL databases", "Cloud (AWS/Azure)", "Event-driven architecture"
   from RabbitMQ, "Observability" from ELK/OpenTelemetry). Use the JD's exact
   spelling. Never add an unrelated language/framework (no Java, TypeScript,
   React, Kotlin, etc. unless cv.md has it) and never put new keywords into
   bullets as achievements. List added keywords in the report.
   If the candidate lists tools in cv.md they only want shown when a job asks
   for them, note that in cv.md and respect it.
2. **No "Core Competencies" section.** Skip straight from Professional Summary
   to Work Experience. The Skills section, summary and bullets already carry
   the keywords.
3. **No em dashes, en dashes rendered as such, or arrow characters anywhere**
   in generated text — use commas, periods, colons, or "and" to join clauses,
   and "to"/"from" instead of arrows. `generate-pdf.mjs`'s ATS normalization
   pass will silently rewrite these if they slip through, but write it
   correctly at the source; don't rely on the safety net.
4. **One page.** Always render with `--max-pages=1 --strict-pages`. If it
   overflows, trim in this order before touching wording: (a) drop the
   least-relevant bullet from the oldest/least-relevant job, (b) shorten the
   project description, (c) merge short bullets in the same job with "and",
   (d) tighten the summary by one clause. Re-render after every trim.
5. **Reformulate, don't reorder-and-pad.** Emphasize the parts of `cv.md` that
   match the job description's language; don't change the underlying facts.

## Procedure

1. Read `cv_md_path`. This is the only factual source for experience,
   education, certifications, and default skills.
2. Read the job description. Identify: the 3-5 requirements that matter most,
   any hard disqualifiers (location, language, a specific required stack the
   candidate lacks), and language the posting itself uses (mirror it in the
   summary/bullets where honest to do so).
3. Draft the Professional Summary: 3-5 sentences, leading with the single
   strongest matching proof point from `cv.md`, written in the job's own
   vocabulary where that's a genuine fit and not a stretch.
4. Reorder/rephrase Work Experience bullets per role to foreground what's
   relevant to this job; keep every role, keep reverse-chronological order,
   keep all facts and numbers exactly as `cv.md` states them.
5. Include Projects only if at least one is genuinely relevant; trim its
   description to the parts that map onto the job.
6. Keep Education, Certifications, and Skills close to `cv.md` as-is; you may
   reorder Skills categories to put the most relevant ones first, and append
   at most a handful of clearly novel items per rule 1.
7. Start from `templates/base-spec.json`. On first use, replace its
   placeholder text with the candidate's own default resume content from
   cv.md (company keys must match `experience` in profile.yaml). Copy it to
   `output/<job_id>-<company-slug>/spec.json` and edit only: `summary`, the
   bullets inside `jobs` (and their order; companies may be reordered),
   `project`, and `skills`. Contact details always come from profile.yaml.
8. Render: `python3 .claude/skills/resume-gen/build_resume.py <spec.json>`. It
   writes resume.html and the resume PDF (name from profile.yaml, strict one page) and
   refuses em/en dashes and arrows. On overflow, trim per rule 4 and re-run.
9. If `cover_letter_required`, add a `cover_letter` object to the same spec
   (`role`, `company`, optional `greeting`, `paragraphs`) written from
   `templates/cover-letter-base.md`; the same command renders the cover
   letter PDF. Keep the plain text handy for pasting
   into message boxes.
10. Report back: the resume PDF path (and cover letter PDF path, if made),
    plus a one-line note of anything from the job description you could not
    honestly address (a real gap, not something to paper over).

## Verification

- build_resume.py exits non-zero on forbidden characters or overflow; confirm
  it printed `Pages: 1` for each PDF.
- Read the PDF back once and skim it for typos and any claim not in cv.md.
