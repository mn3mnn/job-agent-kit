# Ported near-verbatim from src/aihawk_authenticator.py in
# https://github.com/mn3mnn/AutoApplyAI (AGPL-3.0). Unmodified in behavior:
# there are no stored LinkedIn credentials anywhere in this repo. Login is
# always a human solving it once in the visible browser window; this class
# just polls for the redirect to /feed (and waits out a security checkpoint if
# LinkedIn shows one), then the persistent Chromium profile keeps the session
# alive across future runs.

import time

from patchright.sync_api import TimeoutError as PWTimeoutError
from loguru import logger


class Authenticator:

    def __init__(self, page):
        self.page = page

    def start(self) -> None:
        logger.info("Checking LinkedIn login state.")
        if self.is_logged_in():
            logger.info("Already logged in.")
            return
        logger.info("Not logged in. Please log in in the browser window.")
        self.handle_login()

    def handle_login(self) -> None:
        self.page.goto("https://www.linkedin.com/login")
        if "feed" in self.page.url:
            return
        try:
            self._wait_for_manual_login()
        except Exception as e:
            logger.error(f"Login did not complete: {e}")
        self._handle_security_check()

    def _wait_for_manual_login(self, check_interval: int = 4) -> None:
        while True:
            current_url = self.page.url
            logger.info(f"Waiting for manual login on {current_url}")
            if "feed" in current_url:
                logger.info("Login successful.")
                break
            try:
                self.page.locator("#password").wait_for(timeout=10_000)
            except PWTimeoutError:
                pass
            time.sleep(check_interval)

    def _handle_security_check(self) -> None:
        try:
            self.page.wait_for_url("**/checkpoint/challengesV2/**", timeout=10_000)
            logger.warning("Security checkpoint shown. Please complete it manually.")
            self.page.wait_for_url("**/feed/**", timeout=300_000)
            logger.info("Security check completed.")
        except PWTimeoutError:
            pass  # no checkpoint appeared, or /feed was already reached

    def is_logged_in(self) -> bool:
        try:
            self.page.goto("https://www.linkedin.com/feed")
            self.page.locator(".share-box-feed-entry__trigger").wait_for(timeout=3_000)
            buttons = self.page.locator(".share-box-feed-entry__trigger").all()
            if any(b.inner_text().strip().lower() == "start a post" for b in buttons):
                return True
            profile_imgs = self.page.locator("xpath=//img[contains(@alt, 'Photo of')]").all()
            return bool(profile_imgs)
        except PWTimeoutError:
            return False
