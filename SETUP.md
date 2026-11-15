# Setup — five minutes

This repo does two jobs: it is the public case page, and it is the outreach
pipeline that points at it. The page is the argument. The emails only carry a
link to it.

## 1. Put your address in

```bash
# appeal.toml  →  [identity] email
```

`build.py` refuses to generate anything while it still says `__SET_ME__`, so a
placeholder can never reach the public page.

## 2. Build

```bash
python3 build.py
```

That writes `README.md` and `docs/index.html`. Both are generated — edit
`appeal.toml` and `src/`, never the output.

## 3. Publish

```bash
git init -b main
git add -A
git commit -m "hardware request: case file and outreach pipeline"
git remote add origin git@github.com:pdev-labs/hardware-appeal.git
git push -u origin main
```

Then, on GitHub: **Settings → Pages → Source: Deploy from a branch → main / docs**.

Live at `https://pdev-labs.github.io/hardware-appeal/`. Check the URL resolves
before you send any email — every message points at it.

## 4. Enrol in Sponsors first

`github.com/sponsors` — a sponsors tier turns the page into something a reader
can act on without emailing you. It is the single highest-value step here, and
it costs nothing.

## 5. Then the outreach

```bash
cd outreach
python3 render.py --check     # what is ready
python3 render.py             # draft
less outbox/<slug>.md         # read one
```

Full detail in [`outreach/README.md`](outreach/README.md) and
[`targets/README.md`](targets/README.md).

## The rule that matters

One message per organisation, ever. `send.py` enforces it against
`state/sent.jsonl`. Five a day maximum. The list is eight verified routes, not
a hundred guessed addresses — the guessed ones are what get an address
blocklisted and a profile remembered for the wrong reason.

## Refreshing the evidence

The repo list on the page comes from `evidence.json`, which was written from the
public API on the date shown on the page. Re-pull it when your work changes:

```bash
python3 sync_evidence.py
python3 build.py
```
