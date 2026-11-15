#!/usr/bin/env python3
"""Render the public case page and README from appeal.toml.

    python3 build.py

Refuses to write anything if the contact address is still a placeholder,
so the repo can never accidentally publish an address that does not exist.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import sys
import tomllib

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "src"
DOCS = ROOT / "docs"

PASS_FILE = "PASS"
FAIL_FILE = "FAIL"


def die(msg: str) -> None:
    print(f"{FAIL_FILE}  {msg}", file=sys.stderr)
    raise SystemExit(1)


def load() -> tuple[dict, dict]:
    with open(ROOT / "appeal.toml", "rb") as fh:
        cfg = tomllib.load(fh)
    evidence = json.loads((ROOT / "evidence.json").read_text())
    return cfg, evidence


def check(cfg: dict) -> None:
    email = cfg["identity"].get("email", "")
    if not email or "__SET_ME__" in email:
        die(
            "identity.email in appeal.toml is still the placeholder.\n"
            "      Set it, then run build.py again. Nothing was written."
        )
    if "@" not in email:
        die(f"identity.email does not look like an address: {email!r}")


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def evidence_rows(evidence: dict) -> str:
    rows = []
    for r in evidence["repos"]:
        meta = [r["lang"]] if r.get("lang") else []
        if r["stars"]:
            meta.append(f"{r['stars']} star" + ("s" if r["stars"] != 1 else ""))
        rows.append(
            f"""      <li class="repo">
        <div class="repo-head">
          <a href="{esc(r['url'])}">{esc(r['name'])}</a>
          <span class="repo-meta">{esc(" · ".join(meta))}</span>
        </div>
        <p>{esc(r['blurb'])}</p>
      </li>"""
        )
    return "\n".join(rows)


def evidence_md(evidence: dict) -> str:
    lines = []
    for r in evidence["repos"]:
        meta = " · ".join(filter(None, [r.get("lang"), (f"{r['stars']} star" + ("s" if r["stars"] != 1 else "")) if r["stars"] else ""]))
        lines.append(f"- **[{r['name']}]({r['url']})** — {r['blurb']} _({meta})_")
    return "\n".join(lines)


def bullets(items: list[str], cls: str) -> str:
    return "\n".join(f'      <li class="{cls}">{esc(i)}</li>' for i in items)


def offers_html(cfg: dict) -> str:
    return "\n".join(
        f'      <li><strong>{esc(o["title"])}.</strong> {esc(o["text"])}</li>'
        for o in cfg["offers"]
    )


def offers_md(cfg: dict) -> str:
    return "\n".join(
        f'{i}. **{o["title"]}.** {o["text"]}' for i, o in enumerate(cfg["offers"], 1)
    )


def md_bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items)


def main() -> None:
    cfg, evidence = load()
    check(cfg)

    ident = cfg["identity"]
    hw = cfg["hardware"]
    ctx = cfg["context"]
    email = ident["email"]

    today = dt.date.today().isoformat()

    fields = {
        "EMAIL": email,
        "EMAIL_HTML": esc(email),
        "EMAIL_URLENC": email,
        "PROFILE": ident["profile"],
        "HANDLE": ident["handle"],
        "LOCATION": ident.get("location") or "",
        "SITUATION": esc(ctx["situation"]),
        "WHAT_I_DO": esc(ctx["what_i_do"]),
        "DEAD_MACHINE": esc(hw["dead_machine"]),
        "DEAD_YEAR": str(hw["dead_year"]),
        "DEAD_NOTE": esc(hw["dead_note"]),
        "NOT_ASKING": esc(hw["wanted"]["not_asking"]),
        "MIN_ITEMS": bullets(hw["wanted"]["minimum"], "need"),
        "NICE_ITEMS": bullets(hw["wanted"]["nice_to_have"], "nice"),
        "MIN_ITEMS_MD": md_bullets(hw["wanted"]["minimum"]),
        "NICE_ITEMS_MD": md_bullets(hw["wanted"]["nice_to_have"]),
        "EVIDENCE": evidence_rows(evidence),
        "EVIDENCE_MD": evidence_md(evidence),
        "OFFERS": offers_html(cfg),
        "OFFERS_MD": offers_md(cfg),
        "PUBLIC_REPOS": str(evidence["public_repos"]),
        "STARS": str(sum(r["stars"] for r in evidence["repos"])),
        "UPDATED": today,
    }

    DOCS.mkdir(exist_ok=True)
    written = []

    # ---- the page ----
    page = (SRC / "index.tpl.html").read_text()
    for k, v in fields.items():
        page = page.replace("{{" + k + "}}", v)
    if "{{" in page:
        die("unfilled placeholder left in index.tpl.html")
    (DOCS / "index.html").write_text(page)
    (DOCS / ".nojekyll").write_text("")
    written.append("docs/index.html")

    # ---- the README ----
    readme = (SRC / "README.tpl.md").read_text()
    for k, v in fields.items():
        readme = readme.replace("{{" + k + "}}", v)
    if "{{" in readme:
        die("unfilled placeholder left in README.tpl.md")
    (ROOT / "README.md").write_text(readme)
    written.append("README.md")

    print(f"{PASS_FILE}  built {', '.join(written)}")
    print(f"      contact: {email}")
    print("      next:    git add -A && git commit, then push and set Pages to /docs")


if __name__ == "__main__":
    main()
