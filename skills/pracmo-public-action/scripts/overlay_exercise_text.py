#!/usr/bin/env python3
"""Overlay deterministic Chinese exercise text on a generated no-text image."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"


def draw_panel(draw: ImageDraw.ImageDraw, rect: list[int], radius: int = 22) -> None:
    x1, y1, x2, y2 = rect
    shadow = (20, 40, 42, 32)
    panel = (255, 252, 246, 236)
    stroke = (42, 125, 130, 230)
    draw.rounded_rectangle([x1 + 5, y1 + 7, x2 + 5, y2 + 7], radius=radius, fill=shadow)
    draw.rounded_rectangle(rect, radius=radius, fill=panel, outline=stroke, width=3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cue", required=True)
    parser.add_argument("--note", required=True)
    parser.add_argument("--sets", required=True)
    parser.add_argument("--reps", required=True)
    parser.add_argument("--tempo", required=True)
    args = parser.parse_args()

    img = Image.open(args.input).convert("RGBA")
    w, _ = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_label = ImageFont.truetype(FONT_PATH, 25)
    font_value = ImageFont.truetype(FONT_PATH, 26)
    primary = (35, 107, 111, 255)
    text_dark = (42, 57, 60, 255)
    muted = (66, 88, 92, 255)

    left = [54, 54, 430, 230]
    right = [w - 570, 54, w - 54, 206]
    draw_panel(draw, left)
    draw_panel(draw, right)

    lx, ly = left[0] + 28, left[1] + 22
    draw.text((lx, ly), "口诀", font=font_label, fill=primary)
    cue_lines = args.cue.split("|", 1)
    draw.text((lx + 76, ly), cue_lines[0], font=font_value, fill=text_dark)
    if len(cue_lines) > 1:
        draw.text((lx + 76, ly + 40), cue_lines[1], font=font_value, fill=text_dark)
    draw.text((lx, ly + 88), "注意", font=font_label, fill=primary)
    draw.text((lx + 76, ly + 88), args.note, font=font_value, fill=text_dark)

    rx, ry = right[0] + 30, right[1] + 22
    rows = [("组数", args.sets), ("每组", args.reps), ("节奏", args.tempo)]
    for i, (label, value) in enumerate(rows):
        y = ry + i * 42
        draw.text((rx, y), label, font=font_label, fill=primary)
        draw.text((rx + 76, y), value, font=font_value, fill=muted if label == "节奏" else text_dark)

    out = Image.alpha_composite(img, overlay).convert("RGB")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output, quality=95)


if __name__ == "__main__":
    main()
