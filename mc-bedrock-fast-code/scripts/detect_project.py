#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
"""Detect NetEase Bedrock/MCStudio project features and prepared knowledge indexes."""
import argparse
import json
import re
from pathlib import Path
PROJECT_PATTERNS = [('studio.json', 'studio.json'), ('behavior_pack_dir', '*_behavior'), ('resource_pack_dir', '*_resource'), ('behavior_pack_dir_short', '*_beh'), ('resource_pack_dir_short', '*_res'), ('scripts_dir', '*Scripts'), ('netease_dir', 'netease_*')]
CODE_PATTERNS = {'mod_binding': 'from\\s+mod\\.common\\.mod\\s+import\\s+Mod', 'client_api': 'import\\s+mod\\.client\\.extraClientApi\\s+as\\s+clientApi', 'server_api': 'import\\s+mod\\.server\\.extraServerApi\\s+as\\s+serverApi', 'register_system': 'RegisterSystem\\s*\\(', 'listen_event': 'ListenForEvent\\s*\\(', 'engine_comp_factory': '(GetEngineCompFactory|CreateEngineCompFactory)\\s*\\(', 'client_server_message': '(BroadcastToServer|NotifyToClient)\\s*\\('}

BEHAVIOR_SUFFIXES = ('_behavior', '_beh', 'behavior', 'beh')
RESOURCE_SUFFIXES = ('_resource', '_res', 'resource', 'res')


def suffix_namespace(name, suffixes):
    for suffix in suffixes:
        if name.endswith(suffix) and len(name) > len(suffix):
            base = name[:-len(suffix)]
            return base[:-1] if base.endswith('_') else base
    return None

def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None

def find_registry(explicit, root):
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if root:
        candidates.append(Path(root).expanduser() / 'knowledge_registry.json')
    candidates.append(Path.home() / '.codex' / 'mc-bedrock-fast-code-data' / 'knowledge_registry.json')
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None

def detect_project(project):
    signals = []
    for child in project.iterdir() if project.exists() else []:
        name = child.name
        if name == 'studio.json':
            signals.append({'kind': 'studio.json', 'path': name})
        elif child.is_dir() and suffix_namespace(name, BEHAVIOR_SUFFIXES):
            signals.append({'kind': 'behavior_pack_dir', 'path': name})
        elif child.is_dir() and suffix_namespace(name, RESOURCE_SUFFIXES):
            signals.append({'kind': 'resource_pack_dir', 'path': name})
        elif child.is_dir() and name.endswith('Scripts'):
            signals.append({'kind': 'scripts_dir', 'path': name})
        elif child.is_dir() and name.startswith('netease_'):
            signals.append({'kind': 'netease_dir', 'path': name})
    py_files = list(project.rglob('*.py'))[:500]
    for path in py_files:
        rel = path.relative_to(project)
        if (project / 'SKILL.md').exists() and rel.parts and (rel.parts[0] == 'scripts'):
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        for kind, pattern in CODE_PATTERNS.items():
            if re.search(pattern, text):
                signals.append({'kind': kind, 'path': str(rel)})
    namespaces = set()
    for child in project.iterdir() if project.exists() else []:
        if child.is_dir():
            ns = suffix_namespace(child.name, BEHAVIOR_SUFFIXES)
            if ns:
                namespaces.add(ns)
    namespaces = sorted(namespaces)
    return {'project': str(project), 'is_netease_bedrock_project': bool(signals), 'signals': signals[:80], 'namespaces': namespaces}

def detect_knowledge(registry_path):
    if registry_path is None:
        return {'registry_found': False, 'missing': ['knowledge_registry.json', 'api_references', 'demo_index', 'vanilla_indexes']}
    registry = load_json(registry_path)
    if not isinstance(registry, dict):
        return {'registry_found': True, 'registry': str(registry_path), 'valid': False, 'missing': ['valid registry JSON']}
    checks = {'api_references': Path(registry.get('api_references', '')) / 'api-index.md' if registry.get('api_references') else None, 'demo_index': Path(registry.get('demo_index', '')) / 'demo_index.json' if registry.get('demo_index') else None, 'vanilla_indexes': Path(registry.get('vanilla_indexes', '')) if registry.get('vanilla_indexes') else None, 'remote_public_indexes': Path(registry.get('remote_public_indexes', '')) if registry.get('remote_public_indexes') else None}
    missing = []
    present = []
    for key, path in checks.items():
        ok = False
        if path is not None:
            ok = path.exists()
            if key == 'vanilla_indexes':
                ok = path.exists() and any(path.glob('*/index.json'))
            elif key == 'remote_public_indexes':
                ok = path.exists() and any(path.rglob('*.json'))
        if ok:
            present.append(key)
        else:
            missing.append(key)
    return {'registry_found': True, 'registry': str(registry_path), 'valid': True, 'present': present, 'missing': missing, 'root': registry.get('root')}

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='.', help='Workspace/project directory to inspect.')
    parser.add_argument('--registry', help='Path to knowledge_registry.json.')
    parser.add_argument('--root', help='Knowledge root containing knowledge_registry.json.')
    parser.add_argument('--json', action='store_true', help='Print JSON only.')
    return parser.parse_args()

def main():
    args = parse_args()
    project = Path(args.project).resolve()
    registry_path = find_registry(args.registry, args.root)
    result = {'project_detection': detect_project(project), 'knowledge': detect_knowledge(registry_path)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        pd = result['project_detection']
        kd = result['knowledge']
        print('Project: {}'.format(pd['project']))
        print('NetEase Bedrock project: {}'.format(pd['is_netease_bedrock_project']))
        print('Namespaces: {}'.format(', '.join(pd['namespaces']) if pd['namespaces'] else '(none detected)'))
        print('Signals: {}'.format(len(pd['signals'])))
        for signal in pd['signals'][:20]:
            print('- {}: {}'.format(signal['kind'], signal['path']))
        print('Registry found: {}'.format(kd['registry_found']))
        if kd.get('registry'):
            print('Registry: {}'.format(kd['registry']))
        print('Knowledge present: {}'.format(', '.join(kd.get('present', [])) if kd.get('present') else '(none)'))
        print('Knowledge missing: {}'.format(', '.join(kd.get('missing', [])) if kd.get('missing') else '(none)'))
    missing = result['knowledge'].get('missing') or []
    return 2 if result['project_detection']['is_netease_bedrock_project'] and missing else 0
if __name__ == '__main__':
    raise SystemExit(main())
