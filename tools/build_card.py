"""Build card.svg, the profile README's case board.

A typewritten journal page on the left (the numbers), four case cards pinned
on the right (the systems), red string between them, rain over everything and
a loose group of bats that crosses the board on load and every ten seconds.

Inputs, none fetched here:
  card.json             contribution calendar (refresh.py)
  language_stats.json   language bytes and repository count (tools/languages.py)

Stdlib only. GitHub shows the SVG through an <img>, so there is no script and
no web font: motion is CSS inside the file and type is whatever typewriter,
handwriting and sans faces the viewer's system has.
"""
import json
import math
import random
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
W, H = 920, 520

TYPE = "'American Typewriter','Courier New',Courier,monospace"
HAND = "'Bradley Hand','Segoe Print','Marker Felt','Comic Sans MS',cursive"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
RED, RED_DEEP = "#e5132c", "#3b070c"
BONE, ASH, DIM = "#ece6dd", "#948e88", "#4d4845"

# codename, real name, runtime, what it does, pipeline.
# Each card describes a private system and was checked against its source;
# change one only after checking it again. The "what it does" and pipeline
# lines must stay under 52 characters: in Courier New, the fallback face, that
# is the width of a card.
SYSTEMS = (
    ("THE SIGNAL", "imessage-agent", "NODE",
     "Text it from an iPhone. A Mac mini agent answers.",
     ("chat.db poll", "claude -p", "osascript", "iMessage")),
    ("WIRETAP", "mention-tracker", "PYTHON",
     "Transcribes creator videos, flags app mentions.",
     ("yt-dlp", "whisper.cpp", "Vision OCR", "rule engine")),
    ("NIGHT WATCH", "deadman-switch", "SHELL",
     "Off-box alarm when a server goes silent.",
     ("Mac mini", "gist heartbeat", "Actions cron", "alerts")),
    ("LIE DETECTOR", "sync-score", "PYTHON",
     "Scores if an AI video's lips match its voice.",
     ("ffmpeg", "frame diff", "audio envelope", "xcorr lag")),
)
LINE_LIMIT = 52
TREND_WEEKS = 26

BAT_CYCLE = 10      # seconds between passes
BAT_COUNT = 7
BAT_SEED = 5        # fixes the flight paths, so a rebuild does not reshuffle them
# One bat seen from below, head up, in three wing positions that are swapped
# fast: raised, level, swept down. Thin arms, scalloped membrane, no outline.
BAT_BODY = "M-2.2-4.4L-1.9-8.6L-.5-5.5L.5-5.5L1.9-8.6L2.2-4.4C3-2 2.8 3 0 7.6C-2.8 3-3-2-2.2-4.4Z"
BAT_WINGS = {
    "u": "M-1.6-1L-12-14L-28-19C-25-14-22.6-10.6-21.6-6.4C-18.6-8.6-16-8.2-14-4.2C-11.2-6.2-9-5.2-7-1.2C-5-2.2-3-1.2-1.6 2Z",
    "m": "M-1.6-1L-13-7.4L-31-5C-27-3-24.6 0-23.6 4.2C-20.4 1-17.4 1.2-15.4 5.2C-12.2 2-9.2 2.2-7.2 6C-5 3.2-3 3-1.6 3Z",
    "d": "M-1.6 0L-13-3.4L-26 10C-22 8.6-20 10.4-19 14.6C-16 10.4-13.8 10.4-12 13.6C-10 8.6-8 7.4-6 9.6C-5 6-3 4-1.6 3Z",
}


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load(name):
    path = ROOT / name
    if not path.exists():
        raise RuntimeError(f"{name} is missing: see tools/README.md")
    return json.loads(path.read_text(encoding="utf-8"))


def ordinal(n):
    suffix = "TH" if 11 <= n % 100 <= 13 else {1: "ST", 2: "ND", 3: "RD"}.get(n % 10, "TH")
    return f"{n}{suffix}"


CARD = load("card.json")
LANGUAGE_STATS = load("language_stats.json")
TOTAL = CARD["total"]
DAY_COUNTS = [count for week in CARD["weeks"] for count in week["days"]]
WEEKS = [sum(week["days"]) for week in CARD["weeks"]][-TREND_WEEKS:]
PEAK_WEEK = max(WEEKS) or 1
BEST_DAY = max(DAY_COUNTS)
ACTIVE_DAYS = sum(1 for count in DAY_COUNTS if count)
LONGEST_RUN = run = 0
for count in DAY_COUNTS:
    run = run + 1 if count else 0
    LONGEST_RUN = max(LONGEST_RUN, run)
TODAY = date.fromisoformat(CARD["lastDay"])
DAY_NUMBER = (TODAY - date.fromisoformat(CARD["createdAt"][:10])).days
REPOSITORIES = LANGUAGE_STATS["repositories"]
_bytes = sum(entry["bytes"] for entry in LANGUAGE_STATS["languages"]) or 1
LANGUAGES = [(entry["name"], entry["bytes"] / _bytes)
             for entry in LANGUAGE_STATS["languages"] if entry["bytes"] / _bytes >= 0.005]


def bat_markup():
    out = []
    for key, wing in BAT_WINGS.items():
        both = f'<path d="{wing}"/><path d="{wing}" transform="scale(-1 1)"/>'
        # A dark red copy set just up and left of the black one reads as the
        # lamp catching the leading edge.
        out.append(f'<g class="w{key}"><g transform="translate(-.5 -.8)" fill="#571118">{both}</g>'
                   f'<g fill="#030101">{both}</g></g>')
    out.append(f'<path d="{BAT_BODY}" fill="#030101"/>')
    return "".join(out)


def bats():
    """CSS and markup for the bats.

    Each one flies its own uneven path from the left edge to the right,
    gaining height as it goes, and is turned most of the way toward where it
    is heading so it banks into the path instead of sliding sideways. They are
    invisible until their animation starts and between passes, so a viewer
    that does not animate sees the board without them.
    """
    rnd = random.Random(BAT_SEED)
    x0, x1 = -60, W + 60
    css, svg = [], ['<g class="bats">']
    for index in range(BAT_COUNT):
        size = rnd.choice((0.6, 0.75, 0.9, 1.05, 1.25, 1.55))
        cross = rnd.uniform(1.7, 2.7) * (0.85 if size > 1.2 else 1)
        delay = 0.3 + rnd.uniform(0, 1.3)
        y = rnd.uniform(40, H - 60)
        climb = rnd.uniform(-170, -40)
        points = [(0.0, y)]
        for t in sorted(rnd.uniform(0.06, 0.94) for _ in range(6)):
            points.append((t, y + climb * t + rnd.uniform(-34, 34)))
        points.append((1.0, y + climb + rnd.uniform(-20, 20)))
        share = cross / BAT_CYCLE * 100
        frames, pose = [], ""
        for k, (t, py) in enumerate(points):
            ahead, behind = points[min(k + 1, len(points) - 1)], points[max(k - 1, 0)]
            slope = (ahead[1] - behind[1]) / max((ahead[0] - behind[0]) * (x1 - x0), 1)
            pitch = max(-32, min(32, math.degrees(math.atan(slope))))
            pose = (f"transform: translate({x0 + t * (x1 - x0):.0f}px, {py:.0f}px) "
                    f"rotate({52 + pitch * 0.9:.0f}deg) scale({size});")
            frames.append(f"{t * share:.2f}% {{{pose} opacity: 1;}}")
        frames.append(f"{share + 0.1:.2f}%, 100% {{{pose} opacity: 0;}}")
        css.append(f".bat{index} {{animation: bat{index} {BAT_CYCLE}s linear {delay:.2f}s infinite;}}\n"
                   f"@keyframes bat{index} {{{' '.join(frames)}}}")
        blur = ' filter="url(#bat-blur)"' if size > 1.3 else ""
        svg.append(f'<g class="bat{index}" opacity="0"{blur}>{bat_markup()}</g>')
    svg.append("</g>")
    return "\n".join(css), svg


BAT_CSS, BAT_SVG = bats()


def style():
    return f"""<style>
text {{font-family: {TYPE}; white-space: pre;}}
.hand {{font-family: {HAND};}}
.ink {{fill: none; stroke: {RED}; stroke-linecap: round; stroke-linejoin: round;}}
.draw {{stroke-dasharray: 1; animation: draw 1.3s ease-out backwards;}}
@keyframes draw {{from {{stroke-dashoffset: 1;}}}}
.stamp {{transform-box: fill-box; transform-origin: center; animation: stamp 0.35s cubic-bezier(.3,1.6,.5,1) backwards;}}
@keyframes stamp {{from {{opacity: 0; transform: scale(1.7);}}}}
.rain {{animation: rain 0.6s linear infinite;}}
@keyframes rain {{to {{transform: translate(-30px, 110px);}}}}
.lamp {{animation: lamp 7s steps(1) infinite;}}
@keyframes lamp {{0%, 90% {{opacity: 1;}} 92% {{opacity: 0.55;}} 94% {{opacity: 1;}} 97% {{opacity: 0.7;}}}}
.wu {{animation: wu .16s steps(1) infinite;}}
@keyframes wu {{0% {{opacity: 1;}} 25%, 100% {{opacity: 0;}}}}
.wm {{animation: wm .16s steps(1) infinite;}}
@keyframes wm {{0% {{opacity: 0;}} 25% {{opacity: 1;}} 50% {{opacity: 0;}} 75% {{opacity: 1;}}}}
.wd {{animation: wd .16s steps(1) infinite;}}
@keyframes wd {{0%, 25% {{opacity: 0;}} 50% {{opacity: 1;}} 75%, 100% {{opacity: 0;}}}}
{BAT_CSS}
@media (prefers-reduced-motion: reduce) {{
  .draw, .stamp, .rain, .lamp {{animation: none;}}
  .bats {{display: none;}}
}}
</style>"""


def defs(frame):
    return f"""<defs>
<clipPath id="frame"><path d="{frame}"/></clipPath>
<radialGradient id="lamp" cx="30%" cy="18%" r="85%">
<stop offset="0" stop-color="#3a1a14" stop-opacity="0.9"/><stop offset="0.45" stop-color="#150b0a" stop-opacity="0.6"/><stop offset="1" stop-color="#000" stop-opacity="0"/>
</radialGradient>
<linearGradient id="page" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1d1915"/><stop offset="1" stop-color="#12100d"/></linearGradient>
<linearGradient id="index-card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#211c17"/><stop offset="1" stop-color="#15120f"/></linearGradient>
<pattern id="rain" width="30" height="110" patternUnits="userSpaceOnUse">
<path d="M22 4l-5 18M9 52l-6 22M27 70l-4 15M14 96l-3 11" stroke="#fff" stroke-width="0.8" opacity="0.055" fill="none"/>
</pattern>
<filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="5" stdDeviation="6" flood-color="#000" flood-opacity="0.8"/></filter>
<filter id="rough"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="1.6"/></filter>
<filter id="bat-blur"><feGaussianBlur stdDeviation="0.9"/></filter>
</defs>"""


def journal():
    out = ['<g transform="rotate(-1.3 220 260)">']
    out.append('<rect x="34" y="34" width="372" height="456" fill="url(#page)" '
               'stroke="#2c2620" filter="url(#shadow)"/>')
    for rule_y in range(96, 480, 26):
        out.append(f'<path d="M52 {rule_y}H388" stroke="#2a251f" stroke-width="0.8"/>')
    out.append(f'<path d="M78 34V490" stroke="{RED_DEEP}"/>')
    heading = f'{TODAY.strftime("%A")}, {TODAY.strftime("%B")} {ordinal(TODAY.day)}.'.upper()
    out.append(f'<text x="92" y="66" font-size="15.5" letter-spacing="1.5" fill="{BONE}">{heading}</text>')
    out.append(f'<text x="92" y="90" font-size="12" letter-spacing="1.5" fill="{ASH}">'
               f'DAY {DAY_NUMBER}.  GIANCARLO SARTI.</text>')
    out.append(f'<text x="96" y="166" font-size="62" font-weight="700" letter-spacing="1" '
               f'fill="{BONE}">{TOTAL}</text>')
    out.append('<path class="ink draw" pathLength="1" style="animation-delay:.5s" stroke-width="2.6" '
               'filter="url(#rough)" d="M92 148c-6-34 34-52 78-52s86 14 84 46-48 46-96 44'
               '-72-18-66-46c5-24 44-40 92-38"/>')
    out.append(f'<text x="268" y="128" class="hand" font-size="16" fill="{RED}" '
               f'transform="rotate(-6 268 128)">contributions,</text>')
    out.append(f'<text x="276" y="148" class="hand" font-size="16" fill="{RED}" '
               f'transform="rotate(-6 276 148)">12 months</text>')
    rows = (("PEAK DAY", f"{BEST_DAY}"), ("ACTIVE DAYS", f"{ACTIVE_DAYS}"),
            ("LONGEST RUN", f"{LONGEST_RUN} DAYS"), ("REPOSITORIES", f"{REPOSITORIES}"))
    for index, (label, value) in enumerate(rows):
        y = 222 + index * 26
        out.append(f'<text x="92" y="{y}" font-size="12.5" letter-spacing="1.4" fill="{ASH}">{label}</text>')
        out.append(f'<text x="380" y="{y}" font-size="13.5" letter-spacing="1" text-anchor="end" '
                   f'fill="{BONE}">{value}</text>')
    y = 222 + len(rows) * 26
    out.append(f'<text x="92" y="{y}" font-size="12.5" letter-spacing="1.4" fill="{ASH}">SOURCE</text>')
    out.append(f'<rect x="262" y="{y - 12}" width="118" height="15" fill="#050404"/>')
    out.append(f'<text x="254" y="{y}" class="hand" font-size="13" text-anchor="end" fill="{RED}">private</text>')

    # red-pen plot of the last 26 weeks, from zero
    gx, gy, gw, gh = 96, 368, 284, 70
    for k in range(0, TREND_WEEKS + 1, 2):
        x = gx + gw * k / TREND_WEEKS
        out.append(f'<path d="M{x:.1f} {gy}V{gy + gh}" stroke="#2a251f" stroke-width="0.6"/>')
    last = len(WEEKS) - 1
    points = " ".join(f"{gx + gw * i / last:.1f},{gy + gh - gh * week / PEAK_WEEK:.1f}"
                      for i, week in enumerate(WEEKS))
    out.append(f'<polyline class="ink draw" pathLength="1" style="animation-delay:1.1s" '
               f'points="{points}" stroke-width="2.2" filter="url(#rough)"/>')
    peak_x = gx + gw * WEEKS.index(PEAK_WEEK) / last
    # The note sits on whichever side of the peak has room for it.
    note_x, anchor = (peak_x - 20, "end") if peak_x > gx + 150 else (peak_x + 20, "start")
    out.append(f'<text x="{note_x:.1f}" y="{gy + 16}" class="hand" font-size="14" '
               f'text-anchor="{anchor}" fill="{RED}">{PEAK_WEEK} in a week</text>')
    out.append(f'<text x="{gx}" y="{gy + gh + 17}" font-size="9.5" letter-spacing="1.3" '
               f'fill="{DIM}">{TREND_WEEKS} WEEKS</text>')
    out.append(f'<text x="{gx + gw}" y="{gy + gh + 17}" font-size="9.5" letter-spacing="1.3" '
               f'text-anchor="end" fill="{DIM}">NOW</text>')
    languages = " / ".join(f"{name.upper()} {share * 100:.1f}" for name, share in LANGUAGES[:3])
    out.append(f'<text x="92" y="478" font-size="10.5" letter-spacing="1.2" fill="{ASH}">{esc(languages)}</text>')
    out.append("</g>")
    return out


def case_cards():
    cards = ((452, 22, -1.1), (492, 145, 0.9), (446, 268, -0.7), (486, 391, 1.2))
    cw, ch = 390, 112
    # Pins sit right of centre, clear of the name in each card's header.
    pins = [(x + cw / 2 + (60 if i % 2 else 30), y + 12) for i, (x, y, _) in enumerate(cards)]
    string = f"M250 138 Q360 56 {pins[0][0]:.0f} {pins[0][1]:.0f}"
    for (ax, ay), (bx, by) in zip(pins, pins[1:]):
        string += f" Q{(ax + bx) / 2 + 26:.0f} {(ay + by) / 2 + 8:.0f} {bx:.0f} {by:.0f}"
    out = []
    for index, ((x, y, tilt), system) in enumerate(zip(cards, SYSTEMS)):
        codename, name, runtime, does, stages = system
        pipeline = " > ".join(stages)
        assert len(does) <= LINE_LIMIT and len(pipeline) <= LINE_LIMIT, (codename, len(does), len(pipeline))
        out.append(f'<g transform="rotate({tilt} {x + cw / 2} {y + ch / 2})">')
        out.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" fill="url(#index-card)" '
                   f'stroke="#332c25" filter="url(#shadow)"/>')
        out.append(f'<path d="M{x} {y + 30}H{x + cw}" stroke="{RED_DEEP}"/>')
        out.append(f'<text x="{x + 16}" y="{y + 21}" font-size="10.5" letter-spacing="2" '
                   f'fill="{RED}">CASE {index + 1:02d}<tspan fill="{ASH}" letter-spacing="1">   {esc(name)}</tspan></text>')
        out.append(f'<text x="{x + cw - 16}" y="{y + 21}" font-size="9.5" letter-spacing="1.6" '
                   f'text-anchor="end" fill="{DIM}">{runtime}</text>')
        out.append(f'<text x="{x + 16}" y="{y + 56}" font-size="19" font-weight="700" '
                   f'letter-spacing="1.8" fill="{BONE}">{esc(codename)}</text>')
        out.append(f'<text x="{x + 16}" y="{y + 79}" font-size="11.5" fill="#d3ccc2">{esc(does)}</text>')
        out.append(f'<text x="{x + 16}" y="{y + 98}" font-size="10.5" letter-spacing="0.3" '
                   f'fill="{ASH}">{esc(pipeline)}</text>')
        out.append(
            f'<g class="stamp" style="animation-delay:{1.6 + index * 0.25}s">'
            f'<g transform="rotate(-9 {x + cw - 62} {y + 48})" opacity="0.85" filter="url(#rough)">'
            f'<rect x="{x + cw - 112}" y="{y + 36}" width="98" height="24" fill="none" '
            f'stroke="{RED}" stroke-width="2"/>'
            f'<text x="{x + cw - 63}" y="{y + 53}" font-family="{SANS}" font-size="12.5" '
            f'font-weight="800" letter-spacing="2.5" text-anchor="middle" fill="{RED}">DEPLOYED</text>'
            f'</g></g>')
        out.append("</g>")
    out.append(f'<path class="ink draw" pathLength="1" style="animation-delay:.9s;animation-duration:1.8s" '
               f'd="{string}" stroke-width="1.6" opacity="0.9"/>')
    for px, py in [(250, 138)] + pins:
        out.append(f'<circle cx="{px:.0f}" cy="{py + 1.5:.0f}" r="5.5" fill="#000" opacity="0.6"/>')
        out.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="5" fill="{RED}"/>'
                   f'<circle cx="{px - 1.5:.0f}" cy="{py - 1.5:.0f}" r="1.6" fill="#ff9aa5"/>')
    return out


def build():
    frame = f"M7 1H{W - 7}L{W - 1} 7V{H - 7}L{W - 7} {H - 1}H7L1 {H - 7}V7Z"
    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img">',
        f"<title>Giancarlo Sarti's case board: {TOTAL} contributions in twelve months "
        f"and four deployed systems</title>",
        style(), defs(frame),
        '<g clip-path="url(#frame)">',
        f'<rect width="{W}" height="{H}" fill="#070605"/>',
        f'<rect class="lamp" width="{W}" height="{H}" fill="url(#lamp)"/>',
    ]
    out += journal() + case_cards()
    out.append(f'<rect class="rain" x="-40" y="-120" width="{W + 80}" height="{H + 240}" '
               f'fill="url(#rain)"/>')
    out += BAT_SVG
    out.append("</g>")
    out.append(f'<path d="{frame}" fill="none" stroke="#2a2420" stroke-width="1.5"/>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    target = ROOT / "card.svg"
    target.write_text(build(), encoding="utf-8")
    print(f"wrote card.svg ({target.stat().st_size // 1024} KB): {TOTAL} contributions, "
          f"day {DAY_NUMBER}, peak week {PEAK_WEEK}")


if __name__ == "__main__":
    main()
