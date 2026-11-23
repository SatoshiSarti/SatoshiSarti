# Profile card

```bash
python3 refresh.py             # product metrics and contributions -> card.json
python3 tools/build_card.py    # card.json + the files below -> both SVGs
```

`refresh.py` and `tools/build_card.py` use only Python's standard library and
call no AI service. The scheduled workflow runs both every six hours with the
workflow's own token; there is no stored secret. The time in the card's top
right corner is the last refresh that succeeded.

## What each part is

- **MyFutureSelf** figures come from the public snapshot at
  `https://kayahickin.com/api/profile-metrics`. A snapshot older than 48 hours
  is rejected and the card keeps its last values. Downloads, paid
  subscriptions and ratings are exact counts; ARR keeps the source's display
  precision.
- **Downloads chart** draws the last 90 days of `metrics_history.json` from a
  zero baseline, one point per day, appended on each refresh. Days with no
  point are joined by a straight line. The series before this repository
  existed was copied from the same file in
  [kayahickindev/kayahickindev](https://github.com/kayahickindev/kayahickindev).
- **Systems** and **Stack** are written by hand in `tools/build_card.py`. Each
  line describes how a private system works and was checked against its
  source; change a line only after checking it the same way.
- **Languages** and the **repository count** cover private repositories, which
  the workflow's token cannot read. Refresh them on a signed-in machine with
  `python3 tools/languages.py`, then rebuild and commit. `language_stats.json`
  records the date it was last counted.
- **Contributions** is the number on the profile's contribution graph, private
  contributions included. Much of that volume is an automated sync, which is
  why the card shows no lines-of-code or pull-request totals: they would
  overstate the code written by hand.

## Portrait

`tools/scanline.py` turns `tools/headshot.png` into 95 horizontal lines whose
weight follows the photo's luminance (`portrait_dark.json`,
`portrait_light.json`). It needs `pip install -r tools/requirements.txt`;
nothing else does.

```bash
python3 tools/scanline.py --preview
```

## Design notes

- The card is 1000 by 612. GitHub shows it through an `<img>`, so there is no
  script and no web font: type is the viewer's system monospace and sans, and
  nothing depends on exact character widths except the stack chips, which the
  builder asserts fit their column.
- Motion is CSS inside the SVG: the portrait draws in line by line behind a
  beam, the chart line draws itself, and the two live dots pulse. All of it
  stops under `prefers-reduced-motion`, and a viewer that does not animate
  sees the finished card.
- Language colours belong to the language, not its rank. The three per theme
  were checked for colour-blind separation and contrast against each surface.
