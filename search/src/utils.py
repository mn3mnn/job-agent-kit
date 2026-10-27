# Ported from https://github.com/mn3mnn/AutoApplyAI (AGPL-3.0), itself a fork of
# AIHawk by feder-cr. Only the search/anti-detection helpers are used here; the
# apply/LLM/outreach parts of that codebase are intentionally not reused.
#
# This module keeps the same "look like a real human browsing" behavior the
# search step relies on: a headed, persistent Chromium profile plus slow,
# jittered scrolling. It is deliberately simpler than the source (no
# app_config.py indirection) since this repo only ever runs the search path.

import os
import random
import sys
import time

from loguru import logger

logger.remove()
logger.add(sys.stderr, level=os.environ.get("LOG_LEVEL", "INFO"))

CHROME_PROFILE_PATH = os.path.join(os.getcwd(), "chrome_profile", "linkedin_profile")


def ensure_chrome_profile() -> str:
    profile_dir = os.path.dirname(CHROME_PROFILE_PATH)
    os.makedirs(profile_dir, exist_ok=True)
    os.makedirs(CHROME_PROFILE_PATH, exist_ok=True)
    return CHROME_PROFILE_PATH


def browser_launch_options() -> dict:
    """kwargs for patchright chromium.launch_persistent_context().

    headless=False is deliberate, not an oversight: running headed is part of
    the anti-detection posture this whole search step relies on (see README).
    """
    ensure_chrome_profile()
    return dict(
        headless=False,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    )


def is_scrollable(locator) -> bool:
    scroll_height = locator.evaluate("el => el.scrollHeight")
    client_height = locator.evaluate("el => el.clientHeight")
    return int(scroll_height) > int(client_height)


def scroll_slow(locator, start=0, end=3600, step=300, reverse=False) -> None:
    """Human-like incremental scroll with jittered pauses. Ported as-is from
    the reference repo's src/utils.py:scroll_slow (patchright variant) — this
    is one of the specific behaviors the reference tool uses to avoid looking
    like a scripted crawler, so it's preserved wholesale."""
    if reverse:
        start, end = end, start
        step = -step
    if step == 0:
        raise ValueError("step cannot be zero")

    try:
        if not locator.is_visible() or not is_scrollable(locator):
            return

        max_scroll_height = int(locator.evaluate("el => el.scrollHeight"))
        current_position = int(float(locator.evaluate("el => el.scrollTop")))

        if reverse:
            if current_position < start:
                start = current_position
        elif end > max_scroll_height:
            end = max_scroll_height

        if (step > 0 and start >= end) or (step < 0 and start <= end):
            return

        position = start
        previous_position = None
        while (step > 0 and position < end) or (step < 0 and position > end):
            if position == previous_position:
                break
            try:
                locator.evaluate(f"el => {{ el.scrollTop = {position}; }}")
            except Exception as e:
                logger.debug(f"Scroll step failed: {e}")
            previous_position = position
            position += step
            step = max(10, abs(step) - 10) * (-1 if reverse else 1)
            time.sleep(random.uniform(0.6, 1.5))

        locator.evaluate(f"el => {{ el.scrollTop = {end}; }}")
        time.sleep(0.5)
    except Exception as e:
        logger.debug(f"scroll_slow failed: {e}")


def jitter_sleep(low: float, high: float) -> None:
    time.sleep(random.uniform(low, high))
