# Slimmed down from src/job.py in https://github.com/mn3mnn/AutoApplyAI
# (AGPL-3.0). Dropped every apply/outreach-only field (pdf_path, recruiter_link,
# hiring_team, resume_context) since this fork never applies or reaches out —
# it only searches and records. Added job_id (the reference repo only ever
# derived this transiently, never persisted it) and apply_url/skip_reason,
# which are new to this fork.

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Job:
    job_id: str
    title: str
    company: str
    location: str
    link: str
    apply_method: Optional[str]  # "Applied" | "Easy Apply" | None (= external apply)
    description: str = ""
    apply_url: Optional[str] = None       # resolved external application URL, if any
    skip_reason: Optional[str] = None     # e.g. "Easy Apply" when apply_url is None
    search_position: str = ""
    search_location: str = ""
    scraped_at: str = ""

    def stamp(self) -> None:
        self.scraped_at = datetime.now(timezone.utc).isoformat()

    def to_json_line(self) -> str:
        import json
        return json.dumps(asdict(self), ensure_ascii=False)
