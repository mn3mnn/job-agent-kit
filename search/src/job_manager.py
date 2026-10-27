# Trimmed, bugfixed port of the SEARCH-ONLY path of
# src/aihawk_job_manager.py (AutoApplyAI, AGPL-3.0) — specifically the code
# reachable from AIHawkJobManager.start_collecting_data(), which never touches
# the apply/LLM/GPT-answerer machinery. Everything apply-related
# (start_applying, apply_jobs, the resume/LLM plumbing in set_parameters) was
# left behind on purpose.
#
# Two deliberate differences from the source, both intentional (not bugs to
# preserve):
#   1. get_base_search_url() drops the hardcoded `f_LF=f_AL` (Easy-Apply-only)
#      filter. The source always restricted results to Easy Apply jobs; this
#      fork exists specifically to find the OTHER kind (external "Apply"
#      links), so keeping that filter would hide exactly what we want.
#   2. The `experienceLevel` config key is read correctly (the source reads
#      `experience_level`, a snake_case key that plain never appears in
#      config.yaml, so the filter was always silently a no-op upstream).
#
# Also new here: listings and descriptions come from LinkedIn's guest job API
# (src/guest_search.py) since the logged-in search page moved to an AI-search
# UI in Oct 2026; eligibility filters (src/filters.py) run on each
# description, and only surviving jobs are opened in the browser to resolve
# the apply target (external URL vs Easy Apply).

import urllib.parse
from itertools import product

from loguru import logger

from src import utils
from src.apply_link import ApplyUrlCache, resolve_apply_link
from src.filters import eligibility_skip_reason
from src.guest_search import job_description, search_cards
from src.job import Job

class JobManager:
    def __init__(self, page):
        self.page = page
        self.seen_job_ids: set[str] = set()
        self.apply_urls = ApplyUrlCache(page)

    def set_parameters(self, parameters: dict) -> None:
        self.company_blacklist = [s.lower() for s in parameters.get("company_blacklist", []) or []]
        self.title_blacklist = [s.lower() for s in parameters.get("title_blacklist", []) or []]
        self.location_blacklist = [s.lower() for s in parameters.get("location_blacklist", []) or []]
        self.max_pages = parameters.get("max_pages")
        self.parameters = parameters
        self.positions = parameters.get("positions", [])
        self.locations = parameters.get("locations", [])
        self.base_search_url = self._get_base_search_url(parameters)

    # -- search URL / pagination -----------------------------------------

    def _get_base_search_url(self, parameters: dict) -> str:
        url_parts = []
        if parameters.get("remote"):
            url_parts.append("f_CF=f_WRA")
            url_parts.append("f_WT=2")

        experience_level = parameters.get("experienceLevel", {}) or {}
        experience_index = {
            "internship": 1, "entry": 2, "associate": 3,
            "mid-senior level": 4, "director": 5, "executive": 6,
        }
        levels = [str(experience_index[level]) for level, on in experience_level.items() if on and level in experience_index]
        if levels:
            url_parts.append(f"f_E={','.join(levels)}")

        url_parts.append(f"distance={parameters.get('distance', 25)}")

        job_types = parameters.get("jobTypes", {}) or {}
        type_codes = [key[0].upper() for key, on in job_types.items() if on]
        if type_codes:
            url_parts.append(f"f_JT={','.join(type_codes)}")

        date_mapping = {
            "all time": "", "month": "&f_TPR=r2592000",
            "week": "&f_TPR=r604800", "24 hours": "&f_TPR=r86400",
        }
        date_param = next((v for k, v in date_mapping.items() if parameters.get("date", {}).get(k)), "")

        base_url = "&".join(url_parts)
        return f"?{base_url}{date_param}"

    def _is_blacklisted(self, job: Job) -> bool:
        title_hit = any(w in job.title.lower() for w in self.title_blacklist)
        company_hit = job.company.strip().lower() in self.company_blacklist
        location_hit = job.location.strip().lower() in self.location_blacklist
        return title_hit or company_hit or location_hit

    # -- apply target (logged-in browser) ----------------------------------

    def _resolve_apply(self, job: Job) -> None:
        """Open the job page so ApplyUrlCache sees LinkedIn's own API response,
        then classify: external URL, Easy Apply (kept, applied in-LinkedIn), or
        already applied."""
        try:
            self.page.goto(job.link)
        except Exception as e:
            job.skip_reason = f"could not open job page: {e}"
            return
        apply_url, reason = resolve_apply_link(self.page, job.job_id, self.apply_urls)
        if reason == "Easy Apply":
            job.apply_method = "Easy Apply"
            job.apply_url = job.link
        elif reason == "Applied":
            job.apply_method = "Applied"
            job.skip_reason = "Applied"
        else:
            job.apply_url = apply_url
            job.skip_reason = reason

    # -- top-level search loop ----------------------------------------------

    def collect(self, writer) -> None:
        """Search every (position, location) pair through the guest API and
        pass each Job to writer(job) as soon as it's ready. max_pages counts
        25-job pages, as before. Requests are jittered to stay human-paced."""
        import random

        searches = list(product(self.positions, self.locations))
        random.shuffle(searches)
        request = self.page.request

        for position, location in searches:
            logger.info(f"Searching '{position}' in '{location}'")
            start, found = 0, 0
            while not (self.max_pages and start >= self.max_pages * 25):
                try:
                    cards = search_cards(request, self.base_search_url, urllib.parse.quote(position),
                                         urllib.parse.quote(location), start)
                except Exception as e:
                    logger.warning(f"Search page failed ({e}); moving on.")
                    break
                if not cards:
                    break
                start += len(cards)
                for card in cards:
                    if card["job_id"] in self.seen_job_ids:
                        continue
                    self.seen_job_ids.add(card["job_id"])
                    job = Job(link=f"https://www.linkedin.com/jobs/view/{card['job_id']}/", apply_method=None,
                              search_position=position, search_location=location, **card)
                    found += 1
                    if self._is_blacklisted(job):
                        job.skip_reason = "blacklisted"
                    else:
                        job.description = job_description(request, job.job_id)
                        utils.jitter_sleep(1.0, 2.5)
                        job.skip_reason = eligibility_skip_reason(job, self.parameters)
                        if not job.skip_reason:
                            self._resolve_apply(job)
                            utils.jitter_sleep(2.0, 4.0)
                    job.stamp()
                    writer(job)
                utils.jitter_sleep(2.0, 5.0)
            logger.info(f"  {found} new job(s)")
