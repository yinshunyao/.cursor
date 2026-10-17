#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""将 Label Studio 矩形框导出转换为 Pascal VOC（LabelImg）。

输入为导出 JSON 或包含 JSON 与图像的目录。具体路径用环境变量传入，不写在本文件中。
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import shutil
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".bmp", ".png", ".tif", ".tiff", ".webp"}
UUID_PREFIX_RE = re.compile(r"^[0-9a-fA-F]{8}-")


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


def load_categories(categories_path: Path) -> tuple[list[str], dict[int, str]]:
    with categories_path.open(encoding="utf-8") as fp:
        payload = json.load(fp)
    id_to_name: dict[int, str] = {}
    names: list[str] = []
    for item in sorted(payload.get("categories", []), key=lambda x: int(x["id"])):
        cid = int(item["id"])
        name = str(item["name"])
        id_to_name[cid] = name
        names.append(name)
    return names, id_to_name


def find_image_file(image_dir: Path, file_name: str) -> Path | None:
    direct = image_dir / file_name
    if direct.is_file():
        return direct
    stem = Path(file_name).stem
    for suffix in IMAGE_SUFFIXES:
        candidate = image_dir / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def normalize_bbox(
    points: list[float], width: int, height: int
) -> tuple[float, float, float, float]:
    if len(points) != 4:
        raise ValueError(f"矩形框需要 4 个坐标，实际为 {len(points)}")
    x1, y1, x2, y2 = [float(v) for v in points]
    left = max(0.0, min(x1, x2))
    right = min(float(width), max(x1, x2))
    top = max(0.0, min(y1, y2))
    bottom = min(float(height), max(y1, y2))
    return left, top, right, bottom


def bbox_to_voc_ints(
    points: list[float], width: int, height: int
) -> tuple[int, int, int, int] | None:
    x1, y1, x2, y2 = normalize_bbox(points, width, height)
    if x2 <= x1 or y2 <= y1:
        return None
    xmin = max(0, min(width, int(round(x1))))
    ymin = max(0, min(height, int(round(y1))))
    xmax = max(0, min(width, int(round(x2))))
    ymax = max(0, min(height, int(round(y2))))
    if xmax <= xmin or ymax <= ymin:
        return None
    return xmin, ymin, xmax, ymax


def _xml_tostring(root: ET.Element) -> str:
    elem = ET.ElementTree(root)
    try:
        ET.indent(elem, space="    ")
    except AttributeError:
        pass
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def build_voc_xml(
    *,
    image_name: str,
    image_path: Path,
    folder_name: str,
    width: int,
    height: int,
    annotations: list[dict[str, Any]],
    id_to_name: dict[int, str],
) -> str:
    root = ET.Element("annotation")
    ET.SubElement(root, "folder").text = folder_name
    ET.SubElement(root, "filename").text = image_name
    ET.SubElement(root, "path").text = str(image_path.resolve())
    source = ET.SubElement(root, "source")
    ET.SubElement(source, "database").text = "Unknown"
    size = ET.SubElement(root, "size")
    ET.SubElement(size, "width").text = str(width)
    ET.SubElement(size, "height").text = str(height)
    ET.SubElement(size, "depth").text = "3"
    ET.SubElement(root, "segmented").text = "0"

    for ann in annotations:
        points = ann.get("points", [])
        if ann.get("type") != 3 or len(points) != 4:
            continue
        bbox = bbox_to_voc_ints(points, width, height)
        if bbox is None:
            continue
        xmin, ymin, xmax, ymax = bbox
        label = id_to_name.get(int(ann["category_id"]), str(ann["category_id"]))
        obj = ET.SubElement(root, "object")
        ET.SubElement(obj, "name").text = label
        ET.SubElement(obj, "pose").text = "Unspecified"
        ET.SubElement(obj, "truncated").text = "0"
        ET.SubElement(obj, "difficult").text = "0"
        bndbox = ET.SubElement(obj, "bndbox")
        ET.SubElement(bndbox, "xmin").text = str(xmin)
        ET.SubElement(bndbox, "ymin").text = str(ymin)
        ET.SubElement(bndbox, "xmax").text = str(xmax)
        ET.SubElement(bndbox, "ymax").text = str(ymax)
    return _xml_tostring(root)


def write_voc_predefined_classes(output_dir: Path, class_names: list[str]) -> None:
    (output_dir / "predefined_classes.txt").write_text(
        "\n".join(class_names) + ("\n" if class_names else ""),
        encoding="utf-8",
    )


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


def _as_task_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    raise ValueError(f"无法识别的 Label Studio JSON 结构: {type(payload)}")


def iter_ls_tasks(
    input_path: Path, *, recursive: bool = True
) -> Iterable[tuple[Path | None, dict[str, Any]]]:
    if input_path.is_dir():
        pattern = "**/*.json" if recursive else "*.json"
        for path in sorted(input_path.glob(pattern)):
            if not path.is_file():
                continue
            if path.name.startswith("._") or path.name.lower() == "categories.json":
                continue
            try:
                payload = _load_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("跳过无法解析的 JSON: %s (%s)", path.name, exc)
                continue
            for task in _as_task_list(payload):
                yield path, task
        return
    if input_path.is_file():
        payload = _load_json(input_path)
        for task in _as_task_list(payload):
            yield input_path, task
        return
    raise FileNotFoundError(f"输入路径不存在: {input_path}")


def _image_name_candidates(file_name: str) -> list[str]:
    """精确名，以及把文件名中第一处下划线换成空格（导出常把空格写成下划线）。"""
    names = [file_name]
    if "_" in file_name:
        alt = file_name.replace("_", " ", 1)
        if alt not in names:
            names.append(alt)
    return names


def find_image_for_task(
    image_root: Path,
    file_name: str,
    *,
    source_path: Path | None = None,
    recursive: bool = True,
) -> Path | None:
    search_dirs: list[Path] = []
    if source_path is not None:
        search_dirs.append(source_path.parent)
    search_dirs.append(image_root)

    seen: set[Path] = set()
    for directory in search_dirs:
        directory = directory.resolve()
        if directory in seen:
            continue
        seen.add(directory)
        for name in _image_name_candidates(file_name):
            found = find_image_file(directory, name)
            if found is not None:
                return found

    if not recursive:
        return None

    for name in _image_name_candidates(file_name):
        direct = image_root / name
        if direct.is_file():
            return direct
        matches = [
            p
            for p in image_root.rglob(name)
            if p.is_file() and not p.name.startswith("._")
        ]
        if matches:
            return sorted(matches)[0]
        stem = Path(name).stem
        for suffix in IMAGE_SUFFIXES:
            matches = [
                p
                for p in image_root.rglob(f"{stem}{suffix}")
                if p.is_file() and not p.name.startswith("._")
            ]
            if matches:
                return sorted(matches)[0]
    return None


def image_name_from_ls_uri(uri: str) -> str:
    name = Path(str(uri).split("?", 1)[0]).name
    if UUID_PREFIX_RE.match(name):
        return name[9:]
    return name


def resolve_image_name(task: dict[str, Any], source_path: Path | None) -> str:
    if source_path is not None and source_path.name.lower().endswith(".json"):
        candidate = source_path.name[:-5]
        if Path(candidate).suffix.lower() in IMAGE_SUFFIXES:
            return candidate
    data = task.get("data") or {}
    for key in ("image", "img", "Image"):
        if data.get(key):
            return image_name_from_ls_uri(str(data[key]))
    raise ValueError("任务缺少 data.image，且无法从来源文件名推断图像名")


def extract_rectangle_results(task: dict[str, Any]) -> list[dict[str, Any]]:
    annotations = task.get("annotations") or []
    if not annotations:
        return []
    results = annotations[-1].get("result") or []
    return [item for item in results if isinstance(item, dict)]


def _rotated_ends_aabb(
    x: float, y: float, w: float, h: float, rotation_deg: float
) -> list[float]:
    """绕左上角顺时针旋转，取四角的轴对齐外接框。"""
    rad = math.radians(rotation_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    local = ((0.0, 0.0), (w, 0.0), (w, h), (0.0, h))
    xs: list[float] = []
    ys: list[float] = []
    for dx, dy in local:
        xs.append(x + dx * cos_a - dy * sin_a)
        ys.append(y + dx * sin_a + dy * cos_a)
    return [min(xs), min(ys), max(xs), max(ys)]


def ls_value_to_points(value: dict[str, Any], width: int, height: int) -> list[float]:
    x = float(value["x"]) / 100.0 * width
    y = float(value["y"]) / 100.0 * height
    w = float(value["width"]) / 100.0 * width
    h = float(value["height"]) / 100.0 * height
    rotation = float(value.get("rotation") or 0.0) % 360.0
    if min(rotation, 360.0 - rotation) <= 1e-6:
        return [x, y, x + w, y + h]
    return _rotated_ends_aabb(x, y, w, h, rotation)


def result_image_size(result_items: list[dict[str, Any]]) -> tuple[int, int] | None:
    for item in result_items:
        w = int(item.get("original_width") or 0)
        h = int(item.get("original_height") or 0)
        if w > 0 and h > 0:
            return w, h
    return None


def collect_label_names(input_path: Path, *, recursive: bool = True) -> list[str]:
    names: set[str] = set()
    for _, task in iter_ls_tasks(input_path, recursive=recursive):
        for item in extract_rectangle_results(task):
            if item.get("type") != "rectanglelabels":
                continue
            labels = (item.get("value") or {}).get("rectanglelabels") or []
            for label in labels:
                names.add(str(label))
    return sorted(names)


def build_class_maps(
    categories_path: Path | None,
    input_path: Path,
    *,
    recursive: bool = True,
) -> tuple[list[str], dict[str, int]]:
    if categories_path is not None and categories_path.is_file():
        class_names, id_to_name = load_categories(categories_path)
        name_to_id = {name: cid for cid, name in id_to_name.items()}
        return class_names, name_to_id
    class_names = collect_label_names(input_path, recursive=recursive)
    name_to_id = {name: idx for idx, name in enumerate(class_names)}
    return class_names, name_to_id


def results_to_annotations(
    result_items: list[dict[str, Any]],
    *,
    width: int,
    height: int,
    name_to_id: dict[str, int],
) -> tuple[list[dict[str, Any]], int]:
    annotations: list[dict[str, Any]] = []
    skipped_unknown = 0
    for item in result_items:
        if item.get("type") != "rectanglelabels":
            logger.warning("跳过非 rectanglelabels: type=%s", item.get("type"))
            continue
        value = item.get("value") or {}
        labels = value.get("rectanglelabels") or []
        if not labels:
            continue
        label = str(labels[0])
        if label not in name_to_id:
            logger.warning("未知类别，跳过: %s", label)
            skipped_unknown += 1
            continue
        annotations.append(
            {
                "category_id": name_to_id[label],
                "type": 3,
                "points": ls_value_to_points(value, width, height),
            }
        )
    return annotations, skipped_unknown


def labelstudio_to_voc(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    recursive: bool = True,
    categories_path: str | Path | None = None,
    copy_images: bool = True,
) -> dict[str, int]:
    """把 Label Studio 导出转为 Pascal VOC。

    输入目录同时作为 JSON 与图像根；默认递归子目录。
    输出 ``JPEGImages/``、``Annotations/``、``predefined_classes.txt``。
    返回 images / labels / boxes / negatives / skipped / unknown_labels。
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    image_root = input_path if input_path.is_dir() else input_path.parent
    categories = Path(categories_path) if categories_path else None
    class_names, name_to_id = build_class_maps(categories, input_path, recursive=recursive)
    id_to_name = {idx: name for name, idx in name_to_id.items()}

    stats = {
        "images": 0,
        "labels": 0,
        "boxes": 0,
        "negatives": 0,
        "skipped": 0,
        "unknown_labels": 0,
    }
    image_out_dir = output_dir / "JPEGImages"
    label_out_dir = output_dir / "Annotations"
    image_out_dir.mkdir(parents=True, exist_ok=True)
    label_out_dir.mkdir(parents=True, exist_ok=True)

    for source_path, task in iter_ls_tasks(input_path, recursive=recursive):
        try:
            file_name = resolve_image_name(task, source_path)
        except ValueError as exc:
            logger.warning("%s (%s)", exc, source_path.name if source_path else "")
            stats["skipped"] += 1
            continue

        image_path = find_image_for_task(
            image_root, file_name, source_path=source_path, recursive=recursive
        )
        if image_path is None:
            logger.warning("未找到图像文件: %s", file_name)
            stats["skipped"] += 1
            continue

        result_items = extract_rectangle_results(task)
        try:
            width, height = read_image_size(image_path)
        except ValueError as exc:
            logger.warning("%s", exc)
            stats["skipped"] += 1
            continue

        meta_size = result_image_size(result_items)
        if meta_size and meta_size != (width, height):
            logger.info(
                "尺寸校正 %s: export=%sx%s, actual=%sx%s",
                image_path.name, meta_size[0], meta_size[1], width, height,
            )

        annotations, skipped_unknown = results_to_annotations(
            result_items, width=width, height=height, name_to_id=name_to_id
        )
        stats["unknown_labels"] += skipped_unknown
        if not annotations:
            stats["negatives"] += 1

        image_name = image_path.name
        image_out_path = image_out_dir / image_name
        if copy_images:
            shutil.copy2(image_path, image_out_path)
        else:
            image_out_path = image_path

        for ann in annotations:
            if bbox_to_voc_ints(ann["points"], width, height) is not None:
                stats["boxes"] += 1

        voc_xml = build_voc_xml(
            image_name=image_name,
            image_path=image_out_path,
            folder_name="JPEGImages",
            width=width,
            height=height,
            annotations=annotations,
            id_to_name=id_to_name,
        )
        (label_out_dir / f"{Path(image_name).stem}.xml").write_text(voc_xml, encoding="utf-8")
        stats["images"] += 1
        stats["labels"] += 1

    write_voc_predefined_classes(output_dir, class_names)
    logger.info(
        "转换完成 images=%s boxes=%s negatives=%s skipped=%s unknown=%s classes=%s",
        stats["images"], stats["boxes"], stats["negatives"],
        stats["skipped"], stats["unknown_labels"], len(class_names),
    )
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # 路径只从环境变量读，不把具体目录写进本文件。
    INPUT_DIR = os.environ.get("LS_INPUT_DIR", "").strip()
    OUTPUT_DIR = os.environ.get("LS_OUTPUT_DIR", "").strip()
    CATEGORIES = os.environ.get("LS_CATEGORIES", "").strip() or None
    if not INPUT_DIR or not OUTPUT_DIR:
        raise SystemExit("需要环境变量 LS_INPUT_DIR（导出目录）和 LS_OUTPUT_DIR（VOC 输出目录）")
    print(
        labelstudio_to_voc(
            input_path=INPUT_DIR,
            output_dir=OUTPUT_DIR,
            categories_path=CATEGORIES,
        )
    )
