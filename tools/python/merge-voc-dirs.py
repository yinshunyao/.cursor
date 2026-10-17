#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""合并两个 Pascal VOC 目录，按图片 MD5 去重。

先写入第一个目录的样本，再写入第二个。内容相同的图片只保留先出现的那一份，
重复项（图片及对应标注）不复制，清单写到目标目录。路径用环境变量传入。
"""
from __future__ import annotations

import csv
import hashlib
import logging
import os
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".bmp", ".png", ".tif", ".tiff", ".webp"}
IMAGE_DIR_NAMES = ("JPEGImages", "images", "Images")
ANNOTATION_DIR_NAMES = ("Annotations", "annotations", "labels")
DUPLICATE_LIST_NAME = "duplicate_files.csv"
_TAG_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _find_subdir(root: Path, candidates: tuple[str, ...]) -> Path | None:
    for name in candidates:
        path = root / name
        if path.is_dir():
            return path
    return None


def _iter_images(image_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in image_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            files.append(path)
    files.sort(key=lambda p: str(p.relative_to(image_dir)))
    return files


def _file_md5(path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _resolve_xml(annotation_dir: Path | None, image_path: Path, image_dir: Path) -> Path | None:
    if annotation_dir is None:
        return None
    rel = image_path.relative_to(image_dir)
    xml_path = annotation_dir / rel.with_suffix(".xml")
    if xml_path.is_file():
        return xml_path
    flat = annotation_dir / f"{image_path.stem}.xml"
    if flat.is_file():
        return flat
    return None


def _unique_dest(dest: Path, output_image_dir: Path, used_rels: set[str]) -> Path:
    rel = str(dest.relative_to(output_image_dir))
    if rel not in used_rels and not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    index = 2
    while True:
        candidate = dest.with_name(f"{stem}__{index}{suffix}")
        candidate_rel = str(candidate.relative_to(output_image_dir))
        if candidate_rel not in used_rels and not candidate.exists():
            return candidate
        index += 1


def _replace_xml_tag(text: str, tag: str, value: str) -> str:
    pattern = _TAG_RE_CACHE.get(tag)
    if pattern is None:
        pattern = re.compile(rf"(<{tag}>)(.*?)(</{tag}>)", re.DOTALL)
        _TAG_RE_CACHE[tag] = pattern
    if pattern.search(text) is None:
        return text
    return pattern.sub(lambda match: f"{match.group(1)}{value}{match.group(3)}", text, count=1)


def _read_class_names(voc_root: Path) -> list[str]:
    path = voc_root / "predefined_classes.txt"
    if not path.is_file():
        return []
    names: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _merge_class_names(source_a: Path, source_b: Path, output_dir: Path) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for name in _read_class_names(source_a) + _read_class_names(source_b):
        if name in seen:
            continue
        seen.add(name)
        merged.append(name)
    if merged:
        (output_dir / "predefined_classes.txt").write_text(
            "\n".join(merged) + "\n",
            encoding="utf-8",
        )
    return merged


def _copy_image_and_xml(
    image_path: Path,
    xml_path: Path | None,
    image_dir: Path,
    output_image_dir: Path,
    output_annotation_dir: Path,
    used_rels: set[str],
) -> tuple[str, str]:
    rel = image_path.relative_to(image_dir)
    dest_image = _unique_dest(output_image_dir / rel, output_image_dir, used_rels)
    dest_image.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image_path, dest_image)
    used_rels.add(str(dest_image.relative_to(output_image_dir)))

    dest_xml_rel = ""
    if xml_path is not None:
        dest_xml = output_annotation_dir / dest_image.relative_to(output_image_dir).with_suffix(".xml")
        dest_xml.parent.mkdir(parents=True, exist_ok=True)
        text = xml_path.read_text(encoding="utf-8")
        text = _replace_xml_tag(text, "filename", dest_image.name)
        text = _replace_xml_tag(text, "path", str(dest_image.resolve()))
        dest_xml.write_text(text, encoding="utf-8")
        dest_xml_rel = str(dest_xml.relative_to(output_annotation_dir.parent))
    return str(dest_image.relative_to(output_image_dir.parent)), dest_xml_rel


def merge_voc_dirs(source_a: Path | str, source_b: Path | str, output_dir: Path | str) -> dict:
    """合并两个 VOC 目录到新目录，并写出重复文件清单。"""
    sources = [Path(source_a).resolve(), Path(source_b).resolve()]
    output_dir = Path(output_dir).resolve()
    if sources[0] == sources[1]:
        raise ValueError("两个源目录不能相同")
    for source in sources:
        if not source.is_dir():
            raise FileNotFoundError(f"源目录不存在: {source}")
        if output_dir == source or output_dir.is_relative_to(source):
            raise ValueError("目标目录不能放在源目录里面")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"目标目录已存在且非空: {output_dir}")

    prepared: list[dict] = []
    for index, source in enumerate(sources, start=1):
        image_dir = _find_subdir(source, IMAGE_DIR_NAMES)
        if image_dir is None:
            raise FileNotFoundError(
                f"未找到图片目录（候选: {', '.join(IMAGE_DIR_NAMES)}）: {source}"
            )
        prepared.append(
            {
                "index": index,
                "root": source,
                "name": source.name,
                "image_dir": image_dir,
                "annotation_dir": _find_subdir(source, ANNOTATION_DIR_NAMES),
                "images": _iter_images(image_dir),
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_image_dir = output_dir / "JPEGImages"
    output_annotation_dir = output_dir / "Annotations"
    output_image_dir.mkdir(parents=True, exist_ok=True)
    output_annotation_dir.mkdir(parents=True, exist_ok=True)

    seen_md5: dict[str, dict] = {}
    used_rels: set[str] = set()
    duplicates: list[dict] = []
    kept = 0
    missing_xml = 0

    for source in prepared:
        images: list[Path] = source["images"]
        logger.info("扫描 %s ，图片 %d 张", source["name"], len(images))
        for offset, image_path in enumerate(images, start=1):
            digest = _file_md5(image_path)
            rel_image = str(image_path.relative_to(source["root"]))
            xml_path = _resolve_xml(source["annotation_dir"], image_path, source["image_dir"])
            rel_xml = "" if xml_path is None else str(xml_path.relative_to(source["root"]))
            previous = seen_md5.get(digest)
            if previous is not None:
                duplicates.append(
                    {
                        "md5": digest,
                        "kept_source_index": previous["source_index"],
                        "kept_source_name": previous["source_name"],
                        "kept_image": previous["image"],
                        "kept_annotation": previous["annotation"],
                        "duplicate_source_index": source["index"],
                        "duplicate_source_name": source["name"],
                        "duplicate_image": rel_image,
                        "duplicate_annotation": rel_xml,
                    }
                )
                continue

            if xml_path is None:
                missing_xml += 1
                logger.warning("缺少对应标注: %s", image_path)
            kept_image, kept_xml = _copy_image_and_xml(
                image_path=image_path,
                xml_path=xml_path,
                image_dir=source["image_dir"],
                output_image_dir=output_image_dir,
                output_annotation_dir=output_annotation_dir,
                used_rels=used_rels,
            )
            seen_md5[digest] = {
                "source_index": source["index"],
                "source_name": source["name"],
                "image": rel_image,
                "annotation": rel_xml,
                "output_image": kept_image,
                "output_annotation": kept_xml,
            }
            kept += 1
            if offset % 200 == 0 or offset == len(images):
                logger.info("已处理 %s %d / %d", source["name"], offset, len(images))

    classes = _merge_class_names(sources[0], sources[1], output_dir)
    list_path = output_dir / DUPLICATE_LIST_NAME
    with list_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "md5",
                "kept_source_index",
                "kept_source_name",
                "kept_image",
                "kept_annotation",
                "duplicate_source_index",
                "duplicate_source_name",
                "duplicate_image",
                "duplicate_annotation",
            ],
        )
        writer.writeheader()
        writer.writerows(duplicates)

    summary = {
        "source_a": str(sources[0]),
        "source_b": str(sources[1]),
        "output_dir": str(output_dir),
        "source_a_images": len(prepared[0]["images"]),
        "source_b_images": len(prepared[1]["images"]),
        "kept_images": kept,
        "duplicate_count": len(duplicates),
        "missing_xml_count": missing_xml,
        "class_count": len(classes),
        "duplicate_list": str(list_path),
    }
    logger.info(
        "完成 kept=%d duplicate=%d missing_xml=%d classes=%d list=%s",
        kept,
        len(duplicates),
        missing_xml,
        len(classes),
        list_path,
    )
    return summary


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    source_a = os.environ.get("VOC_SOURCE_A", "").strip()
    source_b = os.environ.get("VOC_SOURCE_B", "").strip()
    output_dir = os.environ.get("VOC_OUTPUT_DIR", "").strip()
    if not source_a or not source_b or not output_dir:
        raise SystemExit(
            "需要环境变量 VOC_SOURCE_A、VOC_SOURCE_B、VOC_OUTPUT_DIR"
        )
    print(json.dumps(merge_voc_dirs(source_a, source_b, output_dir), ensure_ascii=False, indent=2))
