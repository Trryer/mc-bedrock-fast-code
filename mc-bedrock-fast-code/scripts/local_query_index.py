#!/usr/bin/env python3
"""Query a Minecraft Bedrock vanilla index.json file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_index(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def record_text(record: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in ("id", "kind", "pack_type", "pack_name", "relative_path", "identifier", "name"):
        value = record.get(key)
        if value is not None:
            chunks.append(str(value))
    chunks.extend(record.get("components", []))
    chunks.extend(record.get("tags", []))
    for values in record.get("references", {}).values():
        chunks.extend(values)
    return "\n".join(chunks).lower()


def search(index: dict[str, Any], term: str, kind: str | None, limit: int) -> dict[str, Any]:
    needle = term.lower()
    needles = {needle}
    if ":" in needle:
        needles.add(needle.split(":", 1)[1])
    records = index.get("records", [])
    by_id = {record["id"]: record for record in records}
    matched_ids: set[str] = set()
    reverse_hits: dict[str, dict[str, list[str]]] = {}
    reverse_section_filter = None
    if kind == "component":
        reverse_section_filter = "by_component"
        kind = None
    elif kind == "reference":
        reverse_section_filter = "by_reference"
        kind = None
    elif kind == "identifier":
        reverse_section_filter = "by_identifier"
        kind = None

    for section, mapping in index.get("reverse_index", {}).items():
        if reverse_section_filter and section != reverse_section_filter:
            continue
        for key, ids in mapping.items():
            haystack = key.lower()
            if any(item in haystack for item in needles):
                if section not in reverse_hits:
                    reverse_hits[section] = {}
                reverse_hits[section][key] = ids[:limit]
                matched_ids.update(ids)

    for record in records:
        if kind and record.get("kind") != kind:
            continue
        haystack = record_text(record)
        if any(item in haystack for item in needles):
            matched_ids.add(record["id"])

    matched = [by_id[rid] for rid in matched_ids if rid in by_id and (not kind or by_id[rid].get("kind") == kind)]
    matched.sort(key=lambda r: (r.get("pack_name", ""), r.get("kind", ""), r.get("identifier") or r.get("name") or "", r.get("relative_path", "")))
    return {"term": term, "kind": kind, "records": matched[:limit], "total_records": len(matched), "reverse_hits": reverse_hits}


def summarize(result: dict[str, Any]) -> str:
    lines = [f"Query: {result['term']}"]
    if result.get("kind"):
        lines.append(f"Kind filter: {result['kind']}")
    lines.append(f"Matched records: {result['total_records']}")
    if result["reverse_hits"]:
        lines.append("")
        lines.append("Reverse hits:")
        for section, mapping in result["reverse_hits"].items():
            for key, ids in list(mapping.items())[:20]:
                lines.append(f"- {section}: {key} ({len(ids)} shown)")
    lines.append("")
    lines.append("Records:")
    for record in result["records"]:
        label = record.get("identifier") or record.get("name") or record["id"]
        refs = sum(len(v) for v in record.get("references", {}).values())
        lines.append(f"- {label} [{record['kind']}] {record['pack_type']}/{record['pack_name']} {record['relative_path']}")
        if record.get("components"):
            lines.append(f"  components: {', '.join(record['components'][:10])}")
        if refs:
            sample_refs = []
            for ref_kind, values in record.get("references", {}).items():
                for value in values[:3]:
                    sample_refs.append(f"{ref_kind}:{value}")
            lines.append(f"  refs: {', '.join(sample_refs[:10])}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("term", help="Search term, identifier, component, reference, or path fragment.")
    parser.add_argument("--index", required=True, help="Path to index.json.")
    parser.add_argument("--kind", help="Optional exact record kind filter, such as behavior_entity or component.")
    parser.add_argument("--limit", type=int, default=25, help="Maximum records to show.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = search(load_index(Path(args.index)), args.term, args.kind, args.limit)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(summarize(result))


if __name__ == "__main__":
    main()
