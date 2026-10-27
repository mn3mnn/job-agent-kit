"""Shared helpers for the pipeline scripts: repo paths, profile, jobs, tracker."""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "search"))
sys.path.insert(0, str(ROOT / "scripts"))

import tracker  # noqa: E402


def profile() -> dict:
    p = ROOT / "profile.yaml"
    if not p.exists():
        sys.exit("profile.yaml not found: copy profile.example.yaml and fill it in")
    return yaml.safe_load(p.read_text())


def search_config(name: str = "config.yaml") -> dict:
    return yaml.safe_load((ROOT / "search" / name).read_text())


def jobs() -> dict:
    """job_id -> job dict from search/output/jobs.jsonl (tolerates partial lines)."""
    out = {}
    path = ROOT / "search" / "output" / "jobs.jsonl"
    if not path.exists():
        return out
    for line in path.open():
        try:
            j = json.loads(line)
            out[j["job_id"]] = j
        except (json.JSONDecodeError, KeyError):
            continue
    return out
