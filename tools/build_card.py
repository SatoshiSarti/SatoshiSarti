"""Build dark_mode.svg and light_mode.svg for the profile README.

Inputs, none of them fetched here:
  card.json                  product metrics and contributions (refresh.py)
  metrics_history.json       one downloads point per day (refresh.py)
  language_stats.json        language bytes and repository count (tools/languages.py)
  tools/portrait_*.json      the scan-line portrait (tools/scanline.py)

Stdlib only. GitHub shows the SVG through an <img>, so there is no script and
no web font: motion is CSS inside the file, and type is the viewer's own
system monospace and sans.
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

W, H = 1000, 612
PAD = 28
LEFT_W = 300                       # portrait and language column
RIGHT_X, RIGHT_END = 364, W - PAD  # readout column
PORTRAIT_Y = 68
TREND_DAYS = 90

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

# Language colours follow the language, never its rank, so a new language
# cannot repaint the others. The three steps per mode were checked for
# colour-blind separation and contrast against each card surface.
LANGUAGE_SLOTS = ("Python", "JavaScript", "Shell")
DARK = dict(
    name="dark", surface="#0b0d10", border="#1e232b", dot="#171b21",
    ink="#f2f4f7", ink2="#a8b0bb", ink3="#6f7885", hair="#252b34",
    accent="#b6f24a", line="#e8ecf1", chip="#12161b",
    languages=("#3987e5", "#d95926", "#199e70"), other="#6f7885",
)
LIGHT = dict(
    name="light", surface="#fbfbf8", border="#dcdcd4", dot="#ecece6",
    ink="#0e1013", ink2="#4a4f57", ink3="#7c828b", hair="#d8d8d0",
    accent="#3f8a12", line="#14171b", chip="#f1f1ec",
    languages=("#2a78d6", "#eb6834", "#1baf7a"), other="#7c828b",
)

# What each system is, in the order it was built. Each line is checked against
# the system's own source before it is changed.
SYSTEMS = (
    ("imessage-agent", "chat.db poll → claude -p → osascript reply · zero npm deps"),
    ("mention-tracker", "yt-dlp → whisper.cpp → rule engine · Vision OCR fallback"),
    ("deadman-switch", "heartbeat gist ← Mac mini · Actions cron → staged alerts"),
    ("sync-score", "ffmpeg frames × audio envelope → cross-correlation lag"),
)
STACK = ("Claude Code", "Playwright", "launchd", "whisper.cpp", "ffmpeg", "GitHub Actions")


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load(path):
    if not path.exists():
        raise RuntimeError(f"{path.name} is missing: see tools/README.md")
    return json.loads(path.read_text(encoding="utf-8"))


CARD = load(ROOT / "card.json")
STATS = CARD["stats"]
LANGUAGE_STATS = load(ROOT / "language_stats.json")
HISTORY = load(ROOT / "metrics_history.json")
for needed in ("downloads", "paid", "arr", "rating", "reviews", "contributions"):
    if not STATS.get(needed):
        raise RuntimeError(f"card.json has no {needed}: run refresh.py")


def languages():
    """(name, share 0..1) for each language worth a segment, largest first."""
    entries = LANGUAGE_STATS["languages"]
    total = sum(entry["bytes"] for entry in entries) or 1
    shown = [(entry["name"], entry["bytes"] / total) for entry in entries
             if entry["bytes"] / total >= 0.005]
    return sorted(shown, key=lambda item: -item[1])


def trend(days=TREND_DAYS):
    """Downloads over the last `days` days: [(date, value)], oldest first.

    The window opens on a value interpolated at its first day, so the gain is
    the change across the whole window whichever days happen to have points.
    """
    series = sorted((date.fromisoformat(p["date"]), p["value"])
                    for p in HISTORY.get("downloads", []))
    end = series[-1][0]
    start = end - timedelta(days=days)
    inside = [point for point in series if point[0] >= start]
    before = [point for point in series if point[0] < start]
    if before and inside[0][0] > start:
        (d0, v0), (d1, v1) = before[-1], inside[0]
        share = (start - d0).days / (d1 - d0).days
        inside.insert(0, (start, round(v0 + (v1 - v0) * share)))
    return inside


def section(pal, label, y, x=RIGHT_X, end=RIGHT_END, note=""):
    out = [f'<text x="{x}" y="{y}" class="label" fill="{pal["ink2"]}">{esc(label)}</text>']
    if note:
        out.append(f'<text x="{end}" y="{y}" class="note" text-anchor="end" '
                   f'fill="{pal["ink3"]}">{esc(note)}</text>')
    out.append(f'<line x1="{x}" y1="{y + 9}" x2="{end}" y2="{y + 9}" '
               f'stroke="{pal["hair"]}"/>')
    return out


def header(pal):
    synced = datetime.fromisoformat(CARD["refreshedAt"].replace("Z", "+00:00"))
    stamp = synced.strftime("SYNCED %Y-%m-%d %H:%M UTC")
    return [
        f'<text x="{PAD}" y="40" class="label" fill="{pal["ink"]}">GIANCARLO SARTI'
        f'<tspan fill="{pal["ink3"]}">  /  CO-FOUNDER &amp; CEO, MYFUTURESELF</tspan></text>',
        f'<circle class="pulse" cx="{RIGHT_END - 4}" cy="36" r="4" fill="{pal["accent"]}"/>',
        f'<circle cx="{RIGHT_END - 4}" cy="36" r="3.5" fill="{pal["accent"]}"/>',
        f'<text x="{RIGHT_END - 16}" y="40" class="note" text-anchor="end" '
        f'fill="{pal["ink3"]}">{stamp}</text>',
        f'<line x1="{PAD}" y1="54" x2="{RIGHT_END}" y2="54" stroke="{pal["hair"]}"/>',
    ]


def portrait(pal):
    data = load(HERE / f'portrait_{pal["name"]}.json')
    width, height, rows = data["width"], data["height"], data["rows"]
    x, y = PAD, PORTRAIT_Y
    out = [f'<g transform="translate({x} {y})" fill="{pal["line"]}">']
    for index, path in enumerate(rows):
        out.append(f'<path class="row" style="animation-delay:{120 + index * 14}ms" '
                   f'd="{path}"/>')
    # A beam that draws the portrait in once, then passes again every so often.
    out.append(f'<rect class="beam" x="0" y="-1" width="{width}" height="2" '
               f'fill="{pal["accent"]}"/>')
    out.append("</g>")
    # Corner brackets, like the frame of an instrument display.
    arm = 9
    for cx, cy, sx, sy in ((x - 6, y - 6, 1, 1), (x + width + 6, y - 6, -1, 1),
                           (x - 6, y + height + 6, 1, -1),
                           (x + width + 6, y + height + 6, -1, -1)):
        out.append(f'<path d="M{cx + sx * arm} {cy}H{cx}V{cy + sy * arm}" fill="none" '
                   f'stroke="{pal["ink3"]}"/>')
    out.append(f'<text x="{x}" y="{y + height + 24}" class="note" fill="{pal["ink3"]}">'
               f'FIG. 1  {len(rows)} SCAN LINES · WEIGHT ∝ LUMINANCE</text>')
    return out


def language_block(pal, y=506):
    shown = languages()
    out = section(pal, "LANGUAGES", y, x=PAD, end=PAD + LEFT_W, note="BY BYTES")
    bar_y, bar_h, gap = y + 20, 8, 2
    out.append(f'<clipPath id="bar"><rect x="{PAD}" y="{bar_y}" width="{LEFT_W}" '
               f'height="{bar_h}" rx="4"/></clipPath><g clip-path="url(#bar)">')
    usable = LEFT_W - gap * (len(shown) - 1)
    offset = PAD
    colors = []
    for name, share in shown:
        color = (pal["languages"][LANGUAGE_SLOTS.index(name)]
                 if name in LANGUAGE_SLOTS else pal["other"])
        colors.append(color)
        span = usable * share
        out.append(f'<rect x="{offset:.1f}" y="{bar_y}" width="{span:.1f}" '
                   f'height="{bar_h}" fill="{color}"/>')
        offset += span + gap
    out.append("</g>")
    for index, ((name, share), color) in enumerate(zip(shown, colors)):
        row_y = bar_y + 28 + index * 18
        out.append(f'<rect x="{PAD}" y="{row_y - 9}" width="9" height="9" rx="2" '
                   f'fill="{color}"/>')
        out.append(f'<text x="{PAD + 17}" y="{row_y}" class="body" '
                   f'fill="{pal["ink"]}">{esc(name)}</text>')
        out.append(f'<text x="{PAD + LEFT_W}" y="{row_y}" class="body" text-anchor="end" '
                   f'fill="{pal["ink2"]}">{share * 100:.1f}%</text>')
    return out


def kpis(pal, y=134):
    tiles = (
        (STATS["downloads"], "DOWNLOADS"),
        (STATS["paid"], "PAID SUBSCRIPTIONS"),
        (STATS["arr"], "ARR"),
        (STATS["rating"], f'STARS · {STATS["reviews"]} RATINGS'),
    )
    out = section(pal, "MYFUTURESELF", 82, note="PRODUCT · LIVE FEED")
    # Columns are as wide as their own label needs, not equal quarters.
    columns = (RIGHT_X, RIGHT_X + 160, RIGHT_X + 312, RIGHT_X + 450)
    for x, (value, label) in zip(columns, tiles):
        out.append(f'<text x="{x:.0f}" y="{y}" class="figure" fill="{pal["ink"]}">'
                   f'{esc(value)}</text>')
        out.append(f'<text x="{x:.0f}" y="{y + 20}" class="note" fill="{pal["ink3"]}">'
                   f'{esc(label)}</text>')
    return out


def chart(pal, top=200, bottom=296):
    """Downloads over the window: one line from a zero baseline, end labelled."""
    points = trend()
    first, last = points[0][0], points[-1][0]
    span = (last - first).days or 1
    gained = points[-1][1] - points[0][1]
    peak = max(value for _, value in points)
    ceiling = 20_000
    while ceiling < peak * 1.04:
        ceiling += 20_000
    # Scale labels sit in their own gutter, so they can never cross the line.
    x0, x1 = RIGHT_X + 34, RIGHT_END - 6

    def px(day):
        return x0 + (day - first).days / span * (x1 - x0)

    def py(value):
        return bottom - value / ceiling * (bottom - top)

    out = [
        f'<text x="{RIGHT_X}" y="{top - 16}" class="note" fill="{pal["ink3"]}">'
        f'DOWNLOADS · LAST {span} DAYS</text>',
        f'<text x="{RIGHT_END}" y="{top - 16}" class="body" text-anchor="end" '
        f'fill="{pal["ink"]}"><tspan fill="{pal["accent"]}">▲ </tspan>{gained:+,}</text>',
    ]
    for level in range(50_000, ceiling + 1, 50_000):
        y = py(level)
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{RIGHT_END}" y2="{y:.1f}" '
                   f'stroke="{pal["hair"]}" stroke-dasharray="2 4"/>')
        out.append(f'<text x="{x0 - 8}" y="{y + 3.5:.1f}" class="tick" text-anchor="end" '
                   f'fill="{pal["ink3"]}">{level // 1000}K</text>')
    out.append(f'<line x1="{x0}" y1="{bottom}" x2="{RIGHT_END}" y2="{bottom}" '
               f'stroke="{pal["ink3"]}"/>')
    out.append(f'<text x="{x0 - 8}" y="{bottom + 3.5}" class="tick" text-anchor="end" '
               f'fill="{pal["ink3"]}">0</text>')
    month = date(first.year, first.month, 1)
    while month <= last:
        if month >= first:
            x = px(month)
            out.append(f'<line x1="{x:.1f}" y1="{bottom}" x2="{x:.1f}" y2="{bottom + 4}" '
                       f'stroke="{pal["ink3"]}"/>')
            out.append(f'<text x="{x + 4:.1f}" y="{bottom + 15}" class="tick" '
                       f'fill="{pal["ink3"]}">{month.strftime("%b").upper()}</text>')
        month = date(month.year + month.month // 12, month.month % 12 + 1, 1)
    line = " ".join(f"{px(day):.1f},{py(value):.1f}" for day, value in points)
    end_x, end_y = px(last), py(points[-1][1])
    out += [
        f'<polygon points="{x0},{bottom} {line} {end_x:.1f},{bottom}" '
        f'fill="{pal["accent"]}" opacity="0.10"/>',
        f'<polyline class="draw" pathLength="1" points="{line}" fill="none" '
        f'stroke="{pal["accent"]}" stroke-width="2" stroke-linejoin="round" '
        f'stroke-linecap="round"/>',
        f'<circle class="pulse" cx="{end_x:.1f}" cy="{end_y:.1f}" r="4" '
        f'fill="{pal["accent"]}"/>',
        f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="4" fill="{pal["accent"]}" '
        f'stroke="{pal["surface"]}" stroke-width="2"/>',
    ]
    return out


def systems(pal, y=346):
    out = section(pal, "SYSTEMS", y, note=f"{len(SYSTEMS)} SHIPPED")
    for index, (name, detail) in enumerate(SYSTEMS):
        row_y = y + 32 + index * 26
        out.append(f'<text x="{RIGHT_X}" y="{row_y}" class="body" fill="{pal["ink3"]}">'
                   f'{index + 1:02d}</text>')
        out.append(f'<text x="{RIGHT_X + 28}" y="{row_y}" class="name" '
                   f'fill="{pal["ink"]}">{esc(name)}</text>')
        out.append(f'<text x="{RIGHT_X + 164}" y="{row_y}" class="detail" '
                   f'fill="{pal["ink2"]}">{esc(detail)}</text>')
    return out


def stack(pal, y=490):
    out = section(pal, "STACK", y)
    x, top, height = RIGHT_X, y + 22, 24
    for name in STACK:
        width = round(len(name) * 6.95 + 18)
        out.append(f'<rect x="{x}" y="{top}" width="{width}" height="{height}" rx="12" '
                   f'fill="{pal["chip"]}" stroke="{pal["hair"]}"/>')
        out.append(f'<text x="{x + width / 2:.1f}" y="{top + 16}" class="chip" '
                   f'text-anchor="middle" fill="{pal["ink"]}">{esc(name)}</text>')
        x += width + 8
    assert x - 8 <= RIGHT_END, "stack chips overflow the column"
    return out


def github(pal, y=590):
    repositories = LANGUAGE_STATS["repositories"]
    return [
        f'<text x="{RIGHT_X}" y="{y}" class="body" fill="{pal["ink2"]}">'
        f'<tspan class="name" fill="{pal["ink"]}">{STATS["contributions"]}</tspan>'
        f' contributions in the last year  ·  '
        f'<tspan class="name" fill="{pal["ink"]}">{repositories}</tspan>'
        f' repositories</text>'
    ]


def style(pal):
    rows = len(load(HERE / f'portrait_{pal["name"]}.json')["rows"])
    draw_ms = 120 + rows * 14
    return f"""<style>
text {{font-family: {MONO}; white-space: pre;}}
.label {{font-size: 12px; letter-spacing: 1.6px; font-weight: 600;}}
.note {{font-size: 10.5px; letter-spacing: 0.9px;}}
.tick {{font-size: 9.5px; letter-spacing: 0.6px;}}
.body {{font-size: 12.5px;}}
.name {{font-size: 13px; font-weight: 700;}}
.detail {{font-size: 12px;}}
.chip {{font-size: 11.5px;}}
.figure {{font-family: {SANS}; font-size: 34px; font-weight: 700;
  letter-spacing: -0.8px; font-variant-numeric: tabular-nums;}}
.row {{animation: row 0.45s ease-out backwards;}}
@keyframes row {{from {{opacity: 0; transform: translateX(-10px);}}}}
.beam {{opacity: 0; animation: draw-beam {draw_ms}ms linear 1, pass 11s linear {draw_ms + 2500}ms infinite;}}
@keyframes draw-beam {{from {{opacity: 0.9; transform: translateY(0);}}
  to {{opacity: 0.9; transform: translateY(380px);}}}}
@keyframes pass {{0% {{opacity: 0; transform: translateY(0);}} 2% {{opacity: 0.55;}}
  16% {{opacity: 0.55; transform: translateY(380px);}} 18%, 100% {{opacity: 0; transform: translateY(380px);}}}}
.draw {{stroke-dasharray: 1; animation: draw 1.8s ease-out 0.3s backwards;}}
@keyframes draw {{from {{stroke-dashoffset: 1;}}}}
.pulse {{transform-box: fill-box; transform-origin: center;
  animation: pulse 2.6s ease-out infinite;}}
@keyframes pulse {{from {{opacity: 0.55; transform: scale(1);}}
  to {{opacity: 0; transform: scale(3.4);}}}}
@media (prefers-reduced-motion: reduce) {{
  .row, .beam, .draw, .pulse {{animation: none;}}
  .pulse {{opacity: 0;}}
}}
</style>"""


def build(pal):
    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img">',
        "<title>Giancarlo Sarti: scan-line portrait, MyFutureSelf product metrics, "
        "systems shipped and GitHub activity</title>",
        style(pal),
        f'<pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">'
        f'<circle cx="10" cy="10" r="0.8" fill="{pal["dot"]}"/></pattern>',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" '
        f'fill="{pal["surface"]}" stroke="{pal["border"]}"/>',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="url(#grid)"/>',
    ]
    for part in (header, portrait, language_block, kpis, chart, systems, stack, github):
        out.extend(part(pal))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    for filename, palette in (("dark_mode.svg", DARK), ("light_mode.svg", LIGHT)):
        (ROOT / filename).write_text(build(palette), encoding="utf-8")
        print(f"wrote {filename} ({(ROOT / filename).stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
