#!/usr/bin/env python3
"""Sanity-check common NetEase Bedrock ModSDK pack references."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        errors.append(f"JSON parse error: {path}: {exc}")
        return None


def safe_namespace(value: str | None, project: Path) -> str:
    if value:
        return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")
    for child in project.iterdir():
        if child.is_dir() and child.name.endswith("_behavior"):
            return child.name[:-9]
    raise SystemExit("namespace not provided and *_behavior folder was not found")


def exists_by_value(base: Path, folders: list[str], value: str) -> bool:
    clean = value
    for prefix in ("Texture.", "Material.", "Geometry."):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    clean = clean.replace(".", "_").replace(":", "_")
    for folder in folders:
        root = base / folder
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            if clean.lower() in path.stem.lower():
                return True
    return False


def collect_defined_keys(obj, container_key: str) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        node = obj.get(container_key)
        if isinstance(node, dict):
            keys.update(str(k) for k in node.keys())
        for value in obj.values():
            keys.update(collect_defined_keys(value, container_key))
    elif isinstance(obj, list):
        for value in obj:
            keys.update(collect_defined_keys(value, container_key))
    return keys


def lint_client_entities(res: Path, beh: Path, errors: list[str], warnings: list[str]) -> None:
    render_keys = set()
    material_keys = set()
    animation_controller_keys = set()
    for path in (res / "render_controllers").glob("*.json") if (res / "render_controllers").exists() else []:
        data = load_json(path, errors)
        if data is not None:
            render_keys.update(collect_defined_keys(data, "render_controllers"))
    for path in (res / "materials").glob("*.json") if (res / "materials").exists() else []:
        data = load_json(path, errors)
        if data is not None:
            material_keys.update(collect_defined_keys(data, "materials"))
    for path in (res / "animation_controllers").glob("*.json") if (res / "animation_controllers").exists() else []:
        data = load_json(path, errors)
        if data is not None:
            animation_controller_keys.update(collect_defined_keys(data, "animation_controllers"))

    for path in (res / "entity").glob("*.json") if (res / "entity").exists() else []:
        data = load_json(path, errors)
        if not isinstance(data, dict):
            continue
        desc = (((data.get("minecraft:client_entity") or {}).get("description")) or {})
        identifier = desc.get("identifier", path.stem)
        for key in desc.get("render_controllers", []) or []:
            if isinstance(key, dict):
                key = next(iter(key.values()), "")
            if key and key not in render_keys:
                warnings.append(f"Client entity {identifier} references render controller {key}, but no matching key was found under resource/render_controllers.")
        for key in (desc.get("materials") or {}).values():
            if key and key not in material_keys and not str(key).startswith("entity_"):
                warnings.append(f"Client entity {identifier} references material {key}, but no matching custom material key was found.")
        for key in (desc.get("animation_controllers") or []):
            if isinstance(key, dict):
                key = next(iter(key.values()), "")
            if key and key not in animation_controller_keys:
                warnings.append(f"Client entity {identifier} references animation controller {key}, but no matching key was found.")
        for key in (desc.get("geometry") or {}).values():
            if key and not exists_by_value(res, ["models", "models/entity", "models/netease_block"], str(key)):
                warnings.append(f"Client entity {identifier} references geometry {key}; check that the model file exists.")
        for key in (desc.get("textures") or {}).values():
            texture_path = res / (str(key) + ".png")
            if not texture_path.exists():
                warnings.append(f"Client entity {identifier} references texture {key}; {texture_path} was not found.")

    if (beh / "entities").exists():
        client_names = {p.stem.replace(".entity", "") for p in (res / "entity").glob("*.json")} if (res / "entity").exists() else set()
        for path in (beh / "entities").glob("*.json"):
            data = load_json(path, errors)
            if not isinstance(data, dict):
                continue
            desc = (((data.get("minecraft:entity") or {}).get("description")) or {})
            identifier = str(desc.get("identifier", path.stem)).split(":")[-1]
            if identifier not in client_names:
                warnings.append(f"Behavior entity {desc.get('identifier', path.stem)} has no matching resource/entity client file.")


def lint_ui(res: Path, errors: list[str], warnings: list[str]) -> None:
    ui_dir = res / "ui"
    if not ui_dir.exists():
        return
    defs_path = ui_dir / "_ui_defs.json"
    if not defs_path.exists():
        warnings.append("resource/ui exists but _ui_defs.json is missing.")
        return
    data = load_json(defs_path, errors)
    if not isinstance(data, dict):
        return
    entries = data.get("ui_defs") or []
    for entry in entries:
        rel = str(entry)
        if not (res / rel).exists():
            warnings.append(f"_ui_defs.json references missing UI file: {rel}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--namespace")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = Path(args.project).resolve()
    ns = safe_namespace(args.namespace, project)
    beh = project / f"{ns}_behavior"
    res = project / f"{ns}_resource"
    errors: list[str] = []
    warnings: list[str] = []
    if not beh.exists():
        errors.append(f"Missing behavior pack folder: {beh}")
    if not res.exists():
        errors.append(f"Missing resource pack folder: {res}")
    for pack in (beh, res):
        manifest = pack / "manifest.json"
        if not manifest.exists():
            errors.append(f"Missing manifest: {manifest}")
        else:
            load_json(manifest, errors)
    if res.exists():
        lint_ui(res, errors, warnings)
    if beh.exists() and res.exists():
        lint_client_entities(res, beh, errors, warnings)
    for item in errors:
        print(f"ERROR: {item}")
    for item in warnings:
        print(f"WARN: {item}")
    if not errors and not warnings:
        print("OK: no common reference problems found.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
