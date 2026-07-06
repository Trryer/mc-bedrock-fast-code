#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
"""Prepare external knowledge indexes for mc-bedrock-fast-code."""
import argparse
from compat import _merge_dicts
import json
import subprocess
from compat import run_command
import sys
from compat import utcnow_iso
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent

def run(cmd):
    proc = run_command(cmd)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)
    return {'cmd': cmd, 'returncode': proc.returncode, 'stdout': proc.stdout.strip(), 'stderr': proc.stderr.strip()}

def read_registry(path):
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}

def write_registry(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    data['updated_at'] = utcnow_iso()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path.home() / '.codex' / 'mc-bedrock-fast-code-data'), help='External knowledge root.')
    parser.add_argument('--registry', help='Registry JSON path. Defaults to <root>/knowledge_registry.json.')
    parser.add_argument('--api-docs', action='store_true', help='Download/update official ModSDK API docs.')
    parser.add_argument('--remote-indexes', action='store_true', help='Download lightweight public indexes instead of or before local generation.')
    parser.add_argument('--remote-url', help='Zip URL for lightweight public indexes.')
    parser.add_argument('--api-out', help='External API docs output. Defaults to <root>/api_references.')
    parser.add_argument('--demo-source', action='append', default=[], help='Official demo source root. May be repeated.')
    parser.add_argument('--demo-out', help='External demo index output. Defaults to <root>/demo_index.')
    parser.add_argument('--vanilla-index', action='store_true', help='Build vanilla local indexes from MC game data.')
    parser.add_argument('--vanilla-out', help='External vanilla index output. Defaults to <root>/vanilla_indexes.')
    parser.add_argument('--mc-root', action='append', default=[], help='MinecraftPE_Netease root. May be repeated.')
    parser.add_argument('--version-dir', action='append', default=[], help='Specific version folder containing data/. May be repeated.')
    parser.add_argument('--list-versions-only', action='store_true', help='List discovered versions but do not build vanilla indexes.')
    parser.add_argument('--auto-search', action='store_true', help='Allow slow default/exhaustive discovery when no MC root/version is supplied.')
    parser.add_argument('--pretty', action='store_true', help='Pretty-print generated JSON indexes.')
    return parser.parse_args()

def main():
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    registry_path = Path(args.registry).expanduser().resolve() if args.registry else root / 'knowledge_registry.json'
    api_out = Path(args.api_out).expanduser().resolve() if args.api_out else root / 'api_references'
    demo_out = Path(args.demo_out).expanduser().resolve() if args.demo_out else root / 'demo_index'
    vanilla_out = Path(args.vanilla_out).expanduser().resolve() if args.vanilla_out else root / 'vanilla_indexes'
    registry = read_registry(registry_path)
    registry.setdefault('root', str(root))
    registry.setdefault('runs', [])
    runs = registry['runs']
    if args.remote_indexes:
        cmd = [sys.executable, str(SCRIPT_DIR / 'download_remote_indexes.py'), '--root', str(root), '--registry', str(registry_path)]
        if args.remote_url:
            cmd.extend(['--url', args.remote_url])
        result = run(cmd)
        runs.append(_merge_dicts({'kind': 'remote_public_indexes'}, result))
        if result['returncode'] != 0:
            write_registry(registry_path, registry)
            return int(result['returncode'])
        registry = read_registry(registry_path)
        registry.setdefault('runs', runs)
    if args.api_docs:
        result = run([sys.executable, str(SCRIPT_DIR / 'update_api_docs.py'), '--out', str(api_out)])
        runs.append(_merge_dicts({'kind': 'api_docs', 'out': str(api_out)}, result))
        if result['returncode'] != 0:
            write_registry(registry_path, registry)
            return int(result['returncode'])
        registry['api_references'] = str(api_out)
    if args.demo_source:
        cmd = [sys.executable, str(SCRIPT_DIR / 'index_demos.py'), '--out', str(demo_out)]
        for source in args.demo_source:
            cmd.extend(['--source', source])
        if args.pretty:
            cmd.append('--pretty')
        result = run(cmd)
        runs.append(_merge_dicts({'kind': 'demo_index', 'out': str(demo_out), 'sources': args.demo_source}, result))
        if result['returncode'] != 0:
            write_registry(registry_path, registry)
            return int(result['returncode'])
        registry['demo_index'] = str(demo_out)
    if args.vanilla_index or args.list_versions_only:
        if not args.mc_root and (not args.version_dir) and (not args.auto_search):
            print('No MC root/version was supplied. Ask the user first, or pass --auto-search after warning it may take a long time.', file=sys.stderr)
            write_registry(registry_path, registry)
            return 2
        cmd = [sys.executable, str(SCRIPT_DIR / 'local_index_versions.py'), '--out-root', str(vanilla_out)]
        for root_arg in args.mc_root:
            cmd.extend(['--mc-root', root_arg])
        for version_arg in args.version_dir:
            cmd.extend(['--version-dir', version_arg])
        if args.auto_search:
            cmd.append('--exhaustive-search')
        if args.list_versions_only:
            cmd.append('--list-only')
        if args.pretty:
            cmd.append('--pretty')
        result = run(cmd)
        runs.append(_merge_dicts({'kind': 'vanilla_index', 'out': str(vanilla_out), 'list_only': args.list_versions_only}, result))
        if result['returncode'] != 0:
            write_registry(registry_path, registry)
            return int(result['returncode'])
        registry['vanilla_indexes'] = str(vanilla_out)
        registry['mc_roots'] = args.mc_root
        registry['version_dirs'] = args.version_dir
    write_registry(registry_path, registry)
    print('Registry: {}'.format(registry_path))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
