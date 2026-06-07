#!/usr/bin/env python3
"""Detect NetEase Bedrock/MCStudio project features and prepared knowledge indexes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PROJECT_PATTERNS = [
    ("studio.json", "studio.json"),
    ("behavior_pack_dir", "*_behavior"),
    ("resource_pack_dir", "*_resource"),
    ("behavior_pack_dir_short", "*_beh"),
    ("resource_pack_dir_short", "*_res"),
    ("scripts_dir", "*Scripts"),
    ("netease_dir", "netease_*"),
]

CODE_PATTERNS = {
    "mod_binding": r"from\s+mod\.common\.mod\s+import\s+Mod",
    "client_api": r"import\s+mod\.client\.extraClientApi\s+as\s+clientApi",
    "server_api": r"import\s+mod\.server\.extraServerApi\s+as\s+serverApi",
    "register_system": r"RegisterSystem\s*\(",
    "listen_event": r"ListenForEvent\s*\(",
    "engine_comp_factory": r"(GetEngineCompFactory|CreateEngineCompFactory)\s*\(",
    "client_server_message": r"(BroadcastToServer|NotifyToClient)\s*\(",
}


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def find_registry(explicit: str | None, root: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if root:
        candidates.append(Path(root).expanduser() / "knowledge_registry.json")
    candidates.append(Path.home() / ".codex" / "mc-bedrock-fast-code-data" / "knowledge_registry.json")
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def detect_project(project: Path) -> dict[str, object]:
    signals: list[dict[str, str]] = []
    for child in project.iterdir() if project.exists() else []:
        name = child.name
        if name == "studio.json":
            signals.append({"kind": "studio.json", "path": name})
        elif child.is_dir() and name.endswith("_behavior"):
            signals.append({"kind": "behavior_pack_dir", "path": name})
        elif child.is_dir() and name.endswith("_resource"):
            signals.append({"kind": "resource_pack_dir", "path": name})
        elif child.is_dir() and name.endswith("_beh"):
            signals.append({"kind": "behavior_pack_dir_short", "path": name})
        elif child.is_dir() and name.endswith("_res"):
            signals.append({"kind": "resource_pack_dir_short", "path": name})
        elif child.is_dir() and name.endswith("Scripts"):
            signals.append({"kind": "scripts_dir", "path": name})
        elif child.is_dir() and name.startswith("netease_"):
            signals.append({"kind": "netease_dir", "path": name})
    py_files = list(project.rglob("*.py"))[:500]
    for path in py_files:
        rel = path.relative_to(project)
        if (project / "SKILL.md").exists() and rel.parts and rel.parts[0] == "scripts":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for kind, pattern in CODE_PATTERNS.items():
            if re.search(pattern, text):
                signals.append({"kind": kind, "path": str(rel)})
    namespaces = sorted({
        p.name[:-9] for p in project.glob("*_behavior") if p.is_dir()
    } | {
        p.name[:-4] for p in project.glob("*_beh") if p.is_dir()
    })
    return {
        "project": str(project),
        "is_netease_bedrock_project": bool(signals),
        "signals": signals[:80],
        "namespaces": namespaces,
    }


def detect_knowledge(registry_path: Path | None) -> dict[str, object]:
    if registry_path is None:
        return {
            "registry_found": False,
            "missing": ["knowledge_registry.json", "api_references", "demo_index", "vanilla_indexes"],
        }
    registry = load_json(registry_path)
    if not isinstance(registry, dict):
        return {"registry_found": True, "registry": str(registry_path), "valid": False, "missing": ["valid registry JSON"]}
    checks = {
        "api_references": Path(registry.get("api_references", "")) / "api-index.md" if registry.get("api_references") else None,
        "demo_index": Path(registry.get("demo_index", "")) / "demo_index.json" if registry.get("demo_index") else None,
        "vanilla_indexes": Path(registry.get("vanilla_indexes", "")) if registry.get("vanilla_indexes") else None,
        "remote_public_indexes": Path(registry.get("remote_public_indexes", "")) if registry.get("remote_public_indexes") else None,
    }
    missing = []
    present = []
    for key, path in checks.items():
        ok = False
        if path is not None:
            ok = path.exists()
            if key == "vanilla_indexes":
                ok = path.exists() and any(path.glob("*/index.json"))
            elif key == "remote_public_indexes":
                ok = path.exists() and any(path.rglob("*.json"))
        if ok:
            present.append(key)
        else:
            missing.append(key)
    return {
        "registry_found": True,
        "registry": str(registry_path),
        "valid": True,
        "present": present,
        "missing": missing,
        "root": registry.get("root"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Workspace/project directory to inspect.")
    parser.add_argument("--registry", help="Path to knowledge_registry.json.")
    parser.add_argument("--root", help="Knowledge root containing knowledge_registry.json.")
    parser.add_argument("--json", action="store_true", help="Print JSON only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = Path(args.project).resolve()
    registry_path = find_registry(args.registry, args.root)
    result = {
        "project_detection": detect_project(project),
        "knowledge": detect_knowledge(registry_path),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        pd = result["project_detection"]
        kd = result["knowledge"]
        print(f"Project: {pd['project']}")
        print(f"NetEase Bedrock project: {pd['is_netease_bedrock_project']}")
        print(f"Namespaces: {', '.join(pd['namespaces']) if pd['namespaces'] else '(none detected)'}")
        print(f"Signals: {len(pd['signals'])}")
        for signal in pd["signals"][:20]:
            print(f"- {signal['kind']}: {signal['path']}")
        print(f"Registry found: {kd['registry_found']}")
        if kd.get("registry"):
            print(f"Registry: {kd['registry']}")
        print(f"Knowledge present: {', '.join(kd.get('present', [])) if kd.get('present') else '(none)'}")
        print(f"Knowledge missing: {', '.join(kd.get('missing', [])) if kd.get('missing') else '(none)'}")
    missing = result["knowledge"].get("missing") or []
    return 2 if result["project_detection"]["is_netease_bedrock_project"] and missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
