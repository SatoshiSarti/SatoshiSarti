"""Turn tools/headshot.png into the card's scan-line portrait.

The portrait is 95 horizontal lines. Nothing is shaded: each line only gets
thicker or thinner along its length, and lifts by a pixel or two, following the
photo's luminance under it. On the dark card a line swells where the photo is
bright; on the light card it swells where the photo is dark, so both read as
the same picture instead of one being the other's negative.

    pip install -r tools/requirements.txt
    python3 tools/scanline.py            # writes portrait_dark.json, portrait_light.json
    python3 tools/scanline.py --preview  # also writes PNG previews beside them

The output is plain SVG path data, so the card builder needs no dependencies.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE = Path(__file__).resolve().parent
WIDTH, HEIGHT = 300, 380
PITCH = 4
ROWS = HEIGHT // PITCH
STEP = 2                      # one sample every 2 px along a line
#: Cream rows added above the photo: its hair nearly touches the top edge.
PAD_TOP = 60
BACKDROP = (251, 248, 242)
CENTER_X = 392                # middle of the head in the 800 px wide source
#: Line weight on the empty backdrop, and the range it sweeps on the subject.
THIN = 0.45
WEIGHT = {"dark": (0.6, 3.5), "light": (0.5, 3.3)}
GAMMA = {"dark": 1.5, "light": 1.15}
#: Share of the tone curve taken from the subject's own histogram. A face is a
#: narrow band of bright values; ranking them spreads that band over the whole
#: range of line weights, which is what makes eyes and mouth readable.
EQUALIZE = 0.65
LIFT = 1.2                    # px a line rises over the brightest skin
TOLERANCE = 0.08              # px of error allowed when dropping path points


def flood_from_border(candidate):
    """The part of `candidate` connected to the frame edge: the backdrop."""
    reached = np.zeros_like(candidate)
    reached[0], reached[-1] = candidate[0], candidate[-1]
    reached[:, 0], reached[:, -1] = candidate[:, 0], candidate[:, -1]
    while True:
        grown = reached.copy()
        grown[1:] |= reached[:-1]
        grown[:-1] |= reached[1:]
        grown[:, 1:] |= reached[:, :-1]
        grown[:, :-1] |= reached[:, 1:]
        grown &= candidate
        if grown.sum() == reached.sum():
            return grown
        reached = grown


def fields(source):
    """Per-pixel (subject coverage, luminance 0..1) at WIDTH by HEIGHT."""
    photo = Image.open(source).convert("RGB")
    padded = Image.new("RGB", (photo.width, photo.height + PAD_TOP), BACKDROP)
    padded.paste(photo, (0, PAD_TOP))
    crop_w = round(padded.height * WIDTH / HEIGHT)
    left = CENTER_X - crop_w // 2
    frame = padded.crop((left, 0, left + crop_w, padded.height))

    big = frame.resize((WIDTH * 2, HEIGHT * 2), Image.Resampling.LANCZOS)
    hsv = np.asarray(big.convert("HSV")).astype(int)
    backdrop = flood_from_border((hsv[..., 1] <= 30) & (hsv[..., 2] >= 225))
    subject = Image.fromarray((~backdrop * 255).astype(np.uint8))
    coverage = np.asarray(
        subject.resize((WIDTH, HEIGHT), Image.Resampling.BOX)
        .filter(ImageFilter.GaussianBlur(1.2))
    ) / 255.0

    gray = ImageOps.autocontrast(
        frame.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).convert("L"), cutoff=1
    )
    base = np.asarray(gray).astype(float)
    # Lift small features (eyes, brows, teeth) over the broad light and shade.
    blurred = np.asarray(gray.filter(ImageFilter.GaussianBlur(5))).astype(float)
    luminance = np.clip(base + 1.6 * (base - blurred), 0, 255) / 255.0
    inside = np.sort(luminance[coverage > 0.6])
    low, high = np.percentile(inside, 2), np.percentile(inside, 99)
    linear = np.clip((luminance - low) / max(high - low, 1e-6), 0, 1)
    ranked = np.searchsorted(inside, luminance) / len(inside)
    return coverage, EQUALIZE * ranked + (1 - EQUALIZE) * linear


def smooth(values, sigma=0.9):
    radius = int(sigma * 3)
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    padded = np.pad(values, radius, mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def simplify(points):
    """Ramer-Douglas-Peucker, so flat backdrop runs cost two points, not 150."""
    if len(points) < 3:
        return points
    (x0, y0), (x1, y1) = points[0], points[-1]
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    worst, index = 0.0, 0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        distance = abs(dy * (px - x0) - dx * (py - y0)) / length
        if distance > worst:
            worst, index = distance, i
    if worst <= TOLERANCE:
        return [points[0], points[-1]]
    return simplify(points[: index + 1])[:-1] + simplify(points[index:])


def number(value):
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def build(source, polarity):
    coverage, luminance = fields(source)
    low, high = WEIGHT[polarity]
    xs = np.arange(0, WIDTH + 1, STEP).clip(max=WIDTH - 1)
    rows = []
    for row in range(ROWS):
        band = slice(row * PITCH, (row + 1) * PITCH)
        cover = smooth(coverage[band].mean(axis=0))[xs]
        light = smooth(luminance[band].mean(axis=0))[xs]
        ink = light if polarity == "dark" else 1.0 - light
        weight = THIN + cover * (low + (ink ** GAMMA[polarity]) * (high - low) - THIN)
        center = row * PITCH + PITCH / 2 - LIFT * cover * light
        x_out = np.arange(0, WIDTH + 1, STEP)
        top = simplify(list(zip(x_out.tolist(), (center - weight / 2).tolist())))
        bottom = simplify(list(zip(x_out.tolist(), (center + weight / 2).tolist())))
        path = "M" + "L".join(f"{number(x)} {number(y)}" for x, y in top)
        path += "L" + "L".join(f"{number(x)} {number(y)}" for x, y in reversed(bottom))
        rows.append(path + "Z")
    return {"width": WIDTH, "height": HEIGHT, "pitch": PITCH, "rows": rows}


def preview(portrait, polarity, path):
    scale = 3
    surface, ink = (((11, 13, 16), (232, 236, 241)) if polarity == "dark"
                    else ((251, 251, 248), (20, 23, 27)))
    image = Image.new("RGB", (WIDTH * scale, HEIGHT * scale), surface)
    draw = ImageDraw.Draw(image)
    for row in portrait["rows"]:
        pairs = row[1:-1].split("L")
        points = [tuple(float(v) * scale for v in pair.split()) for pair in pairs]
        draw.polygon(points, fill=ink)
    image.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=HERE / "headshot.png")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    for polarity in ("dark", "light"):
        portrait = build(args.source, polarity)
        output = HERE / f"portrait_{polarity}.json"
        output.write_text(json.dumps(portrait) + "\n", encoding="utf-8")
        print(f"wrote {output} ({output.stat().st_size // 1024} KB)")
        if args.preview:
            preview(portrait, polarity, HERE / f"portrait_{polarity}.png")


if __name__ == "__main__":
    main()
