"""Build a tailored spec from templates/base-spec.json plus overrides, then render it.

Usage: mkspec.py <job_id>-<key> <overrides.json>
Overrides replace top-level keys (summary, skills, project, cover_letter, ...);
"jobs_patch": {company: [bullets]} replaces bullets for just those companies.
Writes .claude/skills/resume-gen/output/<job_id>-<key>/ and copies the resume
PDF to <Resume name>_<key>.pdf so upload dialogs show a job-specific filename.
"""
import json
import subprocess
import sys

from _common import ROOT, profile

G = ROOT / ".claude" / "skills" / "resume-gen"
name, ov_path = sys.argv[1], sys.argv[2]
key = name.split("-", 1)[1]
out = G / "output" / name
out.mkdir(parents=True, exist_ok=True)
spec = json.loads((G / "templates" / "base-spec.json").read_text())
for k, v in json.loads(open(ov_path).read()).items():
    if k == "jobs_patch":
        spec["jobs"].update(v)
    else:
        spec[k] = v
(out / "spec.json").write_text(json.dumps(spec, indent=1))
r = subprocess.run([sys.executable, str(G / "build_resume.py"), str(out / "spec.json")], capture_output=True, text=True)
p = profile()
pdf = p.get("resume_pdf_name", "Resume.pdf")
if "Pages: 1" in r.stdout and (out / pdf).exists():
    tagged = out / pdf.replace(".pdf", f"_{key}.pdf")
    tagged.write_bytes((out / pdf).read_bytes())
    cl = out / p.get("cover_letter_pdf_name", "Cover_Letter.pdf")
    if cl.exists():
        (out / cl.name.replace(".pdf", f"_{key}.pdf")).write_bytes(cl.read_bytes())
    print("OK", tagged.relative_to(ROOT))
else:
    print("FAIL", name, r.stdout[-300:], r.stderr[-300:])
    sys.exit(1)
