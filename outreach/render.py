#!/usr/bin/env python3
"""Render one draft per verified target.

    python3 render.py                 # every verified target
    python3 render.py --only human-i-t
    python3 render.py --check         # validate, write nothing

Email targets become .eml files ready to review and send one at a time.
Form/program targets become .md briefs to paste into the org's own form,
because those organisations do not accept cold email and pretending
otherwise is how people end up in a spam folder.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

import common

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


def compose(cfg: dict, t: dict, evidence: dict) -> tuple[str, str]:
    """Return (subject, plaintext body) for one target.

    Written as paragraphs and then wrapped at 76 columns, so the delivered
    message has even line lengths instead of the ragged edges that come from
    composing inside an indented f-string.
    """
    ident, hw = cfg["identity"], cfg["hardware"]
    page = f"https://{ident['handle']}.github.io/hardware-appeal/"
    top = evidence["repos"][0]
    blurb = top["blurb"][0].lower() + top["blurb"][1:]

    subject = f"{t['org']}: hardware request from the {top['name']} maintainer"

    paras = [
        f"Hi {t['org']},",
        f"I maintain {top['name']} ({top['url']}) — {blurb} The same profile also "
        f"carries a Rust remote-desktop client and two ESP32-S3 projects.",
        f"My only machine, a {hw['dead_machine']} from {hw['dead_year']}, died this "
        f"month. {hw['dead_note']} I am working from a phone now, and that is the "
        f"ceiling on four active repositories.",
        "I am not asking for a flagship. A refurbished or previous-generation "
        "machine covers everything I need.",
        f"I am writing to you rather than to a general inbox because "
        f"{t['hook'].rstrip('.')}.",
        "The whole case fits on one page, including what I would give back — a "
        f"public build log and an unedited Linux compatibility report:\n\n    {page}",
        f"If this is the wrong address, tell me and I will not write again. If it "
        f"is the right one, I would value a pointer to whoever handles hardware "
        f"donations or developer sponsorship at {t['org']}.",
        f"Thanks for reading,\n{ident['display_name']}\n{ident['profile']}\n{ident['email']}",
        'One message, sent once, to this address. Reply "stop" and you will not '
        "hear from me again. No follow-up unless you answer.",
    ]

    wrapped = "\n\n".join(
        "\n".join(
            textwrap.fill(line, width=76, break_long_words=False, break_on_hyphens=False)
            for line in p.splitlines()
        )
        for p in paras
    )
    return subject, wrapped


def brief(cfg: dict, t: dict, evidence: dict) -> str:
    """A paste-ready brief for orgs that only accept their own web form."""
    _, text = compose(cfg, t, evidence)
    steps = {
        "form": "Open the form and paste the message below into the free-text field.",
        "program": "Read the program rules first. Apply through their process, not by email.",
    }[t["kind"]]

    head = "\n".join([
        f"# {t['org']}",
        "",
        f"- Route: {t['route']}",
        f"- Kind: {t['kind']}",
        f"- Fit: {t['fit']}",
        f"- Verified: {t['verified']}",
        f"- Notes: {t.get('notes', '—')}",
        "",
        steps,
        "",
        "---",
        "",
        "",
    ])
    return head + text + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="render a single slug")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument(
        "--include-low",
        action="store_true",
        help="also draft fit=low targets (they are skipped by default)",
    )
    args = ap.parse_args()

    try:
        cfg = common.load_config()
    except common.ConfigError as exc:
        print(f"{FAIL}  {exc}", file=sys.stderr)
        raise SystemExit(2)

    evidence = json.loads((common.ROOT / "evidence.json").read_text())
    targets = common.load_targets()

    if args.only:
        targets = [t for t in targets if t.get("slug") == args.only]
        if not targets:
            print(f"{FAIL}  no target with slug {args.only!r}", file=sys.stderr)
            raise SystemExit(2)

    common.OUTBOX.mkdir(exist_ok=True)
    blocked = 0
    written = 0

    for t in targets:
        name = t.get("slug") or t.get("org", "?")
        problems = common.validate(t)
        if problems:
            blocked += 1
            print(f"{SKIP}  {name}: " + "; ".join(problems))
            continue

        if t.get("fit") == "low" and not args.include_low and not args.check:
            blocked += 1
            print(f"{SKIP}  {name}: fit is low — skipped (see notes, or --include-low)")
            continue

        if args.check:
            print(f"{PASS}  {name}: route ok ({t['kind']} → {t['route']})")
            continue

        if t["kind"] == "email":
            subject, text = compose(cfg, t, evidence)
            msg = EmailMessage()
            domain = cfg["outreach"]["from_email"].split("@")[-1]
            msg["From"] = f"{cfg['outreach']['from_name']} <{cfg['outreach']['from_email']}>"
            msg["To"] = t["route"]
            msg["Reply-To"] = cfg["outreach"]["reply_to"]
            msg["Subject"] = subject
            msg["Date"] = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid(domain=domain)
            msg["List-Unsubscribe"] = (
                f"<mailto:{cfg['identity']['email']}?subject=unsubscribe>"
            )
            msg.set_content(text)
            path = common.OUTBOX / f"{t['slug']}.eml"
            path.write_bytes(bytes(msg))
        else:
            path = common.OUTBOX / f"{t['slug']}.md"
            path.write_text(brief(cfg, t, evidence))

        written += 1
        print(f"{PASS}  {name}: {path.relative_to(common.ROOT)}")

    print()
    print(f"      {written} drafted, {blocked} blocked.")
    if written:
        print("      Review each file. Then, one at a time:")
        print("        python3 send.py outbox/<slug>.eml")
        print("      That prints the message and stops. Add --yes to transmit.")


if __name__ == "__main__":
    main()
