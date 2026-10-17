#!/usr/bin/env python3
"""专栏「怎么找到靠谱的软件开发」商务密排封面渲染。

小红书 864×1152（3:4）；头条 1280×720（16:9）。
字体优先 STHeiti Medium；配色炭灰底 + 金属金描边。

用法（IDE / 直接改 __main__ 变量后运行）：
  python .cursor/tools/python/zhaokaopu-business-cover.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

# —— 画幅 ——
XHS_SIZE = (864, 1152)
TT_SIZE = (1280, 720)

# —— 配色（对齐已出图篇）——
BG = (34, 37, 46)
CARD_BG = (40, 43, 52)
GOLD = (184, 161, 120)
WHITE = (254, 254, 254)
MUTED = (200, 198, 192)
GOLD_BAR_FG = (28, 28, 32)

FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]


def _font(size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    last_err: Exception | None = None
    for path in FONT_CANDIDATES:
        p = Path(path)
        if not p.exists():
            continue
        try:
            return ImageFont.truetype(str(p), size=size, index=index)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception as exc2:  # noqa: BLE001
                last_err = exc2
    raise RuntimeError(f"no usable Chinese font; last={last_err}")


def _text_w(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _text_h(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[3] - box[1]


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    """按字符折行（中文友好）。"""
    lines: list[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for ch in para:
            trial = cur + ch
            if _text_w(draw, trial, font) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def draw_lines(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    lines: Sequence[str],
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    line_gap: int,
) -> int:
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += _text_h(draw, line or "字", font) + line_gap
    return y


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    outline: tuple[int, int, int],
    width: int = 2,
    fill: tuple[int, int, int] | None = None,
) -> None:
    draw.rounded_rectangle(box, radius=radius, outline=outline, width=width, fill=fill)


def series_label(episode: int) -> str:
    return f"怎么找到靠谱的软件开发 · {episode:02d}"


def render_xhs_cover(
    out_path: Path,
    *,
    episode: int,
    title: str,
    title_underline: str | None,
    bullets: Sequence[str],
    gold_line: str,
    contrast: Sequence[tuple[str, str]],
    close_title: str,
    close_body: str,
) -> None:
    """小红书竖版：专栏名·篇号 / 小标题 / 要点 / 金句 / 对照两栏 / 收束。"""
    w, h = XHS_SIZE
    im = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(im)

    margin = int(w * 0.06)
    y = int(h * 0.035)

    f_series = _font(22)
    f_title = _font(48)
    f_body = _font(28)
    f_gold = _font(28)
    f_card_h = _font(26)
    f_card_b = _font(24)
    f_close_h = _font(26)
    f_close_b = _font(26)

    # 专栏名
    label = series_label(episode)
    lw = _text_w(draw, label, f_series)
    draw.text(((w - lw) // 2, y), label, font=f_series, fill=GOLD)
    y += _text_h(draw, label, f_series) + 22

    # 小标题（可折行）
    title_lines = wrap_text(draw, title, f_title, w - 2 * margin)
    for i, line in enumerate(title_lines):
        tw = _text_w(draw, line, f_title)
        tx = (w - tw) // 2
        draw.text((tx, y), line, font=f_title, fill=WHITE)
        if title_underline and title_underline in line:
            ux0 = tx + _text_w(draw, line[: line.index(title_underline)], f_title)
            ux1 = ux0 + _text_w(draw, title_underline, f_title)
            uy = y + _text_h(draw, line, f_title) + 6
            draw.line((ux0, uy, ux1, uy), fill=GOLD, width=3)
        y += _text_h(draw, line, f_title) + (18 if i == 0 else 10)
    y += 10

    # 要点
    for b in bullets:
        lines = wrap_text(draw, f"· {b}", f_body, w - 2 * margin)
        y = draw_lines(draw, (margin, y), lines, f_body, WHITE, 8)
        y += 6
    y += 14

    # 金句
    g_lines = wrap_text(draw, gold_line, f_gold, w - 2 * margin)
    for line in g_lines:
        gw = _text_w(draw, line, f_gold)
        draw.text(((w - gw) // 2, y), line, font=f_gold, fill=GOLD)
        y += _text_h(draw, line, f_gold) + 8
    y += 18

    # 对照两栏
    gap = 16
    card_w = (w - 2 * margin - gap) // 2
    card_top = y
    # 先量高度
    card_pad = 16
    heights: list[int] = []
    wrapped_cards: list[tuple[list[str], list[str]]] = []
    for head, body in contrast:
        hl = wrap_text(draw, head, f_card_h, card_w - 2 * card_pad)
        bl = wrap_text(draw, body, f_card_b, card_w - 2 * card_pad)
        wrapped_cards.append((hl, bl))
        ch = card_pad
        for line in hl:
            ch += _text_h(draw, line, f_card_h) + 6
        ch += 8
        for line in bl:
            ch += _text_h(draw, line, f_card_b) + 6
        ch += card_pad
        heights.append(ch)
    card_h = max(heights)
    for i, (hl, bl) in enumerate(wrapped_cards):
        x0 = margin + i * (card_w + gap)
        box = (x0, card_top, x0 + card_w, card_top + card_h)
        rounded_rect(draw, box, 10, GOLD, 2, fill=CARD_BG)
        cy = card_top + card_pad
        cy = draw_lines(draw, (x0 + card_pad, cy), hl, f_card_h, GOLD, 6)
        cy += 8
        draw_lines(draw, (x0 + card_pad, cy), bl, f_card_b, WHITE, 6)
    y = card_top + card_h + 18

    # 收束卡
    close_pad = 18
    cl_h = wrap_text(draw, close_title, f_close_h, w - 2 * margin - 2 * close_pad)
    cl_b = wrap_text(draw, close_body, f_close_b, w - 2 * margin - 2 * close_pad)
    close_h = close_pad
    for line in cl_h:
        close_h += _text_h(draw, line, f_close_h) + 6
    close_h += 10
    for line in cl_b:
        close_h += _text_h(draw, line, f_close_b) + 6
    close_h += close_pad
    # 若底部还有空间，卡片贴内容即可，不硬拉满
    box = (margin, y, w - margin, y + close_h)
    rounded_rect(draw, box, 10, GOLD, 2, fill=CARD_BG)
    cy = y + close_pad
    cy = draw_lines(draw, (margin + close_pad, cy), cl_h, f_close_h, GOLD, 6)
    cy += 10
    draw_lines(draw, (margin + close_pad, cy), cl_b, f_close_b, WHITE, 6)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, "PNG")


def render_tt_cover(
    out_path: Path,
    *,
    episode: int,
    title: str,
    title_underline: str | None,
    subtitle: str | None,
    cards: Sequence[tuple[str, Sequence[str]]],
    footer: str | None = None,
    layout: str = "two_col",
) -> None:
    """头条 16:9。layout: two_col | stack | three_row。"""
    w, h = TT_SIZE
    im = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(im)

    margin = 48
    y = 28

    f_series = _font(20)
    f_title = _font(42)
    f_sub = _font(24)
    f_card_h = _font(24)
    f_card_b = _font(22)
    f_footer = _font(24)

    label = series_label(episode)
    draw.text((margin, y), label, font=f_series, fill=GOLD)
    y += _text_h(draw, label, f_series) + 14

    title_lines = wrap_text(draw, title, f_title, w - 2 * margin)
    for line in title_lines:
        draw.text((margin, y), line, font=f_title, fill=WHITE)
        if title_underline and title_underline in line:
            ux0 = margin + _text_w(draw, line[: line.index(title_underline)], f_title)
            ux1 = ux0 + _text_w(draw, title_underline, f_title)
            uy = y + _text_h(draw, line, f_title) + 5
            draw.line((ux0, uy, ux1, uy), fill=GOLD, width=3)
        y += _text_h(draw, line, f_title) + 8

    if subtitle:
        for line in wrap_text(draw, subtitle, f_sub, w - 2 * margin):
            draw.text((margin, y), line, font=f_sub, fill=MUTED)
            y += _text_h(draw, line, f_sub) + 6
    y += 14

    footer_h = 0
    if footer:
        footer_h = 56
    area_bottom = h - margin - footer_h - (8 if footer else 0)
    area_top = y
    area_h = area_bottom - area_top
    gap = 16
    pad = 16

    def measure_card(head: str, body: Sequence[str], cw: int) -> tuple[int, list[str], list[str]]:
        hl = wrap_text(draw, head, f_card_h, cw - 2 * pad)
        bl: list[str] = []
        for b in body:
            bl.extend(wrap_text(draw, b, f_card_b, cw - 2 * pad))
        ch = pad
        for line in hl:
            ch += _text_h(draw, line, f_card_h) + 5
        ch += 8
        for line in bl:
            ch += _text_h(draw, line, f_card_b) + 5
        ch += pad
        return ch, hl, bl

    def paint_card(box: tuple[int, int, int, int], hl: list[str], bl: list[str]) -> None:
        rounded_rect(draw, box, 10, GOLD, 2, fill=CARD_BG)
        cy = box[1] + pad
        cy = draw_lines(draw, (box[0] + pad, cy), hl, f_card_h, GOLD, 5)
        cy += 8
        draw_lines(draw, (box[0] + pad, cy), bl, f_card_b, WHITE, 5)

    n = len(cards)
    if layout == "two_col" and n == 2:
        cw = (w - 2 * margin - gap) // 2
        measured = [measure_card(h0, b0, cw) for h0, b0 in cards]
        ch = min(max(m[0] for m in measured), area_h)
        for i, (_, hl, bl) in enumerate(measured):
            x0 = margin + i * (cw + gap)
            paint_card((x0, area_top, x0 + cw, area_top + ch), hl, bl)
    elif layout == "left_stack_right" and n >= 2:
        # 左栏多卡均分高度，右栏通高（文案4-02 风格）
        left_cards = cards[:-1]
        right = cards[-1]
        left_w = int((w - 2 * margin - gap) * 0.52)
        right_w = w - 2 * margin - gap - left_w
        left_gap = 12
        measured_l = [measure_card(h0, b0, left_w) for h0, b0 in left_cards]
        n_left = len(measured_l)
        each_h = (area_h - left_gap * (n_left - 1)) // max(n_left, 1)
        cy = area_top
        for _, hl, bl in measured_l:
            paint_card((margin, cy, margin + left_w, cy + each_h), hl, bl)
            cy += each_h + left_gap
        _, rhl, rbl = measure_card(right[0], right[1], right_w)
        paint_card(
            (
                margin + left_w + gap,
                area_top,
                margin + left_w + gap + right_w,
                area_top + area_h,
            ),
            rhl,
            rbl,
        )
    elif layout in ("two_over_one", "two_over_one_tight") and n == 3:
        cw = (w - 2 * margin - gap) // 2
        top_measured = [measure_card(h0, b0, cw) for h0, b0 in cards[:2]]
        bot_measured = measure_card(cards[2][0], cards[2][1], w - 2 * margin)
        natural_top = max(m[0] for m in top_measured)
        natural_bot = bot_measured[0]
        natural_total = natural_top + gap + natural_bot
        if layout == "two_over_one_tight" or natural_total >= area_h:
            if natural_total < area_h:
                top_h = natural_top
                bot_h = natural_bot
            else:
                scale = area_h / natural_total
                top_h = max(int(natural_top * scale), 90)
                bot_h = area_h - top_h - gap
        elif natural_total < area_h:
            # 旧版：多余高度分给底卡。新篇用 two_over_one_tight，避免空框拉满。
            extra = area_h - natural_total
            top_h = natural_top
            bot_h = natural_bot + extra
        else:
            scale = area_h / natural_total
            top_h = max(int(natural_top * scale), 90)
            bot_h = area_h - top_h - gap
        for i, (_, hl, bl) in enumerate(top_measured):
            x0 = margin + i * (cw + gap)
            paint_card((x0, area_top, x0 + cw, area_top + top_h), hl, bl)
        _, hl, bl = bot_measured
        paint_card(
            (margin, area_top + top_h + gap, w - margin, area_top + top_h + gap + bot_h),
            hl,
            bl,
        )
    else:
        # stack：纵向均分
        ch = (area_h - gap * (n - 1)) // max(n, 1)
        cw = w - 2 * margin
        cy = area_top
        for head, body in cards:
            _, hl, bl = measure_card(head, body, cw)
            paint_card((margin, cy, margin + cw, cy + ch), hl, bl)
            cy += ch + gap

    if footer:
        bar_top = h - footer_h
        draw.rectangle((0, bar_top, w, h), fill=GOLD)
        flines = wrap_text(draw, footer, f_footer, w - 2 * margin)
        # 垂直居中一行或两行
        total = sum(_text_h(draw, ln, f_footer) + 4 for ln in flines) - 4
        fy = bar_top + (footer_h - total) // 2
        for line in flines:
            fw = _text_w(draw, line, f_footer)
            draw.text(((w - fw) // 2, fy), line, font=f_footer, fill=GOLD_BAR_FG)
            fy += _text_h(draw, line, f_footer) + 4

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, "PNG")


def render_article5(base_dir: Path) -> list[Path]:
    """文案5：里程碑要对上付款。结构：问题 → 分析 → 解答。"""
    xhs_dir = base_dir / "小红书"
    tt_dir = base_dir / "头条"
    outs: list[Path] = []

    p = xhs_dir / "01_封面.png"
    render_xhs_cover(
        p,
        episode=5,
        title="里程碑要对上付款",
        title_underline="要对上付款",
        bullets=[
            "口头「大概下个月」不够，说不清那天该交什么",
            "里程碑三件套：计划时间、交付物、验收标准",
            "小项目至少留一个中期点，或一次 Demo 验收",
            "大项目可按特性拆细——那是能力，不是省略检查点的借口",
        ],
        gold_line="点过了，再对应付款。别只有付款日、没有交付物。",
        contrast=[
            (
                "勤付款、交付含糊",
                "节点写得勤，交什么却说不清，钱出去大半才发现偏了。",
            ),
            (
                "尾款才总验收",
                "一路干到结尾才见面；前面偏了，双方都疼。",
            ),
        ],
        close_title="收束",
        close_body="先核心做一版，落成能检查、能付款的点。点立住了，范围外的变更谁出钱、维护谁扛，才画得清。",
    )
    outs.append(p)

    p = tt_dir / "01_封面.png"
    render_tt_cover(
        p,
        episode=5,
        title="口头「大概下个月」不够",
        title_underline="大概下个月",
        subtitle="合作还没签字，最容易随口定一个上线日",
        cards=[
            (
                "听起来有进度",
                [
                    "真到扯皮时，谁也说不清那一天该交出什么。",
                    "可演示？可试用？可上线？差一个字，全是误会。",
                ],
            ),
            (
                "各说各话的根",
                [
                    "你以为对方懂你的「差不多」；",
                    "对方以为你接受他的「先这样」。",
                    "延期、没做完，都会变成各说各话。",
                ],
            ),
        ],
        footer="缺的不是更勤的催进度，是能回答三件事的里程碑。",
        layout="two_col",
    )
    outs.append(p)

    p = tt_dir / "02_三件套.png"
    render_tt_cover(
        p,
        episode=5,
        title="三件套，再加一个能停下的点",
        title_underline="三件套",
        subtitle=None,
        cards=[
            ("计划与时间", ["什么时候交，写进计划，不要停在口头。"]),
            ("交付物", ["那天到底交出什么：演示、试用，还是可上线。"]),
            ("验收标准", ["怎样算过——缺一条，后面全是各说各话。"]),
            (
                "小项目也要中途点",
                [
                    "不必堆成大厂排期表，至少一次中期检查或 Demo。",
                    "没有中途点，等于把风险全堆到结尾那一次见面。",
                ],
            ),
        ],
        footer=None,
        layout="left_stack_right",
    )
    outs.append(p)

    p = tt_dir / "03_付款绑定.png"
    render_tt_cover(
        p,
        episode=5,
        title="钱跟着点走",
        title_underline="钱跟着点走",
        subtitle="里程碑过了，才对应付款",
        cards=[
            (
                "两种别扭",
                [
                    "付款节点很勤，交付物却含糊；",
                    "或者一路干到尾款，才做唯一一次总验收。",
                ],
            ),
            (
                "纠正的代价",
                [
                    "前面已经偏了，钱却出去大半。",
                    "再想纠正，双方都疼。",
                ],
            ),
            (
                "收束动作",
                [
                    "先核心做一版，落成能检查、能付款的点。",
                    "点立住了，变更谁出钱、维护谁扛、BUG 算不算免费，才画得出来。",
                    "否则连「范围外」都画不出来。",
                ],
            ),
        ],
        footer=None,
        layout="two_over_one",
    )
    outs.append(p)

    return outs


def render_article6(base_dir: Path) -> list[Path]:
    """文案6：变更维护写进合同。结构：问题 → 分析 → 解答。"""
    xhs_dir = base_dir / "小红书"
    tt_dir = base_dir / "头条"
    outs: list[Path] = []

    p = xhs_dir / "01_封面.png"
    render_xhs_cover(
        p,
        episode=6,
        title="变更维护写进合同",
        title_underline="写进合同",
        bullets=[
            "很多人只谈「做出来多少钱」，上线后谁改、谁值守，合同空白",
            "变更和维护，梳理需求时就要想，别事后靠口头情分",
            "自己养人：交接培训写清；继续外包养：方式、节奏、预算谈清",
            "BUG 一般免费修；功能变更另算——量大，对方也不会白做",
        ],
        gold_line="分界提前说，少打架。",
        contrast=[
            (
                "凡改都免费",
                "做的人会被小改拖死，最后只能硬加价或甩锅。",
            ),
            (
                "凡问题都加钱",
                "买方被一点点敲；连真 BUG 也变成讨价还价。",
            ),
        ],
        close_title="收束",
        close_body="检查点、付款点立住之后，范围外的规则也要立住。再往下：定制要不要源码、权利归谁——不谈清楚，维护和二开都会悬空。",
    )
    outs.append(p)

    p = tt_dir / "01_封面.png"
    render_tt_cover(
        p,
        episode=6,
        title="签的是上线，漏的是上线之后",
        title_underline="上线之后",
        subtitle="谈判桌上最热的是开发价和工期",
        cards=[
            (
                "松口气之后",
                [
                    "真正磨人的，往往是上线之后：",
                    "小改不断、值班谁来、需求又变一截。",
                ],
            ),
            (
                "空白的代价",
                [
                    "想得晚，合同里就空白；",
                    "空白一久，只能靠口头情分。",
                    "情分一薄，就开始计价吵架。",
                ],
            ),
        ],
        footer="你以为买的是交付物，其实买的是还要继续活着的系统。",
        layout="two_col",
    )
    outs.append(p)

    p = tt_dir / "02_两条维护路.png"
    render_tt_cover(
        p,
        episode=6,
        title="两条维护路，别混着谈",
        title_underline="别混着谈",
        subtitle=None,
        cards=[
            (
                "自己有人维护",
                [
                    "交接和培训必须约定。",
                    "否则源码扔过来也接不住。",
                ],
            ),
            (
                "维护继续外包",
                [
                    "维护方式、响应节奏、预算，都要谈清。",
                    "谈完写进合同，别临上线靠人情。",
                ],
            ),
            (
                "混谈才会惨",
                [
                    "两种路没有高下，混着谈才会惨——",
                    "你以为对方养着，对方以为你自己有人。",
                ],
            ),
        ],
        footer=None,
        layout="two_over_one",
    )
    outs.append(p)

    p = tt_dir / "03_BUG与变更.png"
    render_tt_cover(
        p,
        episode=6,
        title="BUG 和功能变更不是一类账单",
        title_underline="不是一类账单",
        subtitle="分界写早，比事后吵「这算不算 BUG」省事",
        cards=[
            (
                "BUG：类似售后",
                [
                    "一般来说需要免费解决。",
                    "这是质量承诺，不是人情。",
                ],
            ),
            (
                "功能变更：视情况",
                [
                    "范围外、工作量明显变大，",
                    "外包方不会、也不该默认免费扛。",
                ],
            ),
            (
                "收束动作",
                [
                    "两端都危险：凡改都免费会拖死做的人；凡问题都加钱会敲买方。",
                    "分界写进合同。再往下还得问：定制要不要源码，权利归谁。",
                ],
            ),
        ],
        footer=None,
        layout="two_over_one",
    )
    outs.append(p)

    return outs


def render_article7(base_dir: Path) -> list[Path]:
    """文案7：定制要源码才能二开。结构：问题 → 分析 → 解答。"""
    xhs_dir = base_dir / "小红书"
    tt_dir = base_dir / "头条"
    outs: list[Path] = []

    p = xhs_dir / "01_封面.png"
    render_xhs_cover(
        p,
        episode=7,
        title="定制要源码才能二开",
        title_underline="才能二开",
        bullets=[
            "定制项目，默认要源码——不然二开、换人、排障都会卡死",
            "文档也要约定：用户手册、部署手册是底",
            "小项目可瘦身：源码加两本手册，往往就能交接",
            "主要买产品、定制很少：通常不强求源码，那更像用商品",
        ],
        gold_line="先分清买的是工程还是商品，再开口要交付物。",
        contrast=[
            (
                "定制却不交源码",
                "今天合作愉快，人不在了就等于没有退路。",
            ),
            (
                "买产品却压全套",
                "按「全套源码+全套设计」去压，也不匹配。",
            ),
        ],
        close_title="收束",
        close_body="源码和手册谈清，只是文件层。软著、专利登记在谁名下，是另一层——硬盘有文件，不等于权利在你这。",
    )
    outs.append(p)

    p = tt_dir / "01_封面.png"
    render_tt_cover(
        p,
        episode=7,
        title="没有源码，后面全是求人",
        title_underline="全是求人",
        subtitle="定制项目：源码是为了以后还能动",
        cards=[
            (
                "二开 / 换人 / 排障",
                [
                    "没有源码，后续都会变成求人。",
                    "今天合作愉快，不代表明天还是同一拨人。",
                ],
            ),
            (
                "退路在纸上",
                [
                    "人一换，没有源码就等于没有退路。",
                    "要源码不是仪式感，是可改造性。",
                ],
            ),
        ],
        footer="一般的定制项目，我会默认要求源码交付。",
        layout="two_col",
    )
    outs.append(p)

    p = tt_dir / "02_文档可精简.png"
    render_tt_cover(
        p,
        episode=7,
        title="文档是交付的一部分，可按体量裁",
        title_underline="可按体量裁",
        subtitle=None,
        cards=[
            (
                "常见底线",
                [
                    "用户手册、部署手册。",
                    "大项目还常要需求说明、设计、测试报告。",
                ],
            ),
            (
                "小项目瘦身",
                [
                    "不必堆全套大厂目录。",
                    "源码加用户手册、部署手册，很多时候已够交接。",
                ],
            ),
            (
                "别为了显得正规",
                [
                    "要求越多，越要和预算、工期匹配。",
                    "堆一堆没人看的文档，不等于交接更稳。",
                ],
            ),
        ],
        footer=None,
        layout="two_over_one",
    )
    outs.append(p)

    p = tt_dir / "03_定制vs产品.png"
    render_tt_cover(
        p,
        episode=7,
        title="定制与买产品，别混着谈",
        title_underline="别混着谈",
        subtitle="先分清自己买的是工程还是商品",
        cards=[
            (
                "定制：按工程买",
                [
                    "要源码，为了以后还能改。",
                    "对方交付的是可改造的工程。",
                ],
            ),
            (
                "买产品：按商品用",
                [
                    "定制很少时，一般不强求源码。",
                    "对方卖的是可用性，不是你的可改造性。",
                ],
            ),
            (
                "收束动作",
                [
                    "定制单却不交源码，后面疼；买标准产品却压全套源码，也不匹配。",
                    "文件谈清之后，还要单独问：软著、专利归谁。",
                ],
            ),
        ],
        footer=None,
        layout="two_over_one",
    )
    outs.append(p)

    return outs


def render_article8(base_dir: Path) -> list[Path]:
    """文案8：软著专利别忘谈归属。结构：问题 → 分析 → 解答。"""
    xhs_dir = base_dir / "小红书"
    tt_dir = base_dir / "头条"
    outs: list[Path] = []

    p = xhs_dir / "01_封面.png"
    render_xhs_cover(
        p,
        episode=8,
        title="软著专利别忘谈归属",
        title_underline="谈归属",
        bullets=[
            "很多人只问源码交不交，软著专利这层常被滑过去",
            "软著、专利，有时还有论文相关成果，是另一层权利",
            "成熟一点的企业，会把软著和专利所属权谈死",
            "源码是文件；权利是登记在谁名下——分开谈，少事后补",
        ],
        gold_line="硬盘里有源码，不等于权利在你这。",
        contrast=[
            (
                "只谈文件交付",
                "合同只写交不交源码，登记归谁空白。",
            ),
            (
                "事后才补权属",
                "要用时才发现从没写过；补起来贵，关系也僵。",
            ),
        ],
        close_title="收束",
        close_body="文件交付和权利归属是两件事，合作前都要落到纸上。约束谈清，不保证找对人；但不谈，找对人之后也可能在权属上翻车。",
    )
    outs.append(p)

    p = tt_dir / "01_封面.png"
    render_tt_cover(
        p,
        episode=8,
        title="谈判常停在「源码给不给」",
        title_underline="源码给不给",
        subtitle="另一层更容易被滑过去：知识产权",
        cards=[
            (
                "容易漏掉的一层",
                [
                    "软著、专利，有时还有论文署名。",
                    "特别是软著和专利，成熟企业会要求所属权归己方。",
                ],
            ),
            (
                "你以为 vs 登记上",
                [
                    "你以为「东西是我定的」；",
                    "登记上却可能是别的名字。",
                    "融资、答辩、防扯皮时真的用得上。",
                ],
            ),
        ],
        footer="硬盘里有源码，不等于权利在你这。",
        layout="two_col",
    )
    outs.append(p)

    p = tt_dir / "02_为何容易忽略.png"
    render_tt_cover(
        p,
        episode=8,
        title="为什么这层容易被忽略",
        title_underline="容易被忽略",
        subtitle=None,
        cards=[
            (
                "双方都急着关单",
                [
                    "研发忙着交付，商务忙着关单。",
                    "两边都觉得：先把东西做出来。",
                ],
            ),
            (
                "用得上才发现空",
                [
                    "等要用软著证明权属，或专利要布局时，",
                    "才发现合同里从没写过归谁。",
                ],
            ),
            (
                "事后补的成本",
                [
                    "那时再补，成本高得多。",
                    "关系也更容易僵——不是代办流程课，是提醒早点写死。",
                ],
            ),
        ],
        footer=None,
        layout="two_over_one",
    )
    outs.append(p)

    p = tt_dir / "03_文件与权利分开.png"
    render_tt_cover(
        p,
        episode=8,
        title="文件一层，权利一层",
        title_underline="权利一层",
        subtitle="合作前都要落到纸上",
        cards=[
            (
                "源码 / 手册",
                [
                    "谈的是交不交、交到哪一档。",
                    "硬盘丢了可以再拷。",
                ],
            ),
            (
                "软著 / 专利",
                [
                    "谈的是登记在谁名下。",
                    "权属没写清，补起来贵得多。",
                ],
            ),
            (
                "收束动作",
                [
                    "我不教你怎么代办软著——只提醒：两件事分开谈。",
                    "约束谈清，不保证找对人；但不谈，找对人后也可能在权属上翻车。",
                    "再往下看人：技术答得溜，不等于诚实。",
                ],
            ),
        ],
        footer=None,
        layout="two_over_one",
    )
    outs.append(p)

    return outs


def render_pack(base_dir: Path, episode: int, xhs: dict, tt: Sequence[dict]) -> list[Path]:
    """按规格渲染一篇：小红书 1 张 + 头条 3 张。"""
    outs: list[Path] = []
    p = base_dir / "小红书" / "01_封面.png"
    render_xhs_cover(p, episode=episode, **xhs)
    outs.append(p)
    for item in tt:
        spec = dict(item)
        name = spec.pop("file")
        p = base_dir / "头条" / name
        render_tt_cover(p, episode=episode, **spec)
        outs.append(p)
    return outs


# 文案9～19。结构均为：问题 → 分析 → 解答。三张头条互不复述。
ARTICLE_PACKS: list[tuple[str, int, dict, list]] = [
    (
        "文案9_20260926_技术诚实是评价研发第一条",
        9,
        {
            "title": "技术诚实是第一条",
            "title_underline": "是第一条",
            "bullets": [
                "答得特别满、敢当场拍板，听着专业，未必托付得起",
                "不要求什么都懂；明知没把握还打包票，坑多半是你的",
                "犯错能接受；糊弄不行——坑被盖住，买方买单",
                "会说「这块我不确定，要查一下」，比演成百科更值钱",
            ],
            "gold_line": "知不知说真话，比演成全知更接近可合作。",
            "contrast": [
                ("当场把话说死", "不确定被盖住。延期、返工、甩锅，往往从这里起。"),
                ("把边界说出来", "「要查一下」不丢人。被追问时补边界，而不是说得更满。"),
            ],
            "close_title": "收束",
            "close_body": "诚实是底线。底线过了，还要看他听不听得进别人的约束。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "答得越满，越要留个心眼",
                "title_underline": "留个心眼",
                "subtitle": "问两句就能答到底，会议室里很加分",
                "cards": [
                    ("听着很定", ["语气专业，当场就能拍板。", "这种人短期最像「靠谱」。"]),
                    ("少听的那一句", ["他有没有把不确定说出来。", "没说出来，满，可能是演的。"]),
                ],
                "footer": "全知的表演，短期像专业，长期像陷阱。",
                "layout": "two_col",
            },
            {
                "file": "02_听得出来.png",
                "title": "诚实是能听出来的",
                "title_underline": "听出来",
                "subtitle": None,
                "cards": [
                    ("这几句不丢人", ["「不确定。」", "「我要查一下。」", "「建议先验证。」"]),
                    ("被追问时", ["一种人补充边界。", "另一种人把话说得更满。"]),
                    ("接近可合作", ["一线对接也靠不装懂。", "比当场演成百科，更接近能一起干活。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_底线.png",
                "title": "不要求全知，要求说真话",
                "title_underline": "说真话",
                "subtitle": "评价研发，我把技术诚实放第一条",
                "cards": [
                    ("明知不知还打包票", ["后面的坑，多半转到买方这边。", "话说死，比不会更危险。"]),
                    ("犯错和糊弄", ["犯错可以接受，技术活谁都踩坑。", "糊弄不可接受，坑被盖住才是账单。"]),
                    ("底线之后", ["诚实过了，还要看改不改得动。", "技术硬、谁也说不动，交付一样上不去。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案10_20260926_技术过硬但听不进反而不靠谱",
        10,
        {
            "title": "听不进的别当靠谱",
            "title_underline": "别当靠谱",
            "bullets": [
                "技术硬，不等于靠谱；代码可以，协作可以很难",
                "异议上来先辩赢，把「有主见」演成「谁也说不动」",
                "跨团队一对齐，交付就掉细节",
                "会说真话，和听得进、改得动，是两件事",
            ],
            "gold_line": "理性沟通是底色，不是加分项。",
            "contrast": [
                ("有主见", "可以坚持判断，同时仍把别人的约束听进去。"),
                ("听不进", "会议上他赢了，项目上你可能输了。"),
            ],
            "close_title": "收束",
            "close_body": "别揉成一句「态度好不好」。听得进的人，才有机会把第一版打磨成可交的东西。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "硬，但推不动",
                "title_underline": "推不动",
                "subtitle": "只比技术深度，会漏掉一类人",
                "cards": [
                    ("代码可以", ["强势、自信过了头。", "异议上来，先辩赢。"]),
                    ("卡点不在会写", ["返工、接口扯皮、验收拉锯，", "常常卡在谁也说不动。"]),
                ],
                "footer": "你以为在讨论方案，他以为在打输赢。",
                "layout": "two_col",
            },
            {
                "file": "02_强势不是主见.png",
                "title": "强势不等于有主见",
                "title_underline": "不等于有主见",
                "subtitle": None,
                "cards": [
                    ("有主见", ["坚持自己的判断。", "别人的约束，仍然进得了耳朵。"]),
                    ("听不进", ["更像自我保护。", "先赢场面，再谈方案。"]),
                    ("输赢落在哪", ["会议上他可以赢。", "项目上，你可能输。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_两条线.png",
                "title": "说真话，和听得进，不是一条线",
                "title_underline": "不是一条线",
                "subtitle": "别合成一句「态度不行」",
                "cards": [
                    ("技术诚实", ["管的是知不知、说不说真话。", "糊弄的人，可能很客气。"]),
                    ("这篇管的", ["说了之后，改不改得动。", "听不进的人，可能很「专业」。"]),
                    ("落到结果", ["第一版好看不够。", "听得进，才有机会打磨成可交的东西。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案11_20260926_比打磨交付不比第一版",
        11,
        {
            "title": "比打磨别比第一版",
            "title_underline": "别比第一版",
            "bullets": [
                "第一版演示好看，别急着下定论",
                "软件几乎一定有问题，也一定要优化",
                "首版一次过就封神，后面改需求、收缺陷容易翻车",
                "看缺陷能不能收敛，改动能不能跟上",
            ],
            "gold_line": "靠不靠谱，看到打磨之后的交付。",
            "contrast": [
                ("只收藏第一眼", "界面顺、流程通，松一口气，就当这次找对人了。"),
                ("看到打磨之后", "需求一变怎么接；缺陷是收敛，还是越改越散。"),
            ],
            "close_title": "收束",
            "close_body": "你买的是过程里还能不能被推动，不是某一天的截图。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "掌声停在第一版，往往太早",
                "title_underline": "往往太早",
                "subtitle": "首版一次过，现场气氛很容易很好",
                "cards": [
                    ("当场松口气", ["界面顺，流程通。", "很容易觉得：这次找对人了。"]),
                    ("光鲜盖不住", ["第一周可以很亮。", "第八周的僵持，它盖不住。"]),
                ],
                "footer": "我更愿意把第一版当成起点。",
                "layout": "two_col",
            },
            {
                "file": "02_打磨看什么.png",
                "title": "打磨阶段，看这三件事",
                "title_underline": "这三件事",
                "subtitle": None,
                "cards": [
                    ("需求一变", ["他怎么接。", "是改范围，还是先辩「当初没说」。"]),
                    ("缺陷走向", ["往下收敛，还是越改越散。", "曲线比截图诚实。"]),
                    ("卡点", ["被捅破，还是被捂住。", "捂住的卡点，验收时会一起回来。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_第一眼只是启动.png",
                "title": "第一眼只能说明启动",
                "title_underline": "只能说明启动",
                "subtitle": "漂不漂亮，更多是演示能力",
                "cards": [
                    ("首版说明什么", ["启动快，或演示做得好。", "说明不了最终托付。"]),
                    ("你实际在买", ["过程里还能不能被推动。", "不是某一天的截图。"]),
                    ("更值钱的信号", ["缺陷曲线往下走。", "比界面好看，更接近可交付。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案12_20260926_台前要能对接不是头衔最响",
        12,
        {
            "title": "对接人比头衔重要",
            "title_underline": "比头衔重要",
            "bullets": [
                "选型别只问「你们最强的是谁」",
                "要问：项目期间，我每周对接谁",
                "大厂里专家常在幕后；天天对接的人决定信息折不折损",
                "一线要能讲技术、能沟通，还敢指出自家缺口，不护短",
            ],
            "gold_line": "你以为买到了专家，实际买到的是传话链条。",
            "contrast": [
                ("头衔最响", "名片很亮。真正每周坐在你对面的，常常不是那位。"),
                ("台前多面手", "技术说得清，沟通接得住，对自己人的产出也不护短。"),
            ],
            "close_title": "收束",
            "close_body": "只会挡枪，或只会唱歌，两边都交不了差。台上有人对得起你，打磨才传得动。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "最强的人不一定坐在你对面",
                "title_underline": "不一定坐在你对面",
                "subtitle": "选型时，头衔往往很响",
                "cards": [
                    ("介绍里", ["专家、架构、负责人，名片很满。", "买方容易按头衔下单。"]),
                    ("例会上", ["每周真正说话的是对接人。", "最强的那位，常常不在座。"]),
                ],
                "footer": "你以为买到了专家，实际买到的是传话链条。",
                "layout": "two_col",
            },
            {
                "file": "02_传话损耗.png",
                "title": "损耗发生在传递里",
                "title_underline": "传递里",
                "subtitle": "大厂分工里，专家常常在幕后",
                "cards": [
                    ("传话失真", ["你说的约束，到研发那边变了味。"]),
                    ("问题被捂", ["台前先把场面圆过去，缺口不往上送。"]),
                    ("承诺对不上", ["排期是对接人答应的，做事的人未必认。", "台前缺能扛事的人，后面全是翻译损耗。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_台前多面手.png",
                "title": "台前要像多面手",
                "title_underline": "多面手",
                "subtitle": "一线对接，最好三件事同时做",
                "cards": [
                    ("技术说得清", ["方案能讲到边界，不是只背卖点。"]),
                    ("沟通接得住", ["异议能落成下一步，不是只挡枪。"]),
                    ("不护短", ["敢指出自家产出的缺口。", "护短看起来团结，验收时最疼。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案13_20260926_完全相同案例难求类似可复制更现实",
        13,
        {
            "title": "别死磕一模一样案例",
            "title_underline": "一模一样案例",
            "bullets": [
                "招标最爱要「做过一模一样的」，很难",
                "能扛同款的人，很多已经在竞争对手那边",
                "退一步：类似项目，技术和成果能迁移，更现实",
                "再退才是技术栈匹配——外行很难鉴真假",
            ],
            "gold_line": "别甩一份清单就当验过。",
            "contrast": [
                ("死磕同款", "听起来安全。市场价格和供给，未必给得起这份安全感。"),
                ("类似可复制", "看路径和成果能不能迁移，而不是名字是否一字不差。"),
            ],
            "close_title": "收束",
            "close_body": "熟人常用来补信任：外行鉴不了技术时，只看案例 PPT 常常不够。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "同款案例最好听，也最难求",
                "title_underline": "最难求",
                "subtitle": "互相不熟悉时，买方最想要一模一样",
                "cards": [
                    ("听起来安全", ["做过和我一样的东西，", "好像风险就小了。"]),
                    ("供给很稀", ["能扛同款的人，", "很多已经在对手那边。"]),
                ],
                "footer": "你要的安全感，市场价格未必给得起。",
                "layout": "two_col",
            },
            {
                "file": "02_类似可复制.png",
                "title": "更现实的一档：类似，且能迁移",
                "title_underline": "能迁移",
                "subtitle": "不是把标准放低，是同款常常买不到",
                "cards": [
                    ("看什么", ["技术路径像不像。", "成果能不能迁到你的场景。"]),
                    ("不看什么", ["案例标题是否和你的行业用词一致。"]),
                    ("这一档的意思", ["可复制，比「名字相同」更接近能做成。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_外行难鉴.png",
                "title": "技术栈对得上，外行很难鉴",
                "title_underline": "很难鉴",
                "subtitle": "再退一档，才是关键词对齐",
                "cards": [
                    ("清单的陷阱", ["非技术决策人很难分真本事和演关键词。", "清单越漂亮，越要小心。"]),
                    ("熟人在补什么", ["补的是验货成本，不是万能背书。", "外行鉴不了时，信任总得有个来处。"]),
                    ("只看 PPT", ["「只看案例 PPT」常常不够。", "案例证明不了你这场也能交。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案14_20260926_大团队买信誉贵适大项目",
        14,
        {
            "title": "大团队贵适大项目",
            "title_underline": "适大项目",
            "bullets": [
                "眼下没有完全合适的人，大团队也能招、能扩",
                "买的是信誉，和人员变动时还能补位",
                "贵是标配；小单也堆大厂 logo，常常不划算",
                "规模、风险、预算对得上，这条路才说得通",
            ],
            "gold_line": "Logo 能降低选择焦虑，降不了范围不清的返工。",
            "contrast": [
                ("小单堆 logo", "把它当靠谱证明，往往是买贵了。"),
                ("大项目抗波动", "买的不只是当下几个人，还有组织补位的能力。"),
            ],
            "close_title": "收束",
            "close_body": "不是大团队不靠谱。是贵，而且容易用错地方。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "买的不是 logo，是抗风险",
                "title_underline": "抗风险",
                "subtitle": "大公司大团队，信誉背书强",
                "cards": [
                    ("当下没有人", ["没有现成合适的，也可以招聘扩充。"]),
                    ("你在买什么", ["人员变动时还能补位。", "不只是介绍页上那几个名字。"]),
                ],
                "footer": "对要抗波动的大项目，这条路真实存在。",
                "layout": "two_col",
            },
            {
                "file": "02_贵且用错.png",
                "title": "贵，而且容易用错地方",
                "title_underline": "用错地方",
                "subtitle": None,
                "cards": [
                    ("贵是标配", ["组织、品牌、可扩招，都在报价里。"]),
                    ("小单的误用", ["默认堆大厂 logo，当靠谱的证明。", "体量对不上，就是买贵。"]),
                    ("logo 做不到的", ["它能降低一部分选择焦虑。", "降不了范围不清带来的返工。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_何时划算.png",
                "title": "三者对得上，才划算",
                "title_underline": "才划算",
                "subtitle": "规模、风险、预算",
                "cards": [
                    ("规模", ["项目大到需要一层组织，而不只是几个人。"]),
                    ("风险", ["人员波动你扛不住，才值得为补位付钱。"]),
                    ("预算", ["付得起这层溢价。付不起，logo 只是焦虑的安慰。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案15_20260926_网上找先对齐预算心态",
        15,
        {
            "title": "网上找先对齐预算",
            "title_underline": "对齐预算",
            "bullets": [
                "网上找人，先别到处比最低价",
                "「越便宜越好」和「预算内尽量优质」，是两条路",
                "大预算招标、demo 找学生练手，也是别的档",
                "心态站好，再选团队类型和渠道",
            ],
            "gold_line": "价是低了，预期对不上，报价再多也落不了地。",
            "contrast": [
                ("越便宜越好", "看的是可替换和止损。人能换，损失能停。"),
                ("预算内要优质", "看的是可托付和少返工。便宜不是第一筛。"),
            ],
            "close_title": "收束",
            "close_body": "用同一套话术去询所有人，会把对方问乱，也把自己问乱。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "上网，往往是身边匹配不上",
                "title_underline": "匹配不上",
                "subtitle": "为了找到人，也为了拿到报价",
                "cards": [
                    ("还没站队", ["要越便宜，还是预算内优质，", "自己还没说清。"]),
                    ("先询最低价", ["价下来了。", "哪一条能落地，仍然没有标准。"]),
                ],
                "footer": "你得到一串报价，却没有一条能落地的标准。",
                "layout": "two_col",
            },
            {
                "file": "02_两条路.png",
                "title": "两种心态，不是程度差",
                "title_underline": "不是程度差",
                "subtitle": "不是同一条路上的深浅",
                "cards": [
                    ("越便宜越好", ["筛可替换。", "筛止损：不对了能停。"]),
                    ("预算内优质", ["筛可托付。", "筛少返工，而不是最低一位数。"]),
                    ("话术不能混", ["用同一套问题去问两条路。", "对方乱，你自己的标准也乱。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_别的档.png",
                "title": "还有两档，别并进同一套比法",
                "title_underline": "别并进",
                "subtitle": "站定之后，再选团队和渠道",
                "cards": [
                    ("大预算招标", ["公开比选，流程和保证金都是另一套。"]),
                    ("Demo 练手", ["找初级或学生，买的是试，不是商用托付。"]),
                    ("再往下", ["中预算更常落到有开发的小团队。", "先站队，再谈团队类型。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案16_20260926_中预算找有开发的小团队别皮包中介",
        16,
        {
            "title": "中预算找真人团队",
            "title_underline": "真人团队",
            "bullets": [
                "预算不是天文数字，也不是演示级小钱",
                "别默认把单丢给一层转包，图个省心",
                "更稳的是有软件开发人员的小公司或工作室",
                "能对上真人在做，比只转单的中介靠谱一截",
            ],
            "gold_line": "能约到写代码的人，比能约到很会报价的人更重要。",
            "contrast": [
                ("只转单", "你问细节，得到的是下一层的下一层。责任在传递里蒸发。"),
                ("真人在写", "能约到做软件的人对需求。商务话术隔着一层，先当风险。"),
            ],
            "close_title": "收束",
            "close_body": "省心管的是单，不一定管得了研发。中介可以存在，只是别当中预算的默认第一站。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "中预算的省心陷阱",
                "title_underline": "省心陷阱",
                "subtitle": "有人图省事，把单子丢给中介转包",
                "cards": [
                    ("以为有人管", ["管的是流转。", "不一定是研发。"]),
                    ("细节问下去", ["答案来自下一层的下一层。", "责任在传递里蒸发。"]),
                ],
                "footer": "转包一层，信息就隔一层。",
                "layout": "two_col",
            },
            {
                "file": "02_认谁在写.png",
                "title": "认有没有人在写代码",
                "title_underline": "在写代码",
                "subtitle": "小公司、工作室，关键在这一条",
                "cards": [
                    ("对得上", ["能约到真正做软件的人谈需求。"]),
                    ("对不上", ["见面全是商务话术。", "研发始终隔一层。"]),
                    ("先当风险", ["只转单、研发不露面的，", "先不要当中预算的稳妥选项。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_默认落点.png",
                "title": "中预算更现实的落点",
                "title_underline": "落点",
                "subtitle": "中介不是洪水猛兽，只是别当第一站",
                "cards": [
                    ("小公司 / 工作室", ["有自己的开发人员。", "需求能对到写代码的人。"]),
                    ("报价让位", ["先约到做事的人。", "很会报价，排在后面。"]),
                    ("中介留在哪", ["它可以帮你多问几家。", "不代替你确认谁在写。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案17_20260926_中介捞最便宜商用仍慎重",
        17,
        {
            "title": "商用慎走最低价中介",
            "title_underline": "最低价中介",
            "bullets": [
                "网上中介确实多，也能多家捞到更低价",
                "演示、试水，容错高，有人会走这条路",
                "商用上线，容错低，我仍建议慎重",
                "最低价和可托付，经常不是同一个词",
            ],
            "gold_line": "试水容错高，商用容错低，别用同一套「谁便宜谁上」。",
            "contrast": [
                ("试水可以快", "询价快、报价低，演示阶段有人就这么走。"),
                ("商用要慢", "验收口径、维护责任、人后来找不到，都不在最低价里。"),
            ],
            "close_title": "收束",
            "close_body": "你省下的是签约前的时间，补上的常常是签约后的精力。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "省心和低价，是真需求",
                "title_underline": "是真需求",
                "subtitle": "这条路不必先道德审判",
                "cards": [
                    ("中介能做什么", ["询价快。", "确实可能摸到更便宜的报价。"]),
                    ("先分开两件事", ["演示、试水是一档。", "商用上线是另一档。"]),
                ],
                "footer": "风险本来就不同，别先混成一句「中介好不好」。",
                "layout": "two_col",
            },
            {
                "file": "02_商用补账.png",
                "title": "商用为何要慢半拍",
                "title_underline": "慢半拍",
                "subtitle": "默认多家中介比最低价之后",
                "cards": [
                    ("验收口径", ["便宜的那家，和你说的「完成」可能不是一回事。"]),
                    ("维护责任", ["上线后谁改、谁值守，报价单上常常是空的。"]),
                    ("人找不到", ["转了几手，出问题时候对接人已经不在。", "报价单外的成本，会在过程里补回来。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_怎么用.png",
                "title": "低价可以试，商用别默认",
                "title_underline": "别默认",
                "subtitle": None,
                "cards": [
                    ("试水", ["容错高。低价、快询，可以当实验。"]),
                    ("商用", ["容错低。谁便宜谁上，会低估后面的扯皮。"]),
                    ("时间账", ["省下的是签约前的时间。", "补上的是签约后的精力。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案18_20260926_直连一线研发优先Boss招聘平台",
        18,
        {
            "title": "直连研发优先招聘平台",
            "title_underline": "招聘平台",
            "bullets": [
                "想直连一线，别默认去服务市场发单就等于触达开发",
                "我更优先 Boss 这类招聘平台",
                "猪八戒一类里，营销公司容易占满版面，要自己筛",
                "淘宝、闲鱼同类：能找到人，不等于对方是你要的研发",
            ],
            "gold_line": "你要的是能对齐需求的研发，不是更会写标书的中间层。",
            "contrast": [
                ("招聘平台", "人的身份更接近「我能做」，而不是「我接单再转」。"),
                ("服务交易市场", "营销型公司容易把版面占满。不是没有靠谱的，是噪声大。"),
            ],
            "close_title": "收束",
            "close_body": "便宜和近，也不等于可托付。场选错了，人筛得再累也像在噪声里打捞。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "发单，不等于摸到研发",
                "title_underline": "不等于摸到研发",
                "subtitle": "渠道类型，比平台口号重要",
                "cards": [
                    ("服务市场", ["发一单，回信可以很多。", "回信的未必是写代码的人。"]),
                    ("你要找的", ["能对齐需求的一线研发。", "不是更会写标书的中间层。"]),
                ],
                "footer": "除了招投标场，想直连一线，先看人的身份像不像「我能做」。",
                "layout": "two_col",
            },
            {
                "file": "02_招聘平台.png",
                "title": "招聘平台更贴近直连",
                "title_underline": "直连",
                "subtitle": "Boss 这类，我更优先",
                "cards": [
                    ("身份", ["主页写的是能做什么。", "不是「全行业都能接」。"]),
                    ("对话对象", ["更容易约到做事的人。", "少一层「我帮你找人」。"]),
                    ("仍要筛", ["优先，不是免筛。", "头衔和作品还是要自己看。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_交易场自筛.png",
                "title": "交易场能找到人，要自己筛",
                "title_underline": "要自己筛",
                "subtitle": "猪八戒，以及淘宝、闲鱼一类",
                "cards": [
                    ("版面", ["营销型公司容易占满。", "噪声大，不代表里面一个都没有。"]),
                    ("淘宝 / 闲鱼", ["逻辑类似：离得近、价看起来低。"]),
                    ("仍不等于", ["找到人，不等于是你要的研发。", "便宜和近，也不等于可托付。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
    (
        "文案19_20260926_社交平台匹配效果未验证先当实验",
        19,
        {
            "title": "社交渠道先当实验",
            "title_underline": "先当实验",
            "bullets": [
                "小红书、头条、抖音快手，既能发需求，也能搜服务商",
                "两条动作都通；点赞和私信来得快",
                "匹配稳不稳，我还没验证成可以当主渠道",
                "可以试，别发一条就当招到了",
            ],
            "gold_line": "把实验当结论，容易在热情里放松对交付的要求。",
            "contrast": [
                ("当成主渠道", "一条帖子的热度，就当成已经招到靠谱研发。"),
                ("当成实验", "发可以，搜可以。结论慢一点下，热度不等于匹配。"),
            ],
            "close_title": "收束",
            "close_body": "社交是补充试探，不是替代。认人、谈约束、找路，仍比在场子里赌运气靠谱。",
        },
        [
            {
                "file": "01_封面.png",
                "title": "场在，不等于主渠道已成",
                "title_underline": "主渠道已成",
                "subtitle": "发需求、搜服务商，两条都通",
                "cards": [
                    ("来得快", ["点赞、评论、私信，可以很快。"]),
                    ("还没证明的", ["匹配质量稳不稳。", "快，只说明场是开着的。"]),
                ],
                "footer": "来得快，不等于匹配质量稳。",
                "layout": "two_col",
            },
            {
                "file": "02_尚未验证.png",
                "title": "为什么我还不当它是主渠道",
                "title_underline": "主渠道",
                "subtitle": None,
                "cards": [
                    ("验证没做完", ["发得出、搜得到，我见过。", "稳定匹配到可托付的研发，还没有。"]),
                    ("热情的代价", ["把实验当结论。", "后面容易放松对诚实、边界和交付的要求。"]),
                    ("热闹本身", ["越热闹，越要慢一点下结论。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
            {
                "file": "03_实验心态.png",
                "title": "实验可以做，替代不行",
                "title_underline": "替代不行",
                "subtitle": "社交是补充试探",
                "cards": [
                    ("可以", ["发一条需求。", "搜已经在做服务的人。"]),
                    ("不可以", ["把一条帖子当成已经招到。", "用热度代替认人和谈约束。"]),
                    ("仍要回去的", ["招聘平台直连、预算怎么站、合作前谈清什么。", "平台会变，这些判断没那么快过时。"]),
                ],
                "footer": None,
                "layout": "two_over_one_tight",
            },
        ],
    ),
]


if __name__ == "__main__":
    # 默认：渲染文案9～19。需要单篇时改 ONLY，例如 ONLY = {9}
    WORKSPACE = Path(__file__).resolve().parents[3]
    COPY_ROOT = WORKSPACE / "study/介绍案例/怎么找到靠谱的软件开发/文案"
    ONLY: set[int] | None = None
    for folder, episode, xhs, tt in ARTICLE_PACKS:
        if ONLY is not None and episode not in ONLY:
            continue
        paths = render_pack(COPY_ROOT / folder, episode, xhs, tt)
        for path in paths:
            print(path)
