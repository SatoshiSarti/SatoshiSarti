# Profile card

The layout, portrait method and builder are adapted from
[kayahickindev/kayahickindev](https://github.com/kayahickindev/kayahickindev)
by Kaya Hickin.

```bash
python3 refresh.py            # product metrics and contributions -> card.json
python3 tools/build_svg.py    # card.json + language_stats.json -> both SVGs
```

`refresh.py` and `tools/build_svg.py` use only Python's standard library and
call no AI service. The scheduled workflow runs both every six hours with the
workflow's own token; there is no stored secret.

## What each number is

- **MyFutureSelf** rows come from the public snapshot at
  `https://kayahickin.com/api/profile-metrics`. A snapshot older than 48 hours
  is rejected and the card keeps its last values. Downloads, paid
  subscriptions, actions and ratings are exact counts; ARR keeps the source's
  display precision.
- **Downloads trend** draws the last 90 days of `metrics_history.json`, one
  point per day, appended on each refresh. The series before this repository
  existed was copied from the same file in Kaya's repository.
- **Contributions (1y)** is the number on the profile's contribution graph,
  private contributions included. Much of that volume is an automated sync,
  which is why the card has no lines-of-code or pull-request rows: those
  totals would overstate the code written by hand.
- **Repositories contributed to** and the **language bar** cover private
  repositories, which the workflow's token cannot read. Refresh them on a
  signed-in machine with `python3 tools/languages.py`, then rebuild and
  commit. `language_stats.json` records the date it was last counted.
- **Engineering** rows are written by hand in `tools/build_svg.py`.

## Portrait

`tools/portrait.py` turns `tools/headshot.png` into the two stipple portraits
(`ascii_art_dark.txt`, `ascii_art_light.txt`), 430 by 412 one-pixel cells.
It needs `pip install -r tools/requirements.txt`; nothing else does.

```bash
python3 tools/portrait.py --preset balanced
```

## Layout

The 985 by 545 card has two columns. Left: the portrait, then the language bar
and its legend. Right: a 63-column monospace readout ending on a
`giancarlo@myfutureself:~$` prompt. The builder asserts that every row is
exactly 63 characters, so a longer value fails the build instead of breaking
the right edge. A cover slides off the portrait on load and the cursor blinks;
both stop under `prefers-reduced-motion`.
