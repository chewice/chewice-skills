#!/usr/bin/env python3
"""Load the executable assay and source capability tables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class CapabilityError(ValueError):
    """A capability table is absent or internally inconsistent."""


def _candidate_paths(root: Path | None, filename: str) -> list[Path]:
    paths: list[Path] = []
    if root is not None:
        paths.extend((root / "config" / filename, root / filename))
    paths.append(Path(__file__).resolve().parent.parent / filename)
    return paths


def load_table(filename: str, root: Path | None = None) -> dict[str, Any]:
    for path in _candidate_paths(root, filename):
        if path.is_file():
            with path.open() as handle:
                data = yaml.safe_load(handle)
            if not isinstance(data, dict):
                raise CapabilityError(f"{path} 不是 YAML mapping")
            data["_path"] = str(path)
            return data
    raise CapabilityError(f"找不到能力表 {filename}")


def load_assay_capabilities(root: Path | None = None) -> dict[str, Any]:
    data = load_table("assay_capability.yaml", root)
    if not isinstance(data.get("assays"), dict):
        raise CapabilityError("assay_capability.yaml 缺少 assays")
    return data


def load_source_capabilities(root: Path | None = None) -> dict[str, Any]:
    data = load_table("source_capability.yaml", root)
    if not isinstance(data.get("sources"), dict) or not isinstance(
        data.get("object_classes"), dict
    ):
        raise CapabilityError("source_capability.yaml 缺少 sources/object_classes")
    return data


def assay_capability(modality: str, root: Path | None = None) -> tuple[str, dict[str, Any]]:
    needle = modality.strip().lower().replace("-", "").replace("_", "")
    table = load_assay_capabilities(root)
    for key, capability in table["assays"].items():
        labels = [key, *capability.get("labels", [])]
        normalized = {
            str(label).lower().replace("-", "").replace("_", "") for label in labels
        }
        if needle in normalized:
            return key, capability
    raise CapabilityError(f"能力表未定义 modality={modality!r}")


def source_capability(source: str, root: Path | None = None) -> dict[str, Any]:
    table = load_source_capabilities(root)
    try:
        return table["sources"][source]
    except KeyError as exc:
        raise CapabilityError(f"能力表未定义 source={source!r}") from exc


def classify_source(
    source: str,
    provenance: str,
    root: Path | None = None,
) -> tuple[str, str, dict[str, Any]]:
    table = load_source_capabilities(root)
    source_info = source_capability(source, root)
    for object_class in source_info.get("object_classes", []):
        info = table["object_classes"].get(object_class, {})
        if provenance in info.get("provenance_classes", []):
            return object_class, str(info.get("quality_class", "")), info
    raise CapabilityError(
        f"source={source!r} 不允许 provenance={provenance!r}"
    )
