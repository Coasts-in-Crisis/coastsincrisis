#!/usr/bin/env python3
"""
Find precise pixel coordinates on a line-art image (transparent PNG with
a few solid colored strokes) — used repeatedly while placing the rotating
hurricane icons on the homepage map and on each pathway's background
image for coastsincrisis.net.

Why this exists: eyeballing "put the icon on the magenta line" from a
screenshot is unreliable — screenshots in this environment were
inconsistently scaled, and colors easily get second-guessed (this
project's source images turned out to have hurricane-name labels that
didn't match their actual rendered colors at all — "maria" was green,
"irma" was magenta). Sampling the actual PNG pixel data sidesteps both
problems: it's the ground truth, not a rendering of it.

Two things this script is careful about, learned the hard way on this
project:

1. Alpha matters. These images are ~90%+ fully transparent pixels whose
   leftover RGB channels are garbage (editing-tool artifacts). Naive RGB
   thresholding without checking alpha will "find" colors that aren't
   actually visible anywhere on the image.

2. Don't pick a point right at the line's edge. The very closest pixel
   to a target (e.g. "closest point on the line to the coastline") is
   often within 1px of a *different* color region (like adjacent
   landmass) — at different render sizes, sub-pixel rounding can flip
   which one actually gets sampled, making a "confirmed" placement look
   wrong again later. Always look for a point with several pixels of
   clearance from anything else, not just the single closest pixel.

Usage:
    # find and print all named-color regions on an image
    python3 find_line_position.py map.png --describe

    # find a point on a color, with margin from other colors and/or a
    # target point to be close to
    python3 find_line_position.py map.png --color magenta --near-to 78,936 --min-clearance 15
"""

import argparse
import sys
from collections import Counter

from PIL import Image

# Tuned for this project's line art (a handful of saturated marker-style
# colors on transparent backgrounds). Adjust thresholds for other images.
COLOR_TESTS = {
    "magenta": lambda r, g, b: r > 180 and b > 180 and g < 160,
    "yellow": lambda r, g, b: r > 180 and g > 180 and b < 120,
    "green": lambda r, g, b: g > 150 and r < 120 and b < 120,
    "gray": lambda r, g, b: abs(r - g) < 8 and abs(g - b) < 8 and 60 < r < 220,
}
ALPHA_THRESHOLD = 128


def classify(rgba: tuple[int, int, int, int]) -> str | None:
    r, g, b, a = rgba
    if a < ALPHA_THRESHOLD:
        return None  # transparent — ignore regardless of leftover RGB garbage
    for name, test in COLOR_TESTS.items():
        if test(r, g, b):
            return name
    return None


def find_color_points(img: Image.Image, color: str, step: int = 1) -> list[tuple[int, int]]:
    """All (x, y) pixels matching a named color. `step` subsamples for speed."""
    px = img.load()
    w, h = img.size
    points = []
    for y in range(0, h, step):
        for x in range(0, w, step):
            if classify(px[x, y]) == color:
                points.append((x, y))
    return points


def describe(img: Image.Image, step: int = 2) -> None:
    """Print a summary of every color region found — counts and bounding boxes."""
    px = img.load()
    w, h = img.size
    counts: Counter[str] = Counter()
    bboxes: dict[str, list[int]] = {}
    for y in range(0, h, step):
        for x in range(0, w, step):
            c = classify(px[x, y])
            if c is None:
                continue
            counts[c] += 1
            if c not in bboxes:
                bboxes[c] = [x, x, y, y]
            else:
                b = bboxes[c]
                b[0], b[1] = min(b[0], x), max(b[1], x)
                b[2], b[3] = min(b[2], y), max(b[3], y)

    print(f"image size: {w}x{h}")
    for color, count in counts.most_common():
        x0, x1, y0, y1 = bboxes[color]
        print(f"  {color:8s} ~{count:6d} px sampled   bbox x:[{x0},{x1}] y:[{y0},{y1}]")


def nearest_point(points: list[tuple[int, int]], target: tuple[int, int]) -> tuple[tuple[int, int], float]:
    tx, ty = target
    best, best_d = None, float("inf")
    for x, y in points:
        d = (x - tx) ** 2 + (y - ty) ** 2
        if d < best_d:
            best, best_d = (x, y), d
    return best, best_d**0.5


def clearance(point: tuple[int, int], other_points: list[tuple[int, int]]) -> float:
    """Distance from `point` to the nearest point in `other_points`."""
    _, dist = nearest_point(other_points, point)
    return dist


def find_point_with_clearance(
    img: Image.Image,
    color: str,
    min_clearance: float,
    near_to: tuple[int, int] | None = None,
    exclude_colors: list[str] | None = None,
    step: int = 1,
) -> tuple[int, int] | None:
    """A point on `color` that's at least `min_clearance` px from any of
    `exclude_colors` (default: every other detected color) — so the
    result is robust to sub-pixel rounding at different render sizes —
    optionally the one closest to `near_to`.
    """
    target_points = find_color_points(img, color, step=step)
    if not target_points:
        return None

    if exclude_colors is None:
        exclude_colors = [c for c in COLOR_TESTS if c != color]
    exclude_points: list[tuple[int, int]] = []
    for c in exclude_colors:
        exclude_points.extend(find_color_points(img, c, step=max(step, 2)))

    candidates = [
        p for p in target_points if not exclude_points or clearance(p, exclude_points) >= min_clearance
    ]
    if not candidates:
        return None

    if near_to is not None:
        best, _ = nearest_point(candidates, near_to)
        return best
    return candidates[len(candidates) // 2]  # otherwise just a representative point


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="path to a PNG with transparency")
    parser.add_argument("--describe", action="store_true", help="summarize all color regions found")
    parser.add_argument("--color", help="color to search: magenta, yellow, green, or gray")
    parser.add_argument("--near-to", help="x,y pixel coords to find the closest matching point to")
    parser.add_argument(
        "--min-clearance", type=float, default=0, help="required distance (px) from any other color"
    )
    parser.add_argument("--step", type=int, default=1, help="subsample step for speed on large images")
    args = parser.parse_args()

    img = Image.open(args.image).convert("RGBA")

    if args.describe:
        describe(img)
        return

    if not args.color:
        parser.print_help()
        sys.exit(1)

    near_to = None
    if args.near_to:
        x, y = args.near_to.split(",")
        near_to = (int(x), int(y))

    point = find_point_with_clearance(
        img, args.color, args.min_clearance, near_to=near_to, step=args.step
    )
    if point is None:
        print(f"no {args.color} point found with {args.min_clearance}px clearance", file=sys.stderr)
        sys.exit(1)

    w, h = img.size
    px = img.load()
    print(f"point: {point}")
    print(f"pixel color: {px[point[0], point[1]]}")
    print(f"as fraction of image size: {point[0]/w:.4f}, {point[1]/h:.4f}")
    print(f"as CSS percent: left: {point[0]/w*100:.2f}%; top: {point[1]/h*100:.2f}%;")


if __name__ == "__main__":
    _main()
