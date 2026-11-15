#!/usr/bin/env python3
"""Send exactly one drafted message, after you have read it.

    python3 send.py outbox/human-i-t.eml        # print and stop
    python3 send.py outbox/human-i-t.eml --yes  # transmit

Deliberate limits, all enforced here rather than trusted to you:

  * one file per invocation — no batch mode, no glob expansion
  * a hard daily cap (outreach.daily_cap, default 5)
  * a minimum gap between sends (outreach.min_gap_min, default 20)
  * a refusal to send anything that is not a validated target
  * plain text only, and it must already contain the opt-out line

Credentials come from the environment, never from a file:

    export SMTP_USER='you@example.com'
    export SMTP_PASS='app-password'
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import smtplib
import sys
import textwrap
from email import message_from_bytes
from email.policy import default as default_policy

import common

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("eml", help="one .eml file from outbox/")
    ap.add_argument("--yes", action="store_true", help="actually transmit")
    args = ap.parse_args()

    try:
        cfg = common.load_config()
    except common.ConfigError as exc:
        print(f"{FAIL}  {exc}", file=sys.stderr)
        raise SystemExit(2)

    path = pathlib.Path(args.eml)
    if not path.is_absolute():
        # resolve against the shell's cwd first, then the repo root
        cwd_candidate = pathlib.Path.cwd() / path
        path = cwd_candidate if cwd_candidate.exists() else common.ROOT / path
    if path.suffix != ".eml":
        print(f"{FAIL}  {path.name} is not an .eml draft. Form briefs are pasted, not sent.",
              file=sys.stderr)
        raise SystemExit(2)
    if not path.exists():
        print(f"{FAIL}  no such draft: {path}", file=sys.stderr)
        raise SystemExit(2)

    msg = message_from_bytes(path.read_bytes(), policy=default_policy)
    slug = path.stem

    # The draft must correspond to a still-valid target.
    target = next((t for t in common.load_targets() if t.get("slug") == slug), None)
    if target is None:
        print(f"{FAIL}  {slug} is not in targets.json — refusing to send.", file=sys.stderr)
        raise SystemExit(2)
    problems = common.validate(target)
    if problems:
        print(f"{FAIL}  target no longer valid: " + "; ".join(problems), file=sys.stderr)
        raise SystemExit(2)

    text = msg.get_content()
    if "stop" not in text.lower():
        print(f"{FAIL}  draft has no opt-out line — refusing to send.", file=sys.stderr)
        raise SystemExit(2)

    to_addr = str(msg["To"])
    subject = str(msg["Subject"])

    # Rate limits.
    sent_today = common.today_sends()
    cap = int(cfg["outreach"].get("daily_cap", 5))
    if len(sent_today) >= cap:
        print(f"{FAIL}  daily cap reached ({len(sent_today)}/{cap}). Try tomorrow.", file=sys.stderr)
        raise SystemExit(3)

    gap = int(cfg["outreach"].get("min_gap_min", 20))
    previous = common.last_send()
    if previous:
        try:
            last = dt.datetime.fromisoformat(previous["ts"])
        except (KeyError, ValueError):
            last = None
        if last:
            elapsed = (dt.datetime.now(dt.timezone.utc) - last.astimezone(dt.timezone.utc))
            if elapsed < dt.timedelta(minutes=gap):
                wait = gap - int(elapsed.total_seconds() // 60)
                print(f"{FAIL}  last send was {int(elapsed.total_seconds() // 60)} min ago. "
                      f"Wait {wait} more min.", file=sys.stderr)
                raise SystemExit(3)

    if any(rec.get("slug") == slug for rec in _all_sends()):
        print(f"{FAIL}  {slug} was already sent. One message per organisation.", file=sys.stderr)
        raise SystemExit(3)

    print(f"  to      {to_addr}")
    print(f"  subject {subject}")
    print(f"  from    {cfg['outreach']['from_email']}")
    print(f"  quota   {len(sent_today)}/{cap} sent today")
    print()
    print(textwrap_indent(text))
    print()

    if not args.yes:
        print(f"{WARN}  not sent. Re-run with --yes to transmit.")
        return

    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    if not user or not password:
        print(f"{FAIL}  set SMTP_USER and SMTP_PASS in the environment first.", file=sys.stderr)
        raise SystemExit(2)

    host = cfg["outreach"].get("smtp_host", "smtp.gmail.com")
    port = int(cfg["outreach"].get("smtp_port", 587))

    try:
        with smtplib.SMTP(host, port, timeout=45) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        print(f"{FAIL}  send failed: {exc}", file=sys.stderr)
        common.STATE.mkdir(exist_ok=True)
        common.record(common.STATE / "failed.jsonl", {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "slug": slug, "to": to_addr, "error": str(exc),
        })
        raise SystemExit(4)

    common.record(common.STATE / "sent.jsonl", {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "slug": slug,
        "to": to_addr,
        "subject": subject,
        "message_id": str(msg["Message-ID"]),
    })
    print(f"{PASS}  sent. Logged to state/sent.jsonl. That is {len(sent_today) + 1}/{cap} today.")


def _all_sends() -> list[dict]:
    log = common.STATE / "sent.jsonl"
    if not log.exists():
        return []
    out = []
    for line in log.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def textwrap_indent(text: str) -> str:
    return "\n".join("  │ " + line for line in text.splitlines())


if __name__ == "__main__":
    main()
