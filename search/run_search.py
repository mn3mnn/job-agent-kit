#!/usr/bin/env python3
"""Search-only entrypoint. Deliberately does NOT reuse
Auto_Jobs_Applier_AIHawk's main.py / AIHawkBotFacade / create_and_run_bot(),
since those unconditionally construct the LLM/resume-builder stack even in
"collect" mode. This wires only what the search path actually needs:
Authenticator -> JobManager -> JsonlWriter.

Usage:
    pip install -r requirements.txt
    python run_search.py                  # uses config.yaml
    python run_search.py --config other.yaml
"""

import json
import sys
from pathlib import Path

import click
import yaml
from loguru import logger
from patchright.sync_api import sync_playwright

from src import utils
from src.authenticator import Authenticator
from src.job_manager import JobManager
from src.jsonl_writer import JsonlWriter

REPO_ROOT = Path(__file__).resolve().parent


@click.command()
@click.option("--config", default="config.yaml", help="Path to search config.yaml")
def main(config: str) -> None:
    config_path = REPO_ROOT / config
    if not config_path.exists():
        logger.error(f"Config not found: {config_path}")
        sys.exit(1)

    parameters = yaml.safe_load(config_path.read_text())
    output_path = REPO_ROOT / parameters.get("output_path", "output/jobs.jsonl")

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            utils.ensure_chrome_profile(), **utils.browser_launch_options()
        )
        page = context.pages[0] if context.pages else context.new_page()

        Authenticator(page).start()

        manager = JobManager(page)
        manager.set_parameters(parameters)
        if output_path.exists():
            # don't re-open jobs an earlier run already recorded
            for line in output_path.read_text(encoding="utf-8").splitlines():
                try:
                    manager.seen_job_ids.add(json.loads(line)["job_id"])
                except (json.JSONDecodeError, KeyError):
                    continue  # blank or partially written line

        writer = JsonlWriter(output_path)
        try:
            manager.collect(writer)
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
        finally:
            writer.close()
            context.close()

    logger.info(f"Done. Results in {output_path}")


if __name__ == "__main__":
    main()
