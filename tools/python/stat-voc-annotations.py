#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""统计 Pascal VOC 标注框的类型与尺寸分布。

支持一个或多个 VOC 根目录（或直接指向 Annotations）。仅标准库。
路径用环境变量传入，也可用下方 __main__ 变量本地试跑。
"""
from __future__ import annotations

import json
import logging
import math
import os
import struct
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
IMAGE_DIR_NAMES = ("JPEGImages", "images", "Images")
ANNOTATION_DIR_NAMES = ("Annotations", "annotations", "labels")
SKIP_PATH_PARTS = frozenset({
    ".idea", ".git", "__pycache__", ".pytest_cache", ".vscode", "node_modules",
})
COLLECT_PROGRESS_EVERY = 500
NORM_BOX_BIN_EDGES: List[float] = [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0000001]
PIX_BOX_BIN_EDGES: List[float] = [0.0, 32.0, 64.0, 128.0, 256.0, 512.0, 1024.0, 2048.0, 1.0e9]


def _is_usable_path(path: Path) -> bool:
    name = path.name
    if name.startswith("._") or name == ".DS_Store":
        return False
    if SKIP_PATH_PARTS & set(path.parts):
        return False
    return True


def _find_subdir(root: Path, candidates: tuple[str, ...]) -> Path | None:
    for name in candidates:
        path = root / name
        if path.is_dir():
            return path
    return None


def resolve_voc_layout(root: Path) -> tuple[Path, Path | None]:
    """返回 (annotation_dir, image_dir|None)。"""
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"目录不存在: {root}")

    ann = _find_subdir(root, ANNOTATION_DIR_NAMES)
    img = _find_subdir(root, IMAGE_DIR_NAMES)
    if ann is not None:
        return ann, img

    # 直接指向 Annotations，或扁平目录内全是 xml
    xmls = list(root.glob("*.xml"))
    if xmls or root.name in ANNOTATION_DIR_NAMES:
        parent = root.parent
        img = _find_subdir(parent, IMAGE_DIR_NAMES)
        return root, img

    return root, img


def read_image_size(image_path: Path) -> tuple[int, int]:
    """读取图像宽高，不依赖第三方图像库。"""
    suffix = image_path.suffix.lower()
    with image_path.open("rb") as fp:
        if suffix == ".bmp":
            fp.seek(18)
            width, height = struct.unpack("<ii", fp.read(8))
            return abs(width), abs(height)

        if suffix in {".jpg", ".jpeg"}:
            data = fp.read()
            index = 2
            while index + 9 < len(data):
                if data[index] != 0xFF:
                    break
                marker = data[index + 1]
                if marker in (
                    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
                ):
                    height = struct.unpack(">H", data[index + 5 : index + 7])[0]
                    width = struct.unpack(">H", data[index + 7 : index + 9])[0]
                    return width, height
                segment_len = struct.unpack(">H", data[index + 2 : index + 4])[0]
                index += 2 + segment_len

        if suffix == ".png":
            header = fp.read(24)
            if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
                width, height = struct.unpack(">II", header[16:24])
                return width, height

    raise ValueError(f"无法解析图像尺寸: {image_path.name}")


def load_class_names(categories_path: Path) -> dict[int, str]:
    """支持 predefined_classes.txt（一行一类）或 Categories.json。"""
    text = categories_path.read_text(encoding="utf-8")
    if categories_path.suffix.lower() == ".json" or text.lstrip().startswith("{"):
        payload = json.loads(text)
        categories = payload.get("categories", [])
        return {
            int(item["id"]): str(item["name"])
            for item in sorted(categories, key=lambda x: int(x["id"]))
        }

    names = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    return {i: name for i, name in enumerate(names)}


def _parse_dirs_env(raw: str) -> list[Path]:
    """支持 PATH 分隔符、逗号、换行分隔的多目录。"""
    parts: list[str] = []
    for chunk in raw.replace("\n", os.pathsep).replace(",", os.pathsep).split(os.pathsep):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return [Path(p).expanduser().resolve() for p in parts]


def _bin_label(lo: float, hi: float, *, is_last: bool, as_percent: bool) -> str:
    if as_percent:
        if is_last:
            return f"[{lo * 100:.2f}%, 100.00%]"
        return f"[{lo * 100:.2f}%, {hi * 100:.2f}%)"
    if is_last and hi >= 1e6:
        return f">= {lo:.0f}px"
    if is_last:
        return f"[{lo:.1f}, {hi:.1f}]px"
    return f"[{lo:.1f}, {hi:.1f})px"


def histogram_bin_counts(
    values: Sequence[float],
    edges: Sequence[float],
    *,
    use_percent_labels: bool = False,
) -> Tuple[List[str], List[int]]:
    if len(edges) < 2:
        return [], []
    n = len(edges) - 1
    labels = [
        _bin_label(float(edges[i]), float(edges[i + 1]), is_last=(i == n - 1), as_percent=use_percent_labels)
        for i in range(n)
    ]
    counts = [0] * n
    for v in values:
        try:
            x = float(v)
        except (TypeError, ValueError):
            continue
        placed = False
        for i in range(n):
            lo, hi = edges[i], edges[i + 1]
            last = i == n - 1
            if last:
                if lo <= x <= hi:
                    counts[i] += 1
                    placed = True
                    break
            elif lo <= x < hi:
                counts[i] += 1
                placed = True
                break
        if not placed:
            counts[0 if x < edges[0] else -1] += 1
    return labels, counts


class VocAnnotationStats:
    """聚合统计一个或多个 VOC 目录中的标注框。"""

    def __init__(
        self,
        sample_dirs: Sequence[str | Path],
        *,
        recursive: bool = True,
        categories_path: str | Path | None = None,
        use_diagonal: bool = True,
    ):
        self.sample_dirs = [Path(d).expanduser().resolve() for d in sample_dirs]
        if not self.sample_dirs:
            raise ValueError("至少提供一个样本目录")
        self.recursive = recursive
        self.use_diagonal = bool(use_diagonal)

        self.stats: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "widths_norm": [],
                "heights_norm": [],
                "widths_px": [],
                "heights_px": [],
            }
        )
        self.class_name_to_id: Dict[str, int] = {}
        self.id_to_name: Dict[int, str] = {}
        self.next_class_id = 0

        self.total_annotation_files = 0
        self.empty_annotation_files = 0
        self.missing_image_files = 0
        self.per_dir_file_counts: Dict[str, int] = {}
        self.longest_side_extremes_px: Dict[int, Dict[str, object]] = {}

        self._init_class_maps(Path(categories_path) if categories_path else None)

    def _init_class_maps(self, categories_path: Path | None) -> None:
        candidates: list[Path] = []
        if categories_path is not None:
            candidates.append(categories_path.expanduser().resolve())
        for root in self.sample_dirs:
            candidates.append(root / "predefined_classes.txt")
            candidates.append(root / "Categories.json")

        for path in candidates:
            if path.is_file():
                self.id_to_name = load_class_names(path)
                self.class_name_to_id = {name: cid for cid, name in self.id_to_name.items()}
                self.next_class_id = max(self.id_to_name.keys(), default=-1) + 1
                logger.info("已加载类别表 %s，共 %d 类", path, len(self.id_to_name))
                return

    @staticmethod
    def _safe_relpath(path: Path, base: Path) -> str:
        try:
            return str(path.relative_to(base))
        except ValueError:
            return str(path)

    def _metric_cn(self) -> str:
        return "对角线长度" if self.use_diagonal else "最长边"

    def _metric_values(self, widths: Sequence[float], heights: Sequence[float]) -> List[float]:
        if self.use_diagonal:
            return [math.hypot(w, h) for w, h in zip(widths, heights)]
        return [max(w, h) for w, h in zip(widths, heights)]

    def _metric_stats(self, widths: Sequence[float], heights: Sequence[float]) -> Tuple[float, float, float]:
        vals = self._metric_values(widths, heights)
        if not vals:
            return 0.0, 0.0, 0.0
        return sum(vals) / len(vals), min(vals), max(vals)

    @staticmethod
    def _area_stats(widths: Sequence[float], heights: Sequence[float]) -> Tuple[float, float, float]:
        areas = [w * h for w, h in zip(widths, heights)]
        if not areas:
            return 0.0, 0.0, 0.0
        return sum(areas) / len(areas), min(areas), max(areas)

    def get_class_id_from_name(self, class_name: str) -> int:
        if class_name not in self.class_name_to_id:
            self.class_name_to_id[class_name] = self.next_class_id
            self.id_to_name[self.next_class_id] = class_name
            self.next_class_id += 1
        return self.class_name_to_id[class_name]

    def _class_display(self, class_id: int) -> str:
        return self.id_to_name.get(class_id, str(class_id))

    def _find_image(self, annotation_path: Path, image_dir: Path | None) -> Optional[Path]:
        stem = annotation_path.stem
        for ext in IMAGE_SUFFIXES:
            candidate = annotation_path.with_suffix(ext)
            if candidate.is_file():
                return candidate

        search_dirs: list[Path] = []
        if image_dir and image_dir.is_dir():
            search_dirs.append(image_dir)
        parent = annotation_path.parent
        if parent.name in ANNOTATION_DIR_NAMES:
            sibling = _find_subdir(parent.parent, IMAGE_DIR_NAMES)
            if sibling is not None:
                search_dirs.append(sibling)

        for directory in search_dirs:
            for ext in IMAGE_SUFFIXES:
                candidate = directory / f"{stem}{ext}"
                if candidate.is_file():
                    return candidate
        return None

    def parse_xml_file(
        self,
        xml_path: Path,
        image_dir: Path | None,
    ) -> List[Tuple[int, float, float, float, float]]:
        annotations: List[Tuple[int, float, float, float, float]] = []
        try:
            root = ET.parse(xml_path).getroot()
        except (OSError, ET.ParseError) as exc:
            logger.error("解析 XML 失败 %s: %s", xml_path, exc)
            return annotations

        size = root.find("size")
        image_width = int(size.findtext("width", "0")) if size is not None else 0
        image_height = int(size.findtext("height", "0")) if size is not None else 0
        if image_width <= 0 or image_height <= 0:
            image_path = self._find_image(xml_path, image_dir)
            if image_path is not None:
                try:
                    image_width, image_height = read_image_size(image_path)
                except ValueError:
                    pass
        if image_width <= 0 or image_height <= 0:
            logger.warning("图像尺寸无效，跳过 %s", xml_path)
            return annotations

        for obj in root.findall("object"):
            class_name = (obj.findtext("name") or "").strip()
            if not class_name:
                continue
            bnd = obj.find("bndbox")
            if bnd is None:
                continue
            try:
                xmin = float(bnd.findtext("xmin", "0"))
                ymin = float(bnd.findtext("ymin", "0"))
                xmax = float(bnd.findtext("xmax", "0"))
                ymax = float(bnd.findtext("ymax", "0"))
            except ValueError:
                continue
            width_px = xmax - xmin
            height_px = ymax - ymin
            if width_px <= 0 or height_px <= 0:
                continue
            width_norm = width_px / image_width
            height_norm = height_px / image_height
            if not (0 <= width_norm <= 1 and 0 <= height_norm <= 1):
                continue
            class_id = self.get_class_id_from_name(class_name)
            annotations.append((class_id, width_norm, height_norm, width_px, height_px))
        return annotations

    def collect_stats(self) -> None:
        total_boxes = 0
        for sample_dir in self.sample_dirs:
            annotation_dir, image_dir = resolve_voc_layout(sample_dir)
            pattern = "**/*.xml" if self.recursive else "*.xml"
            annotation_files = [p for p in sorted(annotation_dir.glob(pattern)) if _is_usable_path(p)]
            self.per_dir_file_counts[str(sample_dir)] = len(annotation_files)
            if not annotation_files:
                logger.warning("未找到 VOC xml: %s", annotation_dir)
                continue

            logger.info(
                "目录 %s → 标注 %s，图片 %s，共 %d 个 xml",
                sample_dir,
                annotation_dir,
                image_dir or "(同级/未找到)",
                len(annotation_files),
            )
            n_files = len(annotation_files)
            self.total_annotation_files += n_files

            for file_idx, annotation_path in enumerate(annotation_files, 1):
                annotation_name = f"{sample_dir.name}/{self._safe_relpath(annotation_path, annotation_dir)}"
                boxes = self.parse_xml_file(annotation_path, image_dir)
                if not boxes:
                    self.empty_annotation_files += 1
                if self._find_image(annotation_path, image_dir) is None:
                    self.missing_image_files += 1

                for class_id, width_norm, height_norm, width_px, height_px in boxes:
                    self.stats[class_id]["count"] += 1
                    self.stats[class_id]["widths_norm"].append(width_norm)
                    self.stats[class_id]["heights_norm"].append(height_norm)
                    if width_px > 0 and height_px > 0:
                        self.stats[class_id]["widths_px"].append(width_px)
                        self.stats[class_id]["heights_px"].append(height_px)
                        metric_px = (
                            float(math.hypot(width_px, height_px))
                            if self.use_diagonal
                            else float(max(width_px, height_px))
                        )
                        ext = self.longest_side_extremes_px.get(class_id)
                        if ext is None:
                            self.longest_side_extremes_px[class_id] = {
                                "min": metric_px,
                                "min_file": annotation_name,
                                "max": metric_px,
                                "max_file": annotation_name,
                            }
                        else:
                            if metric_px < float(ext["min"]):  # type: ignore[arg-type]
                                ext["min"] = metric_px
                                ext["min_file"] = annotation_name
                            if metric_px > float(ext["max"]):  # type: ignore[arg-type]
                                ext["max"] = metric_px
                                ext["max_file"] = annotation_name
                    total_boxes += 1

                if file_idx == n_files or (COLLECT_PROGRESS_EVERY > 0 and file_idx % COLLECT_PROGRESS_EVERY == 0):
                    logger.info("进度 [%s]: %d/%d，累计框 %d", sample_dir.name, file_idx, n_files, total_boxes)

        logger.info("共统计 %d 个标注框（%d 个标注文件）", total_boxes, self.total_annotation_files)

    def _format_interval_table_lines(
        self,
        title: str,
        values: List[float],
        edges: List[float],
        *,
        use_percent_labels: bool,
    ) -> List[str]:
        lines = [title, ""]
        if not values:
            lines.extend(["  (无数据)", ""])
            return lines
        labels, counts = histogram_bin_counts(values, edges, use_percent_labels=use_percent_labels)
        total = sum(counts)
        lines.append(f"{'区间':<28} {'数量':<10} {'占比':<10}")
        lines.append("-" * 48)
        for lab, c in zip(labels, counts):
            pct = (100.0 * c / total) if total else 0.0
            lines.append(f"{lab:<28} {c:<10} {pct:>6.2f}%")
        lines.append(f"{'合计':<28} {total:<10} {'100.00%':>10}")
        lines.append("")
        return lines

    def interval_stats_lines(self) -> List[str]:
        lines = [
            "",
            f"【{self._metric_cn()}像素值区间统计（按类别）】",
            "（分箱边界可在文件顶部 PIX_BOX_BIN_EDGES 调整）",
            "",
        ]
        for class_id in sorted(self.stats.keys()):
            stat = self.stats[class_id]
            metric_px = self._metric_values(stat.get("widths_px") or [], stat.get("heights_px") or [])
            title = f"{self._class_display(class_id)} - {self._metric_cn()}(px)"
            lines.extend(
                self._format_interval_table_lines(
                    title, metric_px, PIX_BOX_BIN_EDGES, use_percent_labels=False
                )
            )
        return lines

    def _report_header_lines(self) -> List[str]:
        lines = [
            "=" * 80,
            "标注统计结果 (格式: voc)",
            f"样本目录数: {len(self.sample_dirs)}",
        ]
        for d in self.sample_dirs:
            n = self.per_dir_file_counts.get(str(d), 0)
            lines.append(f"  - {d}  (xml={n})")
        if self.total_annotation_files:
            lines.append(
                f"标注文件数: {self.total_annotation_files}  "
                f"空标注文件数: {self.empty_annotation_files}  "
                f"缺图文件数: {self.missing_image_files}"
            )
        if self.id_to_name:
            lines.append("")
            lines.append("类别名称映射:")
            for class_id, name in sorted(self.id_to_name.items()):
                lines.append(f"  ID {class_id}: {name}")
        lines.append("=" * 80)
        return lines

    def _body_lines(self) -> List[str]:
        if not self.stats:
            return ["没有统计数据"]

        lines: List[str] = []
        sorted_classes = sorted(self.stats.keys())
        lines.append("")
        lines.append("【归一化值统计】")
        lines.append(
            f"{'类别':<18} {'数量':<10} "
            f"{f'{self._metric_cn()}均值':<15} {f'{self._metric_cn()}最小':<15} {f'{self._metric_cn()}最大':<15}"
        )
        lines.append("-" * 73)
        total_count = 0
        for class_id in sorted_classes:
            stat = self.stats[class_id]
            avg_m, min_m, max_m = self._metric_stats(stat["widths_norm"], stat["heights_norm"])
            lines.append(
                f"{self._class_display(class_id):<18} {stat['count']:<10} "
                f"{avg_m:<15.6f} {min_m:<15.6f} {max_m:<15.6f}"
            )
            total_count += stat["count"]
        lines.append("-" * 73)
        lines.append(f"{'总计':<18} {total_count:<10}")

        has_px = any(self.stats[cid]["widths_px"] for cid in sorted_classes)
        if has_px:
            lines.append("")
            lines.append("【原始像素值统计】")
            lines.append(
                f"{'类别':<18} {'数量':<10} "
                f"{f'{self._metric_cn()}均值(px)':<18} {f'{self._metric_cn()}最小(px)':<18} "
                f"{f'{self._metric_cn()}最大(px)':<18} "
                f"{'面积均值(px^2)':<18} {'面积最小(px^2)':<18} {'面积最大(px^2)':<18}"
            )
            lines.append("-" * 142)
            for class_id in sorted_classes:
                stat = self.stats[class_id]
                widths_px = stat["widths_px"]
                heights_px = stat["heights_px"]
                if not widths_px:
                    continue
                avg_m, min_m, max_m = self._metric_stats(widths_px, heights_px)
                avg_a, min_a, max_a = self._area_stats(widths_px, heights_px)
                lines.append(
                    f"{self._class_display(class_id):<18} {len(widths_px):<10} "
                    f"{avg_m:<18.2f} {min_m:<18.2f} {max_m:<18.2f} "
                    f"{avg_a:<18.2f} {min_a:<18.2f} {max_a:<18.2f}"
                )
            lines.append("-" * 142)

        if self.longest_side_extremes_px:
            lines.append("")
            lines.append(f"【每类{self._metric_cn()}(px)极值对应标注文件】")
            lines.append(
                f"{'类别':<18} {'min(px)':<12} {'min文件':<50} {'max(px)':<12} {'max文件'}"
            )
            lines.append("-" * 120)
            rows: List[Tuple[float, int, float, str, float, str]] = []
            for class_id in sorted_classes:
                ext = self.longest_side_extremes_px.get(class_id)
                if not ext:
                    continue
                rows.append(
                    (
                        float(ext["min"]),  # type: ignore[arg-type]
                        class_id,
                        float(ext["min"]),  # type: ignore[arg-type]
                        str(ext["min_file"]),
                        float(ext["max"]),  # type: ignore[arg-type]
                        str(ext["max_file"]),
                    )
                )
            for _, class_id, min_v, min_f, max_v, max_f in sorted(rows, key=lambda x: x[0]):
                lines.append(
                    f"{self._class_display(class_id):<18} "
                    f"{min_v:<12.2f} {min_f:<50} {max_v:<12.2f} {max_f}"
                )
            lines.append("-" * 120)

        lines.extend(self.interval_stats_lines())
        lines.append("=" * 80)
        return lines

    def report_text(self) -> str:
        return "\n".join(self._report_header_lines() + self._body_lines()) + "\n"

    def print_stats(self) -> None:
        print(self.report_text(), end="")

    def save_stats_to_file(self, output_path: str | Path | None = None) -> Path:
        if output_path is None:
            output_path = self.sample_dirs[0] / "annotation_stats_voc.txt"
        else:
            output_path = Path(output_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.report_text(), encoding="utf-8")
        logger.info("统计结果已保存到: %s", output_path)
        return output_path


def run_stats(
    sample_dirs: Sequence[str | Path],
    *,
    recursive: bool = True,
    categories_path: str | Path | None = None,
    use_diagonal: bool = True,
    output_path: str | Path | None = None,
) -> VocAnnotationStats:
    stats = VocAnnotationStats(
        sample_dirs=sample_dirs,
        recursive=recursive,
        categories_path=categories_path,
        use_diagonal=use_diagonal,
    )
    stats.collect_stats()
    stats.print_stats()
    stats.save_stats_to_file(output_path)
    return stats


def run_from_env() -> VocAnnotationStats:
    raw_dirs = os.environ.get("VOC_DIRS", "").strip()
    if not raw_dirs:
        single = os.environ.get("VOC_DIR", "").strip()
        if not single:
            raise SystemExit("请设置 VOC_DIRS（多目录）或 VOC_DIR（单目录）")
        dirs = [Path(single).expanduser().resolve()]
    else:
        dirs = _parse_dirs_env(raw_dirs)

    categories = os.environ.get("VOC_CATEGORIES", "").strip() or None
    output = os.environ.get("VOC_STATS_OUTPUT", "").strip() or None
    recursive = os.environ.get("VOC_RECURSIVE", "1").strip() not in {"0", "false", "False"}
    use_diagonal = os.environ.get("VOC_USE_DIAGONAL", "1").strip() not in {"0", "false", "False"}

    return run_stats(
        sample_dirs=dirs,
        recursive=recursive,
        categories_path=categories,
        use_diagonal=use_diagonal,
        output_path=output,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # 有环境变量时优先走 env；否则改下方变量后直接运行
    if os.environ.get("VOC_DIRS") or os.environ.get("VOC_DIR"):
        run_from_env()
    else:
        SAMPLE_DIRS: list[Path] = [
            Path("<VOC目录1>"),
            # Path("<VOC目录2>"),
        ]
        CATEGORIES_PATH: Path | None = None  # 可选 predefined_classes.txt / Categories.json
        RECURSIVE = True
        USE_DIAGONAL = True
        OUTPUT_PATH: Path | None = None  # 默认写到第一个目录下 annotation_stats_voc.txt

        run_stats(
            sample_dirs=SAMPLE_DIRS,
            recursive=RECURSIVE,
            categories_path=CATEGORIES_PATH,
            use_diagonal=USE_DIAGONAL,
            output_path=OUTPUT_PATH,
        )
