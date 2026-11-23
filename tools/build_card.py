"""Build card.svg, the profile README's case board.

A typewritten journal page on the left (the numbers), four case cards pinned
on the right (the systems), red string between them, rain over everything and
a few bats that cross the board on load and every ten seconds after.

Inputs, none fetched here:
  card.json             contribution calendar (refresh.py)
  language_stats.json   language bytes and repository count (tools/languages.py)

Stdlib only. GitHub shows the SVG through an <img>, so there is no script and
no web font: motion is CSS inside the file and type is whatever typewriter,
handwriting and sans faces the viewer's system has.
"""
import json
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

# name, runtime, pipeline. Each line describes how a private system works and
# was checked against its source; change one only after checking it again.
SYSTEMS = (
    ("imessage-agent", "NODE", ("chat.db", "claude -p", "osascript", "iMessage")),
    ("mention-tracker", "PYTHON", ("yt-dlp", "whisper.cpp", "Vision OCR", "rule engine")),
    ("deadman-switch", "SHELL", ("Mac mini", "gist heartbeat", "Actions cron", "alert")),
    ("sync-score", "PYTHON", ("ffmpeg", "frame diff", "audio envelope", "xcorr lag")),
)
TREND_WEEKS = 26
BAT_CYCLE = 10          # seconds between passes
# start (x, y), end (x, y), size, delay in seconds, seconds to cross, bob in px
BATS = (
    ((-70, 330), (990, 150), 1.00, 0.35, 3.3, 13),
    ((-70, 410), (990, 250), 0.72, 0.70, 3.7, 10),
    ((-70, 250), (990, 60), 0.58, 0.55, 3.0, 9),
    ((-70, 470), (990, 330), 0.86, 1.10, 3.9, 12),
    ((-70, 190), (990, 20), 0.46, 1.35, 3.4, 8),
)


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


def style():
    bats = []
    for index, ((x0, y0), (x1, y1), size, delay, cross, bob) in enumerate(BATS):
        share = cross / BAT_CYCLE * 100
        far = f"translate({x1}px, {y1}px) scale({size * 0.8:.2f})"
        bats.append(
            f".fly{index} {{animation: fly{index} {BAT_CYCLE}s linear {delay}s infinite;}}\n"
            f"@keyframes fly{index} {{0% {{transform: translate({x0}px, {y0}px) scale({size}); opacity: 1;}} "
            f"{share:.1f}% {{transform: {far}; opacity: 1;}} "
            f"{share + 0.1:.1f}%, 100% {{transform: {far}; opacity: 0;}}}}\n"
            f".bob{index} {{animation: bob{index} {0.7 + index * 0.09:.2f}s ease-in-out infinite alternate;}}\n"
            f"@keyframes bob{index} {{from {{transform: translateY(-{bob}px) rotate(-7deg);}} "
            f"to {{transform: translateY({bob}px) rotate(5deg);}}}}"
        )
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
.wing {{transform-box: fill-box; transform-origin: 100% 45%; animation: flap 0.21s ease-in-out infinite alternate;}}
@keyframes flap {{from {{transform: rotate(24deg) scaleX(0.82);}} to {{transform: rotate(-30deg) scaleX(1);}}}}
{chr(10).join(bats)}
@media (prefers-reduced-motion: reduce) {{
  .draw, .stamp, .rain, .lamp, .wing {{animation: none;}}
  .bats {{display: none;}}
}}
</style>"""


# One bat, drawn head-up. Each copy is written out in full rather than reused
# through <use>, because not every browser animates inside a <use> copy.
_WING = ("M-2 -1C-8 -10-19 -12-30 -6C-26 -4-24 -2-23 3C-20 0-17 0-15 4"
         "C-12 1-9 1-7 5C-6 3-4 2-2 2Z")
BAT = (f'<g fill="#050303" stroke="{RED}" stroke-width="0.9" stroke-linejoin="round">'
       f'<path class="wing" d="{_WING}"/>'
       f'<g transform="scale(-1 1)"><path class="wing" d="{_WING}"/></g>'
       '<path d="M-2.6 -4L-2.2 -9L0 -5.4L2.2 -9L2.6 -4C3.6 -2 3.4 3 0 7C-3.4 3-3.6 -2-2.6 -4Z"/>'
       "</g>")


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
    cards = ((452, 34, -1.1), (492, 150, 0.9), (446, 266, -0.7), (486, 382, 1.2))
    cw, ch = 390, 100
    pins = [(x + cw / 2 + (16 if i % 2 else -22), y + 12) for i, (x, y, _) in enumerate(cards)]
    string = f"M250 138 Q360 60 {pins[0][0]:.0f} {pins[0][1]:.0f}"
    for (ax, ay), (bx, by) in zip(pins, pins[1:]):
        string += f" Q{(ax + bx) / 2 + 26:.0f} {(ay + by) / 2 + 8:.0f} {bx:.0f} {by:.0f}"
    out = []
    for index, ((x, y, tilt), (name, runtime, stages)) in enumerate(zip(cards, SYSTEMS)):
        out.append(f'<g transform="rotate({tilt} {x + cw / 2} {y + ch / 2})">')
        out.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" fill="url(#index-card)" '
                   f'stroke="#332c25" filter="url(#shadow)"/>')
        out.append(f'<path d="M{x} {y + 30}H{x + cw}" stroke="{RED_DEEP}"/>')
        out.append(f'<text x="{x + 16}" y="{y + 21}" font-size="10.5" letter-spacing="2" '
                   f'fill="{RED}">CASE {index + 1:02d}</text>')
        out.append(f'<text x="{x + cw - 16}" y="{y + 21}" font-size="9.5" letter-spacing="1.6" '
                   f'text-anchor="end" fill="{DIM}">{runtime}</text>')
        out.append(f'<text x="{x + 16}" y="{y + 57}" font-size="18" font-weight="700" '
                   f'letter-spacing="1.6" fill="{BONE}">{esc(name.upper().replace("-", " "))}</text>')
        out.append(f'<text x="{x + 16}" y="{y + 82}" font-size="11.5" fill="{ASH}">'
                   f'{esc(" > ".join(stages))}</text>')
        out.append(
            f'<g class="stamp" style="animation-delay:{1.6 + index * 0.25}s">'
            f'<g transform="rotate(-9 {x + cw - 62} {y + 52})" opacity="0.85" filter="url(#rough)">'
            f'<rect x="{x + cw - 112}" y="{y + 39}" width="98" height="24" fill="none" '
            f'stroke="{RED}" stroke-width="2"/>'
            f'<text x="{x + cw - 63}" y="{y + 56}" font-family="{SANS}" font-size="12.5" '
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


def bats():
    """A small flock that crosses on load, then again every BAT_CYCLE seconds.

    Each bat is hidden until its own animation starts and between passes, so a
    viewer that does not animate sees the board without them.
    """
    out = ['<g class="bats">']
    for index in range(len(BATS)):
        # Wings level, head up: the silhouette everyone reads as a bat. The bob
        # animation banks it a few degrees either way as it crosses.
        out.append(f'<g class="fly{index}" opacity="0"><g class="bob{index}">'
                   f'<g transform="scale(1.5)">{BAT}</g></g></g>')
    out.append("</g>")
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
    out += bats()
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
