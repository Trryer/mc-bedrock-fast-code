#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
"""Query prepared API/demo/vanilla knowledge indexes."""
import argparse
import json
import re
import subprocess
from compat import run_command, try_load_json
import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent

def load_json(path):
    return try_load_json(path)

def find_registry(path, root):
    candidates = []
    if path:
        candidates.append(Path(path).expanduser())
    if root:
        candidates.append(Path(root).expanduser() / 'knowledge_registry.json')
    candidates.append(Path.home() / '.codex' / 'mc-bedrock-fast-code-data' / 'knowledge_registry.json')
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise SystemExit('knowledge_registry.json not found; run prepare_knowledge.py first or pass --registry')

def text_match(text, query):
    return query.lower() in text.lower()

def load_registry(args):
    path = find_registry(args.registry, args.root)
    data = load_json(path)
    if not isinstance(data, dict):
        raise SystemExit('invalid registry: {}'.format(path))
    data['_registry_path'] = str(path)
    return data

def query_demo(registry, query, kind, limit):
    demo_root = registry.get('demo_index')
    if not demo_root:
        return []
    index = load_json(Path(demo_root) / 'demo_index.json')
    if not isinstance(index, dict):
        return []
    results = []
    for rec in index.get('records', []):
        if not isinstance(rec, dict):
            continue
        if kind and kind != 'all' and (kind not in str(rec.get('category', ''))):
            continue
        blob = json.dumps(rec, ensure_ascii=False)
        if text_match(blob, query):
            results.append({'source': 'demo', 'category': rec.get('category'), 'demo': rec.get('demo'), 'path': rec.get('path'), 'identifier': (rec.get('json') or {}).get('identifier') if isinstance(rec.get('json'), dict) else '', 'sample': rec.get('sample', '')[:300]})
        if len(results) >= limit:
            break
    return results

def api_index_files(api_kind):
    if api_kind == 'interface':
        return ['interfaces.md']
    if api_kind == 'event':
        return ['events.md']
    return ['interfaces.md', 'events.md']


def official_api_doc_files(api_kind):
    if api_kind == 'interface':
        return ['official-api-interfaces.md']
    if api_kind == 'event':
        return ['official-api-events.md']
    return ['official-api-docs.md']


def mirror_api_root(api_root, api_kind):
    root = Path(api_root) / 'wiki' / 'docs' / 'mcdocs' / '1-ModAPI'
    if api_kind == 'interface':
        return root / '接口'
    if api_kind == 'event':
        return root / '事件'
    return Path(api_root) / 'wiki' / 'docs' / 'mcdocs'


def query_index_files(api_root, files, query, limit, source):
    results = []
    seen = set()
    for name in files:
        path = Path(api_root) / name
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if not text_match(line, query):
                continue
            key = (str(path), lineno)
            if key in seen:
                continue
            seen.add(key)
            results.append({'source': source, 'path': str(path), 'line': lineno, 'text': line[:500]})
            if len(results) >= limit:
                return results
    return results


def query_api_type(api_root, query, limit, api_kind):
    results = query_index_files(api_root, api_index_files(api_kind), query, limit, 'api_{}'.format(api_kind))
    if not results:
        results = query_index_files(api_root, official_api_doc_files(api_kind), query, limit, 'official_api_doc_{}'.format(api_kind))
    if not results:
        results = query_document_tree(mirror_api_root(api_root, api_kind), query, limit, 'mirror_api_doc_{}'.format(api_kind), '*.md')
    return results


def query_api(registry, query, kind, limit, api_kind='auto', include_non_api_docs=False, api_only=False):
    api_root = registry.get('api_references')
    if not api_root:
        return []
    results = query_api_type(api_root, query, limit, api_kind)
    if not results and api_kind in {'interface', 'event'}:
        alternate_kind = 'event' if api_kind == 'interface' else 'interface'
        results = query_api_type(api_root, query, limit, alternate_kind)
    if results and not include_non_api_docs:
        return results
    if api_only:
        return results
    remaining = limit - len(results)
    if remaining > 0:
        results.extend(query_index_files(api_root, ['official-development-guides.md', 'official-tutorials.md'], query, remaining, 'non_api_index'))
    if not results:
        results.extend(query_document_tree(Path(api_root) / 'official', query, limit, 'official_non_api_doc', '*.html'))
    if not results:
        results.extend(query_document_tree(Path(api_root) / 'wiki' / 'docs', query, limit, 'mirror_non_api_doc', '*.md'))
    return results


def query_document_tree(root, query, limit, source, pattern):
    if not root.exists():
        return []
    results = []
    for path in sorted(root.rglob(pattern)):
        value = path.read_text(encoding='utf-8', errors='replace')
        if not text_match(value, query):
            continue
        position = value.lower().find(query.lower())
        start = max(0, position - 300)
        end = min(len(value), position + len(query) + 900)
        results.append({'source': source, 'path': str(path), 'text': value[start:end]})
        if len(results) >= limit:
            break
    return results


def query_api_updates(registry, query, limit):
    api_root = registry.get('api_references')
    if not api_root:
        return []
    root = Path(api_root) / 'wiki'
    if not root.exists():
        return []
    hints = ('update', '更新', 'deprecated', '废弃', 'changelog', 'change')
    results = []
    for path in sorted(root.rglob('*.md')):
        path_text = path.as_posix().lower()
        text = path.read_text(encoding='utf-8', errors='replace')
        if not any(h.lower() in path_text or h.lower() in text.lower() for h in hints):
            continue
        if text_match(text, query):
            results.append({'source': 'api_update_note', 'path': str(path), 'text': text[:1200], 'recommendation': 'This API may be old or changed; prefer the newer API described by the update note and ask before rewriting project code.'})
        if len(results) >= limit:
            break
    return results


def custom_indexes(registry):
    found = []
    for item in registry.get('custom_project_indexes', []) or []:
        if not isinstance(item, dict):
            continue
        path = item.get('index')
        if path and Path(path).exists():
            found.append((item, Path(path)))
    return found


def query_custom(registry, query, kind, limit):
    results = []
    for meta, index_path in custom_indexes(registry):
        index = load_json(index_path)
        if not isinstance(index, dict):
            continue
        records = index.get('records', []) or []
        def rank(rec):
            return 0 if rec.get('category') == 'lang_zh_cn' or str(rec.get('path', '')).endswith('zh_CN.lang') else 1
        for rec in sorted(records, key=rank):
            if not isinstance(rec, dict):
                continue
            if kind and kind != 'all' and kind not in str(rec.get('category', '')):
                continue
            blob = json.dumps(rec, ensure_ascii=False)
            if text_match(blob, query):
                results.append({'source': 'custom_local', 'index': str(index_path), 'name': meta.get('name') or index.get('name'), 'repo': meta.get('repo') or index.get('repo'), 'path': rec.get('path'), 'category': rec.get('category'), 'text': blob[:1500]})
            if len(results) >= limit:
                return results
    return results

def query_remote(registry, query, kind, limit):
    remote_root = registry.get('remote_public_indexes')
    if not remote_root:
        return []
    root = Path(remote_root)
    if not root.exists():
        return []
    results = []
    for path in sorted(root.rglob('*.json')):
        data = load_json(path)
        blob = json.dumps(data, ensure_ascii=False) if data is not None else path.read_text(encoding='utf-8', errors='replace')
        if kind and kind != 'all' and (kind.lower() not in blob.lower()) and (kind.lower() not in path.as_posix().lower()):
            continue
        if text_match(blob, query):
            results.append({'source': 'remote_public', 'path': str(path), 'text': blob[:1500]})
        if len(results) >= limit:
            break
    return results

def vanilla_indexes(registry):
    root = registry.get('vanilla_indexes')
    if not root:
        return []
    base = Path(root)
    if not base.exists():
        return []
    return sorted((path for path in base.glob('*/index.json') if path.is_file()), key=lambda p: p.parent.name, reverse=True)

def query_vanilla(registry, query, kind, limit):
    results = []
    for index_path in vanilla_indexes(registry):
        cmd = [sys.executable, str(SCRIPT_DIR / 'local_query_index.py'), '--index', str(index_path), query]
        if kind and kind not in {'all', 'demo', 'api', 'vanilla'}:
            cmd.extend(['--kind', kind])
        proc = run_command(cmd)
        text = (proc.stdout or proc.stderr).strip()
        if proc.returncode == 0 and text:
            results.append({'source': 'vanilla', 'version': index_path.parent.name, 'index': str(index_path), 'text': text[:2000]})
        if len(results) >= limit:
            break
    return results

def print_results(results):
    for i, rec in enumerate(results, 1):
        print('## Result {}: {}'.format(i, rec.get('source')))
        for key, value in rec.items():
            if key == 'source' or value in (None, ''):
                continue
            print('{}: {}'.format(key, value))
        print()

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query', help='Identifier, name, path fragment, API, material, texture, controller, etc.')
    parser.add_argument('--kind', default='all', help='Optional kind filter: render_controller, material, texture, entity, item, component, ui, api, vanilla, custom, etc.')
    parser.add_argument('--registry', help='Path to knowledge_registry.json.')
    parser.add_argument('--root', help='Knowledge root containing knowledge_registry.json.')
    parser.add_argument('--limit', type=int, default=8)
    parser.add_argument('--api-kind', choices=['auto', 'interface', 'event'], default='auto', help='Search only interfaces or events when the user states the API type.')
    parser.add_argument('--api-only', action='store_true', help='Do not expand a zero-result API lookup into development guides or tutorials.')
    parser.add_argument('--include-non-api-docs', action='store_true', help='Search development-guide and tutorial indexes even when API results exist.')
    parser.add_argument('--source', choices=['all', 'custom', 'demo', 'api', 'vanilla', 'remote'], default='all')
    return parser.parse_args()

def main():
    args = parse_args()
    registry = load_registry(args)
    results = []
    if args.source in {'all', 'custom'}:
        results.extend(query_custom(registry, args.query, args.kind, args.limit))
    if len(results) < args.limit and args.source in {'all', 'vanilla'}:
        results.extend(query_vanilla(registry, args.query, args.kind, args.limit - len(results)))
    if len(results) < args.limit and args.source in {'all', 'demo'}:
        results.extend(query_demo(registry, args.query, args.kind, args.limit - len(results)))
    if len(results) < args.limit and args.source in {'all', 'api'}:
        results.extend(query_api(registry, args.query, args.kind, args.limit - len(results), args.api_kind, args.include_non_api_docs, args.api_only))
    if len(results) < args.limit and args.source in {'all', 'remote'}:
        results.extend(query_remote(registry, args.query, args.kind, args.limit - len(results)))
    print_results(results)
    if not results:
        print('No matches found. Check that prepare_knowledge.py has built the relevant index.')
        return 1
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
