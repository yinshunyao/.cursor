#!/usr/bin/env python3
"""图像识别接单线：小红书深色笔记封面 + 微头条浅色资讯卡。

小红书 864×1152（3:4）；微头条 1280×720（16:9）。
禁止署名。字体优先 STHeiti。

用法：改 __main__ 后运行
  /Users/shunyaoyin/miniconda310/miniconda3/bin/python .cursor/tools/python/shibie-jiedan-cover.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

XHS_SIZE = (864, 1152)
WT_SIZE = (1280, 720)

# 小红书：深色笔记
XHS_BG = (28, 30, 36)
XHS_CARD = (38, 41, 50)
XHS_ACCENT = (232, 196, 120)
XHS_WHITE = (250, 250, 250)
XHS_MUTED = (168, 170, 178)
XHS_BAD = (220, 120, 110)
XHS_GOOD = (120, 190, 150)

# 微头条：浅色资讯
WT_BG = (244, 246, 248)
WT_CARD = (255, 255, 255)
WT_NAVY = (28, 48, 84)
WT_MUTED = (110, 120, 135)
WT_LINE = (210, 216, 224)
WT_BAD = (180, 70, 60)
WT_GOOD = (40, 120, 90)

FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    last: Exception | None = None
    for path in FONT_CANDIDATES:
        p = Path(path)
        if not p.exists():
            continue
        try:
            return ImageFont.truetype(str(p), size=size, index=0)
        except Exception as exc:  # noqa: BLE001
            last = exc
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception as exc2:  # noqa: BLE001
                last = exc2
    raise RuntimeError(f"no Chinese font; last={last}")


def _tw(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def _center_x(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, canvas_w: int) -> int:
    return (canvas_w - _tw(draw, text, font)) // 2


def _save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    print(f"wrote {path}")


def xhs_cover(out: Path) -> None:
    img = Image.new("RGB", XHS_SIZE, XHS_BG)
    d = ImageDraw.Draw(img)
    w, h = XHS_SIZE

    eyebrow = _font(28)
    title = _font(72)
    sub = _font(56)

    d.rounded_rectangle((48, 72, w - 48, h - 72), radius=28, outline=XHS_ACCENT, width=3)

    t1 = "说不清认出什么"
    t2 = "就别开工"
    tag = "图像识别 · 开工前先问清"

    y = 320
    d.text((_center_x(d, tag, eyebrow, w), y), tag, font=eyebrow, fill=XHS_MUTED)
    y = 420
    d.text((_center_x(d, t1, title, w), y), t1, font=title, fill=XHS_WHITE)
    y = 520
    d.text((_center_x(d, t2, sub, w), y), t2, font=sub, fill=XHS_ACCENT)

    bar_y = 640
    d.rectangle((w // 2 - 48, bar_y, w // 2 + 48, bar_y + 6), fill=XHS_ACCENT)

    tip = "口径糊着，后面全糊"
    tip_f = _font(32)
    d.text((_center_x(d, tip, tip_f, w), 720), tip, font=tip_f, fill=XHS_MUTED)

    _save(img, out)


def xhs_compare(out: Path) -> None:
    img = Image.new("RGB", XHS_SIZE, XHS_BG)
    d = ImageDraw.Draw(img)
    w, h = XHS_SIZE

    head = _font(40)
    body = _font(36)
    small = _font(28)

    title = "先问哪一句"
    d.text((_center_x(d, title, head, w), 80), title, font=head, fill=XHS_WHITE)

    left = (56, 200, w // 2 - 20, h - 160)
    d.rounded_rectangle(left, radius=20, fill=XHS_CARD, outline=XHS_BAD, width=3)
    d.text((left[0] + 36, 240), "先谈算法", font=body, fill=XHS_BAD)
    lines_l = ["用什么模型", "多久训完", "多少钱", "", "开口就问", "常把人往坑里带"]
    y = 330
    for line in lines_l:
        d.text((left[0] + 36, y), line, font=small, fill=XHS_MUTED)
        y += 56

    right = (w // 2 + 20, 200, w - 56, h - 160)
    d.rounded_rectangle(right, radius=20, fill=XHS_CARD, outline=XHS_GOOD, width=3)
    d.text((right[0] + 36, 240), "先谈认出什么", font=body, fill=XHS_GOOD)
    lines_r = ["认出什么", "错了谁挨骂", "图在哪拍的", "", "三句说不清", "就别开工"]
    y = 330
    for line in lines_r:
        d.text((right[0] + 36, y), line, font=small, fill=XHS_WHITE)
        y += 56

    foot = "说不清认出什么，就别开工"
    d.text((_center_x(d, foot, small, w), h - 100), foot, font=small, fill=XHS_ACCENT)
    _save(img, out)


def xhs_quote(out: Path) -> None:
    img = Image.new("RGB", XHS_SIZE, XHS_BG)
    d = ImageDraw.Draw(img)
    w, h = XHS_SIZE

    d.rounded_rectangle((64, 220, w - 64, h - 280), radius=24, fill=XHS_CARD, outline=XHS_ACCENT, width=2)

    quote_f = _font(48)
    lines = ["口径糊着开工，", "钱先烧，", "活后黄。"]
    y = 380
    for line in lines:
        d.text((_center_x(d, line, quote_f, w), y), line, font=quote_f, fill=XHS_WHITE)
        y += 90

    foot_f = _font(30)
    foot = "说不清认出什么，就别开工"
    d.text((_center_x(d, foot, foot_f, w), h - 180), foot, font=foot_f, fill=XHS_ACCENT)
    _save(img, out)


def wt_cover(out: Path) -> None:
    img = Image.new("RGB", WT_SIZE, WT_BG)
    d = ImageDraw.Draw(img)
    w, h = WT_SIZE

    d.rounded_rectangle((40, 40, w - 40, h - 40), radius=16, fill=WT_CARD, outline=WT_LINE, width=2)

    tag_f = _font(26)
    title_f = _font(56)
    sub_f = _font(40)

    tag = "图像识别 · 开工前先问清"
    d.text((80, 100), tag, font=tag_f, fill=WT_MUTED)

    t1 = "说不清认出什么，就别开工"
    d.text((80, 200), t1, font=title_f, fill=WT_NAVY)

    d.rectangle((80, 300, 200, 308), fill=WT_NAVY)

    tip = "口径糊着，后面全糊。钱先烧，活后黄。"
    d.text((80, 360), tip, font=sub_f, fill=WT_MUTED)
    _save(img, out)


def wt_compare(out: Path) -> None:
    img = Image.new("RGB", WT_SIZE, WT_BG)
    d = ImageDraw.Draw(img)
    w, h = WT_SIZE

    d.rounded_rectangle((40, 40, w - 40, h - 40), radius=16, fill=WT_CARD, outline=WT_LINE, width=2)

    head = _font(36)
    body = _font(32)
    small = _font(26)

    d.text((80, 80), "说不清 vs 说得清", font=head, fill=WT_NAVY)

    left = (80, 160, w // 2 - 30, h - 100)
    d.rounded_rectangle(left, radius=12, outline=WT_BAD, width=2)
    d.text((left[0] + 28, 190), "说不清", font=body, fill=WT_BAD)
    for i, line in enumerate(["白训一场", "测集好看", "现场对不上", "钱先烧"]):
        d.text((left[0] + 28, 270 + i * 50), line, font=small, fill=WT_MUTED)

    right = (w // 2 + 20, 160, w - 80, h - 100)
    d.rounded_rectangle(right, radius=12, outline=WT_GOOD, width=2)
    d.text((right[0] + 28, 190), "说得清", font=body, fill=WT_GOOD)
    for i, line in enumerate(["能验收", "能改松紧", "能接到系统", "活后黄的少"]):
        d.text((right[0] + 28, 270 + i * 50), line, font=small, fill=WT_NAVY)

    _save(img, out)


def wt_conclusion(out: Path) -> None:
    img = Image.new("RGB", WT_SIZE, WT_BG)
    d = ImageDraw.Draw(img)
    w, h = WT_SIZE

    d.rounded_rectangle((40, 40, w - 40, h - 40), radius=16, fill=WT_CARD, outline=WT_LINE, width=2)

    title_f = _font(52)
    sub_f = _font(32)

    line = "说不清认出什么，就别开工"
    d.text((_center_x(d, line, title_f, w), 250), line, font=title_f, fill=WT_NAVY)

    d.rectangle((w // 2 - 60, 340, w // 2 + 60, 346), fill=WT_NAVY)

    tip = "认出什么 · 错了谁挨骂 · 图在哪拍的"
    d.text((_center_x(d, tip, sub_f, w), 400), tip, font=sub_f, fill=WT_MUTED)
    _save(img, out)


def xhs_cover_20261009(out: Path) -> None:
    img = Image.new("RGB", XHS_SIZE, XHS_BG)
    d = ImageDraw.Draw(img)
    w, h = XHS_SIZE

    eyebrow = _font(26)
    title = _font(52)
    sub = _font(48)
    label = _font(28)
    body = _font(30)

    d.rounded_rectangle((40, 48, w - 40, h - 48), radius=28, outline=XHS_ACCENT, width=3)

    d.text((_center_x(d, "企业项目承接", eyebrow, w), 88), "企业项目承接", font=eyebrow, fill=XHS_MUTED)
    d.text((_center_x(d, "企业要识别和智能体", title, w), 140), "企业要识别和智能体", font=title, fill=XHS_WHITE)
    d.text((_center_x(d, "我接能上线的", sub, w), 214), "我接能上线的", font=sub, fill=XHS_ACCENT)

    d.text((88, 310), "对接客户", font=label, fill=XHS_ACCENT)
    customers = [
        "图像识别和缺陷检测",
        "智能体要能商用",
        "有预算，要进度，要质量",
    ]
    y = 362
    for line in customers:
        d.text((88, y), line, font=body, fill=XHS_WHITE)
        y += 52

    d.text((88, 560), "凭什么接", font=label, fill=XHS_ACCENT)
    advantages = [
        "一人端到端做完",
        "样本、训练、推理和 GPU/NPU",
        "数十人项目到独立交付",
        "质量和进度按合同管",
    ]
    y = 612
    for line in advantages:
        d.text((88, y), line, font=body, fill=XHS_WHITE)
        y += 52

    foot = "Nvidia · Jetson · 华为 · 瑞芯微"
    d.text((_center_x(d, foot, eyebrow, w), 920), foot, font=eyebrow, fill=XHS_MUTED)
    _save(img, out)


def wt_cover_20261009(out: Path) -> None:
    """浅色横卡。标题和两行要点居中，避开左右裁切。"""
    img = Image.new("RGB", WT_SIZE, WT_BG)
    d = ImageDraw.Draw(img)
    w, h = WT_SIZE

    d.rounded_rectangle((36, 28, w - 36, h - 28), radius=18, fill=WT_CARD, outline=WT_LINE, width=2)

    tag_f = _font(24)
    title_f = _font(46)
    line_f = _font(30)

    d.text((_center_x(d, "企业项目承接", tag_f, w), 88), "企业项目承接", font=tag_f, fill=WT_MUTED)
    d.text((_center_x(d, "企业要识别和智能体", title_f, w), 136), "企业要识别和智能体", font=title_f, fill=WT_NAVY)
    d.text((_center_x(d, "我接能上线的", title_f, w), 200), "我接能上线的", font=title_f, fill=WT_NAVY)
    d.rectangle((w // 2 - 64, 276, w // 2 + 64, 284), fill=WT_NAVY)

    rows = [
        "客户：识别和缺陷检测，智能体要商用",
        "还要有预算，要进度，要质量",
        "优势：一人做完，数十人项目到独立交付",
        "样本到推理，GPU/NPU 按现场上线",
    ]
    y = 330
    for line in rows:
        d.text((_center_x(d, line, line_f, w), y), line, font=line_f, fill=WT_NAVY)
        y += 52
    _save(img, out)


def xhs_cover_20261010(out: Path) -> None:
    img = Image.new("RGB", XHS_SIZE, XHS_BG)
    d = ImageDraw.Draw(img)
    w, h = XHS_SIZE

    eyebrow = _font(26)
    title = _font(52)
    sub = _font(48)
    label = _font(28)
    body = _font(30)

    d.rounded_rectangle((40, 48, w - 40, h - 48), radius=28, outline=XHS_ACCENT, width=3)

    d.text((_center_x(d, "工业质检承接", eyebrow, w), 88), "工业质检承接", font=eyebrow, fill=XHS_MUTED)
    d.text((_center_x(d, "缺陷检测要上工位", title, w), 148), "缺陷检测要上工位", font=title, fill=XHS_WHITE)
    d.text((_center_x(d, "测集不算交工", sub, w), 222), "测集不算交工", font=sub, fill=XHS_ACCENT)

    d.text((88, 320), "对接客户", font=label, fill=XHS_ACCENT)
    customers = [
        "产线或来料检缺陷",
        "要上工位或边端",
        "有预算，要进度，要质量",
    ]
    y = 372
    for line in customers:
        d.text((88, y), line, font=body, fill=XHS_WHITE)
        y += 52

    d.text((88, 560), "凭什么接", font=label, fill=XHS_ACCENT)
    advantages = [
        "一人从样本做到推理",
        "按现场 GPU 和 NPU 做",
        "松紧做成能改的参数",
        "质量和进度按合同管",
    ]
    y = 612
    for line in advantages:
        d.text((88, y), line, font=body, fill=XHS_WHITE)
        y += 52

    gate = "开工三句：叫什么，错了谁认，机器在哪"
    d.text((_center_x(d, gate, body, w), 880), gate, font=body, fill=XHS_ACCENT)

    foot = "Nvidia · Jetson · 华为 · 瑞芯微"
    d.text((_center_x(d, foot, eyebrow, w), 1000), foot, font=eyebrow, fill=XHS_MUTED)
    _save(img, out)


def wt_cover_20261010(out: Path) -> None:
    """浅色横卡。标题居中；客户 / 不接 / 凭什么用三条色带，避开左右裁切。"""
    img = Image.new("RGB", WT_SIZE, WT_BG)
    d = ImageDraw.Draw(img)
    w, h = WT_SIZE

    d.rounded_rectangle((36, 28, w - 36, h - 28), radius=18, fill=WT_CARD, outline=WT_LINE, width=2)

    tag_f = _font(24)
    title_f = _font(48)
    line_f = _font(32)

    d.text((_center_x(d, "工业质检承接", tag_f, w), 64), "工业质检承接", font=tag_f, fill=WT_MUTED)
    d.text((_center_x(d, "缺陷检测要上工位", title_f, w), 112), "缺陷检测要上工位", font=title_f, fill=WT_NAVY)
    d.text((_center_x(d, "测集不算交工", title_f, w), 176), "测集不算交工", font=title_f, fill=WT_NAVY)
    d.rectangle((w // 2 - 64, 252, w // 2 + 64, 260), fill=WT_NAVY)

    bands = [
        ((232, 238, 246), WT_NAVY, "客户：产线缺陷，要上工位或边端"),
        ((246, 236, 232), WT_BAD, "不接：测集好看，周末演示"),
        ((230, 240, 234), WT_GOOD, "凭什么：一人做完，按现场硬件"),
    ]
    y = 292
    for fill, color, text in bands:
        box = (160, y, w - 160, y + 96)
        d.rounded_rectangle(box, radius=14, fill=fill)
        tw = _tw(d, text, line_f)
        th = d.textbbox((0, 0), text, font=line_f)
        text_h = th[3] - th[1]
        tx = (w - tw) // 2
        ty = y + (96 - text_h) // 2 - 2
        d.text((tx, ty), text, font=line_f, fill=color)
        y += 112
    _save(img, out)


def render_20261010(root: Path) -> None:
    xhs_cover_20261010(root / "小红书" / "01_封面.png")
    wt_cover_20261010(root / "微头条" / "01_封面.png")


def render_20261009(root: Path) -> None:
    xhs_cover_20261009(root / "小红书" / "01_封面.png")
    wt_cover_20261009(root / "微头条" / "01_封面.png")


def render_20260930(root: Path) -> None:
    xhs = root / "小红书"
    wt = root / "微头条"
    xhs_cover(xhs / "01_封面.png")
    xhs_compare(xhs / "02_两句对照.png")
    xhs_quote(xhs / "03_收藏句.png")
    wt_cover(wt / "01_封面.png")
    wt_compare(wt / "02_对照.png")
    wt_conclusion(wt / "03_结论.png")


if __name__ == "__main__":
    OUT_ROOT = Path(
        "/Users/shunyaoyin/Documents/ai-company/study/介绍案例/"
        "图像识别智能体Web应用接单/文案_20261010_缺陷检测要上工位测集不算交工"
    )
    render_20261010(OUT_ROOT)
