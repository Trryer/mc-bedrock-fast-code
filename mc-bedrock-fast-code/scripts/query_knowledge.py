#!/usr/bin/env python3
"""Query prepared API/demo/vanilla knowledge indexes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        try:
            return json.loads(path.read_bytes().decode("utf-8", "replace"))
        except Exception:
            return None


def find_registry(path: str | None, root: str | None) -> Path:
    candidates = []
    if path:
        candidates.append(Path(path).expanduser())
    if root:
        candidates.append(Path(root).expanduser() / "knowledge_registry.json")
    candidates.append(Path.home() / ".codex" / "mc-bedrock-fast-code-data" / "knowledge_registry.json")
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise SystemExit("knowledge_registry.json not found; run prepare_knowledge.py first or pass --registry")


def text_match(text: str, query: str) -> bool:
    return query.lower() in text.lower()


def load_registry(args: argparse.Namespace) -> dict:
    path = find_registry(args.registry, args.root)
    data = load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"invalid registry: {path}")
    data["_registry_path"] = str(path)
    return data


def query_demo(registry: dict, query: str, kind: str | None, limit: int) -> list[dict]:
    demo_root = registry.get("demo_index")
    if not demo_root:
        return []
    index = load_json(Path(demo_root) / "demo_index.json")
    if not isinstance(index, dict):
        return []
    results = []
    for rec in index.get("records", []):
        if not isinstance(rec, dict):
            continue
        if kind and kind != "all" and kind not in str(rec.get("category", "")):
            continue
        blob = json.dumps(rec, ensure_ascii=False)
        if text_match(blob, query):
            results.append({
                "source": "demo",
                "category": rec.get("category"),
                "demo": rec.get("demo"),
                "path": rec.get("path"),
                "identifier": (rec.get("json") or {}).get("identifier") if isinstance(rec.get("json"), dict) else "",
                "sample": rec.get("sample", "")[:300],
            })
        if len(results) >= limit:
            break
    return results


def query_api(registry: dict, query: str, kind: str | None, limit: int) -> list[dict]:
    api_root = registry.get("api_references")
    if not api_root:
        return []
    files = []
    if kind in (None, "all", "api"):
        files.extend(["api-index.md", "interfaces.md", "events.md"])
    else:
        files.extend(["api-index.md", "interfaces.md", "events.md"])
    results = []
    seen = set()
    for name in files:
        path = Path(api_root) / name
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if text_match(line, query):
                key = (str(path), lineno)
                if key in seen:
                    continue
                seen.add(key)
                results.append({"source": "api", "path": str(path), "line": lineno, "text": line[:500]})
                if len(results) >= limit:
                    return results
    return results


def query_remote(registry: dict, query: str, kind: str | None, limit: int) -> list[dict]:
    remote_root = registry.get("remote_public_indexes")
    if not remote_root:
        return []
    root = Path(remote_root)
    if not root.exists():
        return []
    results = []
    for path in sorted(root.rglob("*.json")):
        data = load_json(path)
        blob = json.dumps(data, ensure_ascii=False) if data is not None else path.read_text(encoding="utf-8", errors="replace")
        if kind and kind != "all" and kind.lower() not in blob.lower() and kind.lower() not in path.as_posix().lower():
            continue
        if text_match(blob, query):
            results.append({
                "source": "remote_public",
                "path": str(path),
                "text": blob[:1500],
            })
        if len(results) >= limit:
            break
    return results


def vanilla_indexes(registry: dict) -> list[Path]:
    root = registry.get("vanilla_indexes")
    if not root:
        return []
    base = Path(root)
    if not base.exists():
        return []
    return sorted((path for path in base.glob("*/index.json") if path.is_file()), key=lambda p: p.parent.name, reverse=True)


def query_vanilla(registry: dict, query: str, kind: str | None, limit: int) -> list[dict]:
    results = []
    for index_path in vanilla_indexes(registry):
        cmd = [sys.executable, str(SCRIPT_DIR / "local_query_index.py"), "--index", str(index_path), query]
        if kind and kind not in {"all", "demo", "api", "vanilla"}:
            cmd.extend(["--kind", kind])
        proc = subprocess.run(cmd, text=True, capture_output=True)
        text = (proc.stdout or proc.stderr).strip()
        if proc.returncode == 0 and text:
            results.append({
                "source": "vanilla",
                "version": index_path.parent.name,
                "index": str(index_path),
                "text": text[:2000],
            })
        if len(results) >= limit:
            break
    return results


def print_results(results: list[dict]) -> None:
    for i, rec in enumerate(results, 1):
        print(f"## Result {i}: {rec.get('source')}")
        for key, value in rec.items():
            if key == "source" or value in (None, ""):
                continue
            print(f"{key}: {value}")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Identifier, name, path fragment, API, material, texture, controller, etc.")
    parser.add_argument("--kind", default="all", help="Optional kind filter: render_controller, material, texture, entity, item, component, ui, api, vanilla, etc.")
    parser.add_argument("--registry", help="Path to knowledge_registry.json.")
    parser.add_argument("--root", help="Knowledge root containing knowledge_registry.json.")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--source", choices=["all", "demo", "api", "vanilla", "remote"], default="all")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = load_registry(args)
    results: list[dict] = []
    if args.source in {"all", "vanilla"}:
        results.extend(query_vanilla(registry, args.query, args.kind, args.limit))
    if len(results) < args.limit and args.source in {"all", "demo"}:
        results.extend(query_demo(registry, args.query, args.kind, args.limit - len(results)))
    if len(results) < args.limit and args.source in {"all", "api"}:
        results.extend(query_api(registry, args.query, args.kind, args.limit - len(results)))
    if len(results) < args.limit and args.source in {"all", "remote"}:
        results.extend(query_remote(registry, args.query, args.kind, args.limit - len(results)))
    print_results(results)
    if not results:
        print("No matches found. Check that prepare_knowledge.py has built the relevant index.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
