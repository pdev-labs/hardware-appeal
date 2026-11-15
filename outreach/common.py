"""Shared loading and validation for the outreach scripts."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
OUTBOX = ROOT / "outbox"
TARGETS = ROOT / "targets" / "targets.json"

KINDS = {"email", "form", "program"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
MAX_VERIFY_AGE_DAYS = 180


class ConfigError(Exception):
    pass


def load_config() -> dict:
    with open(ROOT / "appeal.toml", "rb") as fh:
        cfg = tomllib.load(fh)
    email = cfg.get("identity", {}).get("email", "")
    if not email or "__SET_ME__" in email or "@" not in email:
        raise ConfigError(
            "identity.email in appeal.toml is not set.\n"
            "Run: python3 build.py   (it will tell you what to fill in)"
        )
    if cfg.get("outreach", {}).get("from_email", "").startswith("__SET_ME__"):
        cfg["outreach"]["from_email"] = email
    if cfg.get("outreach", {}).get("reply_to", "").startswith("__SET_ME__"):
        cfg["outreach"]["reply_to"] = email
    return cfg


def load_targets() -> list[dict]:
    data = json.loads(TARGETS.read_text())
    return data["targets"]


def validate(t: dict) -> list[str]:
    """Return a list of reasons this target may not be contacted."""
    problems = []

    for key in ("slug", "org", "kind", "route", "hook", "fit"):
        if not str(t.get(key, "")).strip():
            problems.append(f"missing '{key}'")

    if t.get("slug") and not SLUG.match(t["slug"]):
        problems.append("slug must be lowercase, hyphenated, 2-41 chars")

    if t.get("kind") and t["kind"] not in KINDS:
        problems.append(f"kind must be one of {sorted(KINDS)}")

    # A target is only contactable if a human actually checked the route.
    raw = t.get("verified")
    if not raw:
        problems.append("no 'verified' date — confirm the route, then set it")
    else:
        try:
            when = dt.date.fromisoformat(raw)
        except ValueError:
            problems.append("'verified' must be YYYY-MM-DD")
        else:
            age = (dt.date.today() - when).days
            if age > MAX_VERIFY_AGE_DAYS:
                problems.append(f"route verified {age} days ago — re-check it")
            if age < 0:
                problems.append("'verified' is in the future")

    # No hook, no send. This is what stops a template becoming a blast.
    hook = str(t.get("hook", "")).strip()
    if hook and len(hook.split()) < 8:
        problems.append("'hook' is too thin — write a real, specific sentence")

    if t.get("kind") == "email":
        route = str(t.get("route", ""))
        if "@" not in route or route.startswith("http"):
            problems.append("kind 'email' needs a bare address in 'route'")

    return problems


def today_sends() -> list[dict]:
    log = STATE / "sent.jsonl"
    if not log.exists():
        return []
    today = dt.date.today().isoformat()
    out = []
    for line in log.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(rec.get("ts", "")).startswith(today):
            out.append(rec)
    return out


def last_send() -> dict | None:
    log = STATE / "sent.jsonl"
    if not log.exists():
        return None
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def record(path: pathlib.Path, rec: dict) -> None:
    STATE.mkdir(exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
