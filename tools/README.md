# Profile card

```bash
GH_TOKEN=$(gh auth token) python3 refresh.py   # contribution calendar -> card.json
python3 tools/build_card.py                    # card.json + language_stats.json -> card.svg
```

Both use only Python's standard library and call no AI service. The scheduled
workflow runs them every six hours with the workflow's own token; there is no
stored secret.

## What each part is

- **Journal page.** The date is the last day in the contribution calendar and
  `DAY n` counts from the day this account was created. The circled number is
  the total on the profile's contribution graph for the last twelve months,
  private contributions included. Peak day, active days and longest run are
  computed from the same calendar. Much of that volume is an automated sync,
  which is why the card shows no lines-of-code or pull-request totals: they
  would overstate the code written by hand.
- **Red-pen plot.** Contributions per week for the last 26 weeks, from zero.
- **Repositories and languages** cover private repositories, which the
  workflow's token cannot read. Refresh them on a signed-in machine with
  `python3 tools/languages.py`, then rebuild and commit. `language_stats.json`
  records the date it was last counted.
- **Case cards** are written by hand in `tools/build_card.py`. Each describes
  how a private system works and was checked against its source; change one
  only after checking it the same way.

## Design notes

- The card is 920 by 520 and dark in both GitHub themes. GitHub shows it
  through an `<img>`, so there is no script and no web font. Type falls back
  from American Typewriter to Courier New, and from Bradley Hand to Segoe
  Print, so the layout avoids anything that depends on exact text width.
- Motion is CSS inside the SVG: the pen circle, the plot and the string draw
  themselves, the stamps land, rain falls, and a few bats cross on load and
  every ten seconds after (`BAT_CYCLE`, `BATS`). Under
  `prefers-reduced-motion` the bats are removed and everything else is still.
  A viewer that does not animate sees the finished board without bats.
