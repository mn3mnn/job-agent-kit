#!/usr/bin/env python3
"""Render a tailored resume (and optional cover letter) from a JSON spec.

Usage: build_resume.py <spec.json>
Writes resume.html + <pdf_name> (and cover_letter.html + cover-letter PDF when
the spec has a "cover_letter" key) next to the spec.

Layout and CSS live in templates/resume-style.html. Candidate facts (contact
details, job titles/dates, education, certifications) come from profile.yaml
at the repo root; the spec only carries the tailored text.

Spec keys:
  summary        str
  jobs           {company: [bullets]} in the order to print them; companies
                 must be keys of profile.yaml's `experience`. Omit one to drop it.
  project        str description, or null to omit
  project_tech   str (optional)
  skills         [[category, items], ...]
  header_location, pdf_name, masters_note (optional)
  cover_letter   {"role": str, "company": str, "greeting": str,
                  "paragraphs": [str, ...]} (optional)
"""
import datetime, html, json, subprocess, sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROFILE_PATH = ROOT / "profile.yaml"
if not PROFILE_PATH.exists():
    sys.exit(f"{PROFILE_PATH} not found: copy profile.example.yaml to profile.yaml and fill it in")
PROFILE = yaml.safe_load(PROFILE_PATH.read_text())
C = PROFILE["candidate"]
C["name"] = f'{C["first_name"]} {C["last_name"]}'
e = html.escape
FORBIDDEN = ("—", "–", "→", "←")


def contact_row(location: str) -> str:
    tel = "".join(ch for ch in C["phone"] if ch.isdigit() or ch == "+")
    return f"""<a href="tel:{tel}">{e(C["phone"])}</a>
      <span class="separator">|</span>
      <a href="mailto:{C["email"]}">{e(C["email"])}</a>
      <span class="separator">|</span>
      <a href="https://{C["linkedin"]}">{e(C["linkedin"])}</a>
      <span class="separator">|</span>
      <a href="https://{C["github"]}">{e(C["github"])}</a>
      <span class="separator">|</span>
      <span>{e(location)}</span>"""


def render(out_html: Path, out_pdf: Path, text: str) -> int:
    for bad in FORBIDDEN:
        if bad in text:
            sys.exit(f"forbidden character {bad!r} in {out_html.name}")
    out_html.write_text(text)
    r = subprocess.run(["node", str(HERE / "generate-pdf.mjs"), str(out_html), str(out_pdf),
                        "--format=a4", "--max-pages=1", "--strict-pages"], capture_output=True, text=True)
    print(r.stdout[-400:], r.stderr[-400:])
    return r.returncode


def education_html(spec: dict) -> str:
    out = ""
    for i, ed in enumerate(PROFILE.get("education", [])):
        note = spec.get("masters_note", ed.get("note", "")) if i == 0 else ed.get("note", "")
        desc = f'\n      <div class="edu-desc">{e(note)}</div>' if note else ""
        out += f"""    <div class="edu-item">
      <div class="edu-header">
        <div class="edu-title">{e(ed["title"])} <span class="edu-org">{e(ed["org"])}</span></div>
        <div class="edu-year">{e(ed["period"])}</div>
      </div>{desc}
    </div>
"""
    return out


def certs_html() -> str:
    return "".join(f"""<div class="cert-item">
      <span class="cert-title">{e(c["title"])}</span>
      <span class="cert-org">{e(c["org"])}</span>
      <span class="cert-year">{e(str(c["year"]))}</span>
    </div>""" for c in PROFILE.get("certifications", []))


def resume_body(spec: dict) -> str:
    jobs_html = ""
    for company, bullets in spec["jobs"].items():
        job = PROFILE["experience"][company]
        period, role, loc = job["period"], job["role"], job["location"]
        lis = "\n".join(f"        <li>{e(b)}</li>" for b in bullets)
        jobs_html += f"""    <div class="job">
      <div class="job-header">
        <span class="job-company">{e(company)}</span>
        <span class="job-period">{period}</span>
      </div>
      <div class="job-role">{e(role)}</div>
      <div class="job-location">{loc}</div>
      <ul>
{lis}
      </ul>
    </div>
"""
    project_html = ""
    proj = PROFILE.get("project")
    if spec.get("project") and proj:
        project_html = f"""  <div class="section">
    <div class="section-title">Projects</div>
    <div class="project">
      <div class="project-title">{e(proj["title"])}<span class="project-badge">{e(proj.get("badge", ""))}</span></div>
      <div class="project-desc">{e(spec["project"])}</div>
      <div class="project-tech">{e(spec.get("project_tech", proj.get("default_tech", "")))}</div>
    </div>
  </div>
"""
    skills_html = "\n".join(
        f'    <div class="skill-item"><span class="skill-category">{e(cat)}: </span>{e(items)}</div>'
        for cat, items in spec["skills"])
    return f"""<body>
<div class="page">
  <div class="header">
    <h1>{e(C["name"])}</h1>
    <div class="header-gradient"></div>
    <div class="contact-row">
      {contact_row(spec.get("header_location", C["header_location"]))}
    </div>
  </div>
  <div class="section">
    <div class="section-title">Professional Summary</div>
    <div class="summary-text">{e(spec["summary"])}</div>
  </div>
  <div class="section">
    <div class="section-title">Work Experience</div>
{jobs_html}  </div>
{project_html}  <div class="section">
    <div class="section-title">Education</div>
{education_html(spec)}  </div>
  <div class="section">
    <div class="section-title">Certifications</div>
    <div class="cert-table">{certs_html()}</div>
  </div>
  <div class="section">
    <div class="section-title">Skills</div>
{skills_html}
  </div>
</div>
</body>
</html>
"""


def cover_letter_body(spec: dict) -> str:
    cl = spec["cover_letter"]
    today = datetime.date.today().strftime("%d %B %Y").lstrip("0")
    paras = "\n".join(f'    <p class="cl-p">{e(p)}</p>' for p in cl["paragraphs"])
    return f"""<body>
<div class="page">
  <div class="header">
    <h1>{e(C["name"])}</h1>
    <div class="header-gradient"></div>
    <div class="contact-row">
      {contact_row(spec.get("header_location", C["header_location"]))}
    </div>
  </div>
  <div class="section">
    <div class="section-title">{e(cl["role"])}, {e(cl["company"])}</div>
    <p class="cl-p cl-date">{today}</p>
    <p class="cl-p">{e(cl.get("greeting", "Hello " + cl["company"] + " team,"))}</p>
{paras}
    <p class="cl-p">Best regards,<br>{e(C["name"])}</p>
  </div>
</div>
</body>
</html>
"""


def main() -> None:
    spec_path = Path(sys.argv[1]).resolve()
    spec = json.loads(spec_path.read_text())
    head = (HERE / "templates" / "resume-style.html").read_text()
    head = head[: head.index("<body>")]
    out = spec_path.parent
    rc = render(out / "resume.html", out / spec.get("pdf_name", PROFILE.get("resume_pdf_name", "Resume.pdf")), head + resume_body(spec))
    if spec.get("cover_letter"):
        cl_head = head.replace("</style>", "  .cl-p { font-size: 11.5px; line-height: 1.6; margin: 0 0 11px; color: #222; }\n  .cl-date { color: #777; }\n</style>")
        rc |= render(out / "cover_letter.html", out / PROFILE.get("cover_letter_pdf_name", "Cover_Letter.pdf"), cl_head + cover_letter_body(spec))
    sys.exit(rc)


if __name__ == "__main__":
    main()
