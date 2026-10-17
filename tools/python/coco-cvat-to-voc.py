#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""将 CVAT 导出的 COCO 检测标注转换为 Pascal VOC（LabelImg）XML。

支持单份 COCO JSON，或目录内多份 JSON（如 train/val 各一份）。
具体路径用环境变量或改 `__main__` 变量传入，不写项目敏感路径进仓库默认值。
仅标准库。
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import struct
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".bmp", ".png", ".tif", ".tiff", ".webp"}


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


def _xml_tostring(root: ET.Element) -> str:
    elem = ET.ElementTree(root)
    try:
        ET.indent(elem, space="    ")
    except AttributeError:
        pass
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def coco_bbox_to_voc_ints(
    bbox: list[float] | tuple[float, ...],
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    """COCO bbox=[x, y, w, h] → VOC xmin/ymin/xmax/ymax（像素整数）。"""
    if len(bbox) != 4:
        return None
    x, y, w, h = (float(v) for v in bbox)
    if w <= 0 or h <= 0:
        return None
    x1, y1, x2, y2 = x, y, x + w, y + h
    xmin = max(0, min(width, int(round(x1))))
    ymin = max(0, min(height, int(round(y1))))
    xmax = max(0, min(width, int(round(x2))))
    ymax = max(0, min(height, int(round(y2))))
    if xmax <= xmin or ymax <= ymin:
        return None
    return xmin, ymin, xmax, ymax


def build_voc_xml(
    *,
    image_name: str,
    image_path: Path,
    folder_name: str,
    width: int,
    height: int,
    objects: list[dict[str, Any]],
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

    for obj in objects:
        node = ET.SubElement(root, "object")
        ET.SubElement(node, "name").text = str(obj["name"])
        ET.SubElement(node, "pose").text = "Unspecified"
        ET.SubElement(node, "truncated").text = "1" if obj.get("truncated") else "0"
        ET.SubElement(node, "difficult").text = "1" if obj.get("difficult") else "0"
        bndbox = ET.SubElement(node, "bndbox")
        ET.SubElement(bndbox, "xmin").text = str(obj["xmin"])
        ET.SubElement(bndbox, "ymin").text = str(obj["ymin"])
        ET.SubElement(bndbox, "xmax").text = str(obj["xmax"])
        ET.SubElement(bndbox, "ymax").text = str(obj["ymax"])
    return _xml_tostring(root)


def write_voc_predefined_classes(output_dir: Path, class_names: list[str]) -> None:
    (output_dir / "predefined_classes.txt").write_text(
        "\n".join(class_names) + ("\n" if class_names else ""),
        encoding="utf-8",
    )


def find_image_file(image_dirs: list[Path], file_name: str) -> Path | None:
    for image_dir in image_dirs:
        direct = image_dir / file_name
        if direct.is_file():
            return direct
        nested = image_dir / Path(file_name).name
        if nested.is_file():
            return nested
        stem = Path(file_name).stem
        for suffix in IMAGE_SUFFIXES:
            candidate = image_dir / f"{stem}{suffix}"
            if candidate.is_file():
                return candidate
    return None


def _is_coco_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("images"), list)
        and isinstance(payload.get("annotations"), list)
        and isinstance(payload.get("categories"), list)
    )


def discover_coco_jsons(input_path: Path, *, recursive: bool = True) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"输入不存在: {input_path}")
    pattern = "**/*.json" if recursive else "*.json"
    found: list[Path] = []
    for path in sorted(input_path.glob(pattern)):
        if not path.is_file() or path.name.startswith("._"):
            continue
        try:
            with path.open(encoding="utf-8") as fp:
                payload = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("跳过无法解析的 JSON: %s (%s)", path, exc)
            continue
        if _is_coco_payload(payload):
            found.append(path)
    return found


def _category_maps(categories: list[dict[str, Any]]) -> tuple[list[str], dict[int, str]]:
    id_to_name: dict[int, str] = {}
    names: list[str] = []
    for item in sorted(categories, key=lambda x: int(x["id"])):
        cid = int(item["id"])
        name = str(item["name"])
        id_to_name[cid] = name
        if name not in names:
            names.append(name)
    return names, id_to_name


def _ann_truncated_difficult(ann: dict[str, Any]) -> tuple[bool, bool]:
    attrs = ann.get("attributes") or {}
    truncated = bool(attrs.get("occluded", False))
    rotation = float(attrs.get("rotation", 0.0) or 0.0)
    # VOC 无旋转框；有明显旋转时标 difficult，便于下游筛选
    difficult = bool(ann.get("iscrowd", 0)) or abs(rotation) > 1e-3
    return truncated, difficult


def convert_one_coco(
    coco_json: Path,
    *,
    image_dirs: list[Path],
    annotation_out_dir: Path,
    image_out_dir: Path | None,
    copy_images: bool,
    skip_missing_image: bool,
    write_empty: bool,
    folder_name: str,
) -> dict[str, Any]:
    with coco_json.open(encoding="utf-8") as fp:
        payload = json.load(fp)
    if not _is_coco_payload(payload):
        raise ValueError(f"不是 COCO 检测标注 JSON: {coco_json}")

    class_names, id_to_name = _category_maps(payload["categories"])
    anns_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ann in payload["annotations"]:
        if not isinstance(ann, dict):
            continue
        image_id = int(ann["image_id"])
        anns_by_image[image_id].append(ann)

    stats = {
        "coco_json": str(coco_json),
        "images": 0,
        "xml_written": 0,
        "boxes": 0,
        "skipped_boxes": 0,
        "missing_images": 0,
        "empty_xml": 0,
        "classes": class_names,
    }

    annotation_out_dir.mkdir(parents=True, exist_ok=True)
    if copy_images and image_out_dir is not None:
        image_out_dir.mkdir(parents=True, exist_ok=True)

    for image_info in payload["images"]:
        if not isinstance(image_info, dict):
            continue
        stats["images"] += 1
        image_id = int(image_info["id"])
        file_name = str(image_info["file_name"])
        src_image = find_image_file(image_dirs, file_name)
        if src_image is None:
            stats["missing_images"] += 1
            msg = f"找不到图像: {file_name} (json={coco_json.name})"
            if skip_missing_image:
                logger.warning(msg)
                continue
            raise FileNotFoundError(msg)

        width = int(image_info.get("width") or 0)
        height = int(image_info.get("height") or 0)
        if width <= 0 or height <= 0:
            width, height = read_image_size(src_image)

        objects: list[dict[str, Any]] = []
        for ann in anns_by_image.get(image_id, []):
            bbox = ann.get("bbox")
            if not isinstance(bbox, (list, tuple)):
                stats["skipped_boxes"] += 1
                continue
            voc_box = coco_bbox_to_voc_ints(bbox, width, height)
            if voc_box is None:
                stats["skipped_boxes"] += 1
                continue
            xmin, ymin, xmax, ymax = voc_box
            cat_id = int(ann["category_id"])
            truncated, difficult = _ann_truncated_difficult(ann)
            objects.append(
                {
                    "name": id_to_name.get(cat_id, str(cat_id)),
                    "xmin": xmin,
                    "ymin": ymin,
                    "xmax": xmax,
                    "ymax": ymax,
                    "truncated": truncated,
                    "difficult": difficult,
                }
            )

        if not objects and not write_empty:
            continue

        out_image_name = src_image.name
        if copy_images and image_out_dir is not None:
            dest_image = image_out_dir / out_image_name
            if not dest_image.exists():
                shutil.copy2(src_image, dest_image)
            path_for_xml = dest_image
        else:
            path_for_xml = src_image

        xml_text = build_voc_xml(
            image_name=out_image_name,
            image_path=path_for_xml,
            folder_name=folder_name,
            width=width,
            height=height,
            objects=objects,
        )
        (annotation_out_dir / f"{src_image.stem}.xml").write_text(xml_text, encoding="utf-8")
        stats["xml_written"] += 1
        stats["boxes"] += len(objects)
        if not objects:
            stats["empty_xml"] += 1

    return stats


def coco_cvat_to_voc(
    input_path: Path | str,
    output_dir: Path | str,
    *,
    image_dir: Path | str | None = None,
    recursive: bool = True,
    copy_images: bool = True,
    skip_missing_image: bool = True,
    write_empty: bool = True,
    merge_splits: bool = True,
) -> dict[str, Any]:
    """CVAT COCO → Pascal VOC。

    Parameters
    ----------
    input_path:
        COCO JSON 文件，或包含若干 COCO JSON 的目录（如数据集根目录）。
    output_dir:
        VOC 输出根目录，将写入 `Annotations/`、`JPEGImages/`（可选）、`predefined_classes.txt`。
    image_dir:
        额外的图像搜索目录；默认还会在每个 JSON 所在目录及其父目录查找。
    merge_splits:
        True 时多份 JSON 合并进同一套 Annotations/JPEGImages；
        False 时按 JSON 文件名（去后缀）分子目录。
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    extra_image_dir = Path(image_dir) if image_dir else None

    coco_jsons = discover_coco_jsons(input_path, recursive=recursive)
    if not coco_jsons:
        raise FileNotFoundError(f"未找到 COCO JSON: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    all_class_names: list[str] = []
    seen_class: set[str] = set()
    per_json: list[dict[str, Any]] = []

    for coco_json in coco_jsons:
        search_dirs: list[Path] = [coco_json.parent]
        parent = coco_json.parent.parent
        if parent not in search_dirs:
            search_dirs.append(parent)
        if extra_image_dir is not None and extra_image_dir not in search_dirs:
            search_dirs.insert(0, extra_image_dir)

        if merge_splits:
            annotation_out = output_dir / "Annotations"
            image_out = output_dir / "JPEGImages" if copy_images else None
            folder_name = "JPEGImages"
        else:
            split_name = coco_json.stem
            split_root = output_dir / split_name
            annotation_out = split_root / "Annotations"
            image_out = split_root / "JPEGImages" if copy_images else None
            folder_name = "JPEGImages"

        stats = convert_one_coco(
            coco_json,
            image_dirs=search_dirs,
            annotation_out_dir=annotation_out,
            image_out_dir=image_out,
            copy_images=copy_images,
            skip_missing_image=skip_missing_image,
            write_empty=write_empty,
            folder_name=folder_name,
        )
        per_json.append(stats)
        for name in stats["classes"]:
            if name not in seen_class:
                seen_class.add(name)
                all_class_names.append(name)

        if not merge_splits:
            write_voc_predefined_classes(split_root, stats["classes"])

    if merge_splits:
        write_voc_predefined_classes(output_dir, all_class_names)
    else:
        write_voc_predefined_classes(output_dir, all_class_names)

    summary = {
        "input": str(input_path),
        "output": str(output_dir),
        "coco_json_count": len(coco_jsons),
        "classes": all_class_names,
        "images": sum(s["images"] for s in per_json),
        "xml_written": sum(s["xml_written"] for s in per_json),
        "boxes": sum(s["boxes"] for s in per_json),
        "skipped_boxes": sum(s["skipped_boxes"] for s in per_json),
        "missing_images": sum(s["missing_images"] for s in per_json),
        "empty_xml": sum(s["empty_xml"] for s in per_json),
        "per_json": per_json,
    }
    logger.info(
        "完成 coco→voc: json=%d images=%d xml=%d boxes=%d missing=%d classes=%d → %s",
        summary["coco_json_count"],
        summary["images"],
        summary["xml_written"],
        summary["boxes"],
        summary["missing_images"],
        len(all_class_names),
        output_dir,
    )
    return summary


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip() not in {"0", "false", "False", "no", "NO"}


def run_from_env() -> dict[str, Any]:
    input_path = os.environ.get("COCO_INPUT", "").strip()
    output_dir = os.environ.get("VOC_OUTPUT_DIR", "").strip()
    if not input_path or not output_dir:
        raise SystemExit(
            "需要环境变量 COCO_INPUT（COCO JSON 或数据集目录）和 VOC_OUTPUT_DIR（VOC 输出目录）"
        )
    image_dir = os.environ.get("COCO_IMAGE_DIR", "").strip() or None
    return coco_cvat_to_voc(
        input_path,
        output_dir,
        image_dir=image_dir,
        recursive=_env_bool("COCO_RECURSIVE", True),
        copy_images=_env_bool("COCO_COPY_IMAGES", True),
        skip_missing_image=_env_bool("COCO_SKIP_MISSING", True),
        write_empty=_env_bool("COCO_WRITE_EMPTY", True),
        merge_splits=_env_bool("COCO_MERGE_SPLITS", True),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if os.environ.get("COCO_INPUT") and os.environ.get("VOC_OUTPUT_DIR"):
        print(json.dumps(run_from_env(), ensure_ascii=False, indent=2))
    else:
        # 本地试跑：改下面变量，或改用环境变量调用
        COCO_INPUT = Path("<数据集根目录或某个 coco.json>")
        VOC_OUTPUT_DIR = Path("<VOC输出目录>")
        COCO_IMAGE_DIR: Path | None = None  # 图像不在 JSON 同级时再填
        COCO_COPY_IMAGES = True
        COCO_MERGE_SPLITS = True
        summary = coco_cvat_to_voc(
            COCO_INPUT,
            VOC_OUTPUT_DIR,
            image_dir=COCO_IMAGE_DIR,
            copy_images=COCO_COPY_IMAGES,
            merge_splits=COCO_MERGE_SPLITS,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
