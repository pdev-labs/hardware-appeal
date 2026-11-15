# Targets

`targets.json` is the list of organisations worth contacting. It is short on
purpose. Eight verified routes beat a hundred guessed ones, and the guessed
ones are what get an address blocklisted.

## Adding a target

1. Find the organisation's **published** route for this kind of enquiry. Not a
   guessed `firstname@company.com`. Not a generic `hello@`.
2. Open it. Confirm it is live, that it accepts individual requests, and that
   the audience matches you.
3. Add an entry, then run:

```bash
python3 render.py --check
```

It will refuse the entry until every field is real.

## Fields

| field | meaning |
|---|---|
| `slug` | lowercase, hyphenated, used as the filename |
| `org` | display name, used in the subject and greeting |
| `kind` | `email` (sendable), `form` (web form), `program` (their process) |
| `route` | a bare address for `email`, otherwise the URL |
| `audience` | `individual`, `maintainer`, `community` — keeps the fit honest |
| `fit` | `high`, `medium`, `low` — low means low; do not send low-fit mail |
| `verified` | `YYYY-MM-DD`, the day *you* opened the route |
| `hook` | one specific sentence about why them. Must be at least 8 words, and must be true |
| `notes` | what to actually do with the draft |

## Rules that keep this legitimate

- **One message per organisation, ever.** `send.py` enforces this against
  `state/sent.jsonl`. If they say no, that is the end of it.
- **No low-fit targets.** If `fit` is `low` because the programme is
  location-locked to a city you do not live in, do not send it. That is a
  wasted stranger's time and it is how a request reads as spam.
- **No scraped addresses.** If it is not published for enquiries, it is not a
  route.
- **Refresh the date.** A route verified six months ago is a guess again.
