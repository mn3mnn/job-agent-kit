# New in this fork — the reference repo (AutoApplyAI) never needed this,
# since it only ever drives LinkedIn's own Easy Apply flow. We deliberately do
# NOT automate Easy Apply (see README), so for jobs with a plain external
# "Apply" button we need the real destination URL instead.
#
# (Header below predates Easy Apply support; Easy Apply jobs are now kept and
# applied to by the linkedin-job-search skill, this module only classifies.)
#
# LinkedIn's Easy Apply button is `button#jobs-apply-button-id:not([role="link"])`
# (see AutoApplyAI's src/aihawk_easy_applier.py:101) — the `:not([role="link"])`
# implies the external-apply variant of that same id renders as an <a role="link">
# carrying a real href, of the form:
#   https://www.linkedin.com/safety/go/?url=<url-encoded-real-url>&urlhash=...
# so the real destination is just a query param to decode, no navigation needed
# in the common case.

import json
import re
import urllib.parse
from typing import Optional, Tuple

from loguru import logger

APPLY_BUTTON_SELECTOR = "xpath=//*[@id='jobs-apply-button-id']"
EXTERNAL_APPLY_SELECTOR = "a[aria-label='Apply on company website']"
EASY_APPLY_SELECTOR = "button[aria-label^='Easy Apply']"
SAFETY_REDIRECT_HOST = "linkedin.com/safety/go"
APPLICATION_DETAIL_URN_RE = re.compile(r"urn:li:fsd_jobSeekerApplicationDetail:(\d+)")


def _decode_safety_redirect(href: str) -> str:
    if SAFETY_REDIRECT_HOST not in href:
        return href
    parsed = urllib.parse.urlparse(href)
    params = urllib.parse.parse_qs(parsed.query)
    real_url = params.get("url", [None])[0]
    return urllib.parse.unquote(real_url) if real_url else href


class ApplyUrlCache:
    """Passively records each job's apply target from the voyager API
    responses LinkedIn's own frontend already fetches while browsing results
    (the JobSeekerApplicationDetail entity: onsiteApply + companyApplyUrl).

    This replaces clicking the Apply button to see where it leads. The
    external-apply button is now a <button role="link"> with no href, and
    clicking it opens a "Share your profile?" dialog that both blocks every
    later click on the page and, if continued, shares the profile with the
    job poster. Reading the URL from data needs no click at all.
    """

    def __init__(self, page):
        self._details: dict[str, dict] = {}
        page.on("response", self._on_response)

    def _on_response(self, response) -> None:
        if "/voyager/api/" not in response.url:
            return
        try:
            text = response.text()
            if "companyApplyUrl" not in text:
                return
            self._walk(json.loads(text))
        except Exception as e:
            logger.debug(f"Could not read voyager response: {e}")

    def _walk(self, node) -> None:
        if isinstance(node, dict):
            match = APPLICATION_DETAIL_URN_RE.match(str(node.get("entityUrn", "")))
            if match and "companyApplyUrl" in node:
                self._details[match.group(1)] = node
            for value in node.values():
                self._walk(value)
        elif isinstance(node, list):
            for value in node:
                self._walk(value)

    def get(self, job_id: str) -> Optional[dict]:
        return self._details.get(job_id)


def resolve_apply_link(page, job_id: str, cache: ApplyUrlCache) -> Tuple[Optional[str], Optional[str]]:
    """Returns (apply_url, skip_reason). Exactly one is non-None.

    Primary path: the apply target LinkedIn's API reported for this job.
    Fallback path: read the Apply button's href and decode the safety/go
    redirect wrapper if present. The button is never clicked.
    """
    try:
        detail = cache.get(job_id)
        waited_ms = 0
        while detail is None and waited_ms < 5_000:
            page.wait_for_timeout(250)  # also lets queued response handlers run
            waited_ms += 250
            detail = cache.get(job_id)

        if detail is not None:
            if detail.get("applied"):
                return None, "Applied"
            if detail.get("onsiteApply"):
                return None, "Easy Apply"
            if detail.get("companyApplyUrl"):
                return _decode_safety_redirect(detail["companyApplyUrl"]), None

        # Oct 2026 job page (server-driven UI): no stable ids, but the
        # aria-labels are stable: an <a> "Apply on company website" carrying a
        # safety/go href, or a <button> "Easy Apply to this job".
        external = page.locator(EXTERNAL_APPLY_SELECTOR).first
        easy = page.locator(EASY_APPLY_SELECTOR).first
        legacy = page.locator(APPLY_BUTTON_SELECTOR).first
        for _ in range(32):
            if external.count() or easy.count() or legacy.count():
                break
            page.wait_for_timeout(250)

        if page.get_by_text("Application submitted", exact=True).count():
            return None, "Applied"
        if external.count():
            href = external.get_attribute("href")
            return (_decode_safety_redirect(href), None) if href else (None, "external apply url not found")
        if easy.count():
            return None, "Easy Apply"
        if legacy.count() == 0:
            return None, "apply button not found"

        tag = legacy.evaluate("el => el.tagName.toLowerCase()")
        if tag == "a" or legacy.get_attribute("role") == "link":
            href = legacy.get_attribute("href")
            if href:
                return _decode_safety_redirect(href), None
            return None, "external apply url not found"
        return None, "Easy Apply"

    except Exception as e:
        logger.warning(f"Could not resolve apply link: {e}")
        return None, f"error resolving apply link: {e}"


JOB_ID_RE = re.compile(r"/jobs/view/(\d+)")


def extract_job_id(job_link: str) -> Optional[str]:
    match = JOB_ID_RE.search(job_link)
    return match.group(1) if match else None
