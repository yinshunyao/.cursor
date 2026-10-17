#!/usr/bin/env python3
"""Cover matching words on an image (OCR boxes), optional title bar rewrite.

Designed for promo screenshot desensitization: blot brand tokens, redraw header.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def tesseract_tsv(image_path: Path) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        out_base = Path(tmp) / "ocr"
        subprocess.run(
            ["tesseract", str(image_path), str(out_base), "-l", "eng", "tsv"],
            check=True,
            capture_output=True,
        )
        tsv_path = Path(str(out_base) + ".tsv")
        rows = []
        lines = tsv_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if not lines:
            return rows
        headers = lines[0].split("\t")
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) < len(headers):
                continue
            item = dict(zip(headers, parts))
            text = (item.get("text") or "").strip()
            if not text:
                continue
            try:
                rows.append(
                    {
                        "text": text,
                        "left": int(item["left"]),
                        "top": int(item["top"]),
                        "width": int(item["width"]),
                        "height": int(item["height"]),
                        "conf": float(item.get("conf") or -1),
                    }
                )
            except (KeyError, ValueError):
                continue
        return rows


def match_boxes(rows: list[dict], patterns: list[re.Pattern]) -> list[tuple[int, int, int, int]]:
    boxes = []
    for row in rows:
        if row["conf"] < 0:
            continue
        for pat in patterns:
            if pat.search(row["text"]):
                pad = 4
                boxes.append(
                    (
                        max(0, row["left"] - pad),
                        max(0, row["top"] - pad),
                        row["left"] + row["width"] + pad,
                        row["top"] + row["height"] + pad,
                    )
                )
                break
    return boxes


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size, index=0)
            except OSError:
                continue
    return ImageFont.load_default()


def main() -> None:
    parser = argparse.ArgumentParser(description="Redact words on an image via OCR boxes")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--word",
        action="append",
        default=[],
        help="Word/regex to cover (case-insensitive). Repeatable.",
    )
    parser.add_argument("--fill", default="#F3EEE4", help="Cover fill color")
    parser.add_argument(
        "--title-bar",
        type=int,
        default=0,
        help="If >0, cover top N px of image and redraw --title-text",
    )
    parser.add_argument("--title-text", default="")
    parser.add_argument("--title-kicker", default="记录")
    parser.add_argument("--crop", default="", help="left,top,right,bottom optional crop")
    parser.add_argument("--max-width", type=int, default=0)
    args = parser.parse_args()

    words = args.word or ["Veo"]
    patterns = [re.compile(w, re.I) for w in words]

    src = Path(args.input)
    dst = Path(args.output)
    dst.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(src).convert("RGB")
    if args.crop:
        l, t, r, b = [int(x) for x in args.crop.split(",")]
        img = img.crop((l, t, r, b))

    # OCR on current (possibly cropped) image: write temp for tesseract
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        img.save(tmp_path)

    try:
        rows = tesseract_tsv(tmp_path)
        boxes = match_boxes(rows, patterns)
    finally:
        tmp_path.unlink(missing_ok=True)

    draw = ImageDraw.Draw(img)
    for box in boxes:
        draw.rectangle(box, fill=args.fill)

    if args.title_bar > 0:
        w, _ = img.size
        draw.rectangle((0, 0, w, args.title_bar), fill=args.fill)
        kicker_font = load_font(28)
        title_font = load_font(48)
        draw.text((48, 36), args.title_kicker, fill="#B08A5A", font=kicker_font)
        draw.text((48, 72), args.title_text or "需求评估记录", fill="#1A1A1A", font=title_font)

    if args.max_width and img.width > args.max_width:
        ratio = args.max_width / img.width
        img = img.resize((args.max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

    img.save(dst, quality=92)
    print(f"wrote {dst} covered={len(boxes)}")


if __name__ == "__main__":
    main()
