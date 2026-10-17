#!/usr/bin/env python3
"""Remove corner AI watermarks and add mild photographic imperfections.

Intended for images with a semi-transparent corner label (e.g. Doubao-style
bottom-right text). Keeps full resolution; does not regenerate scene content.

Parameters live in ``__main__`` (demo-style entry).
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def wipe_corner_watermark(
    bgr: np.ndarray,
    *,
    x_ratio: float = 0.805,
    y_ratio: float = 0.925,
) -> np.ndarray:
    """Replace bottom-right watermark band by cloning left texture + inpaint."""
    out = bgr.copy()
    h, w = out.shape[:2]
    x0, x1 = int(w * x_ratio), w
    y0, y1 = int(h * y_ratio), h
    bw, bh = x1 - x0, y1 - y0

    sx1 = x0 - 8
    sx0 = max(0, sx1 - bw)
    src = out[y0:y1, sx0:sx1]
    if src.shape[1] < bw:
        src = cv2.resize(src, (bw, bh), interpolation=cv2.INTER_LINEAR)
    else:
        src = src[:, -bw:]

    mask = np.zeros((bh, bw), np.float32)
    pad = 18
    mask[pad : bh - 2, pad : bw - 2] = 1.0
    mask = cv2.GaussianBlur(mask, (0, 0), 10)
    mask3 = mask[..., None]

    region = out[y0:y1, x0:x1].astype(np.float32)
    blended = region * (1 - mask3) + src.astype(np.float32) * mask3
    out[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)

    hard = np.zeros((h, w), np.uint8)
    hard[y0 + pad : y1 - 2, x0 + pad : x1 - 2] = 255
    hard = cv2.GaussianBlur(hard, (15, 15), 0)
    _, hard = cv2.threshold(hard, 40, 255, cv2.THRESH_BINARY)
    return cv2.inpaint(out, hard, 4, cv2.INPAINT_TELEA)


def _lf(h: int, w: int, scale: int, strength: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    gh, gw = max(3, h // scale), max(3, w // scale)
    small = rng.normal(0, 1, (gh, gw)).astype(np.float32)
    field = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
    field = cv2.GaussianBlur(field, (0, 0), sigmaX=max(3, scale / 2.2))
    field /= np.abs(field).max() + 1e-6
    return 1.0 + field * strength


def apply_deai(bgr: np.ndarray, seed: int = 0) -> np.ndarray:
    """Uneven exposure, mild grain, vignette, slight CA — less 'CGI clean'."""
    h, w = bgr.shape[:2]
    img = bgr.astype(np.float32)
    rng = np.random.default_rng(seed)

    img *= _lf(h, w, 65, 0.16, seed + 1)[..., None]
    img *= _lf(h, w, 130, 0.11, seed + 2)[..., None]
    img *= _lf(h, w, 35, 0.06, seed + 3)[..., None]

    xs = np.linspace(0, 1, w, dtype=np.float32)
    ys = np.linspace(0, 1, h, dtype=np.float32)
    xv, yv = np.meshgrid(xs, ys)
    shade = 1.0 - 0.09 * xv - 0.06 * (yv**1.15)
    warm = 0.035 * (xv - 0.35) + 0.02 * (yv - 0.45)
    img[..., 2] *= shade * (1 + warm)
    img[..., 1] *= shade * (1 + warm * 0.25)
    img[..., 0] *= shade * (1 - warm * 0.95)

    luma = 0.114 * img[..., 0] + 0.587 * img[..., 1] + 0.299 * img[..., 2]
    t = np.clip(luma / 255, 0, 1)
    t2 = 0.12 + 0.76 * t + 0.12 * (t * t)
    img *= ((t2 * 255) / (luma + 1e-3))[..., None]
    hi = np.clip((luma - 185) / 70, 0, 1)
    img = img * (1 - 0.16 * hi[..., None]) + 232 * (0.16 * hi[..., None])

    cy, cx = h / 2, w / 2
    rr = np.sqrt(((xv * w - cx) / (w * 0.8)) ** 2 + ((yv * h - cy) / (h * 0.8)) ** 2)
    vig = np.clip(1 - 0.24 * np.clip(rr - 0.48, 0, None) ** 1.25, 0.76, 1)
    img *= vig[..., None]

    gray = img.mean(axis=2, keepdims=True)
    img = gray + (img - gray) * 0.80
    img = np.clip(img, 0, 255).astype(np.uint8)

    soft = cv2.GaussianBlur(img, (0, 0), 1.0)
    img = cv2.addWeighted(img, 0.5, soft, 0.5, 0)

    luma2 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gmul = 1.0 + 0.7 * (1 - luma2 / 255)
    grain = rng.normal(0, 6.0, (h, w, 1)).astype(np.float32)
    chroma = rng.normal(0, 3.0, (h, w, 3)).astype(np.float32)
    out = np.clip(img.astype(np.float32) + grain * gmul[..., None] + chroma, 0, 255).astype(
        np.uint8
    )

    b, g, r = cv2.split(out)
    r = cv2.warpAffine(
        r, np.float32([[1, 0, 1.3], [0, 1, 0]]), (w, h), borderMode=cv2.BORDER_REFLECT
    )
    b = cv2.warpAffine(
        b, np.float32([[1, 0, -1.3], [0, 1, 0]]), (w, h), borderMode=cv2.BORDER_REFLECT
    )
    out = cv2.merge([b, g, r])
    return cv2.convertScaleAbs(out, alpha=0.91, beta=9)


def process_file(
    src: Path,
    out_dir: Path,
    *,
    seed: int = 0,
    also_jpg: bool = True,
) -> Path:
    bgr = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"cannot read image: {src}")
    cleaned = wipe_corner_watermark(bgr)
    final = apply_deai(cleaned, seed=seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem
    out_png = out_dir / f"{stem}_去水印实拍感.png"
    cv2.imwrite(str(out_png), final, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    if also_jpg:
        cv2.imwrite(
            str(out_dir / f"{stem}_去水印实拍感.jpg"),
            final,
            [cv2.IMWRITE_JPEG_QUALITY, 93],
        )
    only = out_dir / f"{stem}_仅去水印.png"
    cv2.imwrite(str(only), cleaned, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    return out_png


if __name__ == "__main__":
    # Edit these paths when reusing.
    INPUT_DIR = Path("<图片目录>")
    OUTPUT_DIR = INPUT_DIR / "处理后"
    FILES = ["公司门头.png", "办公室.png"]  # relative to INPUT_DIR
    SEED = 11

    for i, name in enumerate(FILES):
        process_file(INPUT_DIR / name, OUTPUT_DIR, seed=SEED + i * 12)
        print("ok", name)
