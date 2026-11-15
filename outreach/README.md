# Outreach — how this is meant to be used

This is not a mailer. It is a review pipeline with a handbrake.

```
targets/targets.json  →  render.py  →  outbox/*.eml  →  you read it  →  send.py --yes
```

The chain is deliberately friction-heavy in three places, because the failure
mode of a tool like this is not "it doesn't work" — it's "it works, and now your
address is on a blocklist."

## The three brakes

**1. A target does not exist until a human verified its route.**
Every entry in `targets.json` needs a `verified` date. `render.py` will not
draft for anything missing it, anything verified more than 180 days ago, or
anything without a `hook` — a sentence explaining why *this* organisation
specifically. No hook means the message would be identical to the other ones,
and identical messages are the definition of bulk mail.

**2. Drafts are files, not a queue.**
`render.py` writes `.eml` files into `outbox/`. Nothing leaves the machine.
You open the file, read it, and decide.

**3. `send.py` sends one file per invocation.**
Not a glob. Not a loop. One path in, one message out. On top of that it
enforces `daily_cap` (default 5), `min_gap_min` (default 20), a per-slug
dedupe against `state/sent.jsonl`, and refuses any target that has since gone
stale.

## Daily routine

```bash
# 1. see what is actually ready, write nothing
python3 render.py --check

# 2. draft
python3 render.py

# 3. read one
less outbox/human-i-t.eml

# 4. send that one, or don't
export SMTP_USER='you@example.com'
export SMTP_PASS='app-password'     # Gmail: an app password, not your login
python3 send.py outbox/human-i-t.eml          # preview, stops
python3 send.py outbox/human-i-t.eml --yes    # transmits
```

Five per day is the default. That is not a technical limit to work around —
it is the point. A slow trickle of specific, individually-written messages
gets read. A hundred near-identical ones get a domain suspended.

## Form and program targets

Half of the useful routes are web forms, not inboxes. For those, `render.py`
writes a `.md` brief instead of an `.eml`: the same message, plus the route,
the notes and what to do with it. Paste it into their form. `send.py` refuses
`.md` files outright — you cannot accidentally email a form.

## Gmail specifics

Use an app password (`myaccount.google.com/apppasswords`), not your account
password. If you have 2FA on — you should — plain SMTP login will fail without
it. Keep `daily_cap` at 5 or lower; Gmail's own sending limits are far higher,
but recipient-side filters are not.

## What "success" looks like

Realistically: a handful of replies, mostly "no", one or two "try this other
programme", and possibly one refurbished machine. That is a good outcome. The
page is doing most of the work — the email only has to survive long enough to
be read.
