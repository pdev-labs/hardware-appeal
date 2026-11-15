#!/usr/bin/env python3
"""Refresh star counts, languages and the public repo total from the GitHub API.

    python3 sync_evidence.py && python3 build.py

It never invents a description. Repos already listed in evidence.json keep
their hand-written blurb; a repo that disappears is flagged rather than
silently dropped. New repos are listed at the end so you can decide whether
one deserves a line and a blurb.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).parent
HANDLE = "pdev-labs"
API = f"https://api.github.com/users/{HANDLE}/repos?per_page=100&sort=updated"


def fetch() -> list[dict]:
    req = urllib.request.Request(API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{HANDLE}-hardware-appeal",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        hint = " (rate limited — try again later)" if exc.code == 403 else ""
        sys.exit(f"FAIL  GitHub API returned {exc.code}{hint}")
    except urllib.error.URLError as exc:
        sys.exit(f"FAIL  cannot reach the GitHub API: {exc.reason}")


def main() -> None:
    path = ROOT / "evidence.json"
    data = json.loads(path.read_text())
    everything = {r["name"]: r for r in fetch()}
    live = {name: r for name, r in everything.items() if not r.get("fork")}

    listed = {r["name"] for r in data["repos"]}
    gone, refreshed, forked = [], [], []

    for row in data["repos"]:
        src = live.get(row["name"])
        if not src:
            if row["name"] in everything:
                forked.append(row["name"])
            else:
                gone.append(row["name"])
            continue
        before = (row.get("stars"), row.get("lang"))
        row["stars"] = src["stargazers_count"]
        row["lang"] = src.get("language") or row.get("lang")
        if (row["stars"], row["lang"]) != before:
            refreshed.append(f"{row['name']}: {before[0]}→{row['stars']} stars")

    data["public_repos"] = len(live)
    data["generated"] = dt.date.today().isoformat()
    path.write_text(json.dumps(data, indent=2) + "\n")

    print(f"PASS  {len(live)} original public repos, {len(data['repos'])} on the page")
    for line in refreshed:
        print(f"      updated {line}")
    for name in forked:
        print(f"WARN  {name} is a fork — the page should only claim original work")
    for name in gone:
        print(f"WARN  {name} is no longer public — remove it or fix the name")

    extras = sorted(set(live) - listed)
    if extras:
        print(f"      not on the page yet ({len(extras)}): {', '.join(extras[:8])}"
              + (" …" if len(extras) > 8 else ""))


if __name__ == "__main__":
    main()
