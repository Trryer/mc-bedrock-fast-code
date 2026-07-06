#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import argparse
import re
import sys
from compat import quote
from compat import Request, urlopen
from pathlib import Path
OWNER = 'EaseCation'
REPO = 'netease-modsdk-wiki'
BRANCH = 'main'
API_BASE = 'https://api.github.com/repos/{}/{}'.format(OWNER, REPO)
RAW_BASE = 'https://raw.githubusercontent.com/{}/{}/{}'.format(OWNER, REPO, BRANCH)
ROOT = Path(__file__).resolve().parent
REFERENCES = Path.cwd() / 'mc_bedrock_api_references'
WIKI = REFERENCES / 'wiki'
MAX_WORKERS = 16
PROGRESS_EVERY = 25
DOWNLOAD_EXACT = {'api-index.json', 'docs/mcdocs/readme.md', 'docs/mcdocs/context7.json'}
DOWNLOAD_PREFIXES = ('docs/',)

def fetch_bytes(url):
    req = Request(url, headers={'User-Agent': 'build-mc-bedrock-api-idx-fast-skill-updater'})
    response = urlopen(req, timeout=60)
    try:
        return response.read()
    finally:
        response.close()

def fetch_json(url):
    return json.loads(fetch_bytes(url).decode('utf-8', 'replace'))

def repo_tree():
    url = '{}/git/trees/{}?recursive=1'.format(API_BASE, BRANCH)
    data = fetch_json(url)
    if data.get('truncated'):
        print('warning: GitHub tree response is truncated', file=sys.stderr)
    return data.get('tree', [])

def should_download(path):
    if path in DOWNLOAD_EXACT:
        return True
    return path.endswith('.md') and any((path.startswith(p) for p in DOWNLOAD_PREFIXES))

def raw_url(path):
    return '{}/{}'.format(RAW_BASE, quote(path, safe='/'))

def write_binary(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

def download_one(path):
    data = fetch_bytes(raw_url(path))
    write_binary(WIKI / path, data)
    if path == 'api-index.json':
        write_binary(REFERENCES / 'api-index.raw.json', data)
    return path

def read_json_lenient(path):
    return json.loads(path.read_bytes().decode('utf-8', 'replace'))

def md_escape(value):
    if value is None:
        return ''
    text = str(value).replace('\r', ' ').replace('\n', ' ').strip()
    return text.replace('|', '\\|')

def anchor(text):
    s = text.strip().lower()
    s = re.sub('[^\\w一-鿿\\- ]+', '', s)
    s = re.sub('\\s+', '-', s)
    return s or 'entry'

def local_doc_link(link):
    if not link:
        return ''
    clean = link.split('#', 1)[0].lstrip('/')
    if not clean:
        return ''
    return (Path('wiki') / clean).as_posix()

def summarize_params(values):
    if not values:
        return ''
    parts = []
    for item in values:
        if isinstance(item, dict):
            name = item.get('name') or item.get('param') or item.get('key') or ''
            typ = item.get('type') or item.get('valueType') or ''
            desc = item.get('description') or item.get('desc') or item.get('remark') or ''
            combined = ': '.join((x for x in [name, typ] if x))
            if desc:
                combined = '{} {}'.format(combined, desc).strip()
            if combined:
                parts.append(combined)
        elif item:
            parts.append(str(item))
    return '; '.join(parts[:6])

def row_for(item):
    name = md_escape(item.get('name'))
    method = md_escape(item.get('method'))
    item_type = md_escape(item.get('type'))
    side = md_escape(item.get('side'))
    description = md_escape(item.get('description'))
    params = md_escape(summarize_params(item.get('params')))
    returns = md_escape(summarize_params(item.get('return')))
    doc = local_doc_link(item.get('link') or '')
    doc_cell = '[{}]({})'.format(md_escape(item.get('link')), doc) if doc else md_escape(item.get('link'))
    display = method or name
    entry_anchor = anchor(display)
    return '| <a id="{}"></a>{} | {} | {} | {} | {} | {} | {} | {} |'.format(entry_anchor, item_type, name, method, side, description, params, returns, doc_cell)

def write_index(path, title, items, intro):
    lines = ['# {}'.format(title), '', intro, '', 'Total entries: {}'.format(len(items)), '', '| Type | Name | Method | Side | Description | Params | Return | Source |', '|---|---|---|---|---|---|---|---|']
    lines.extend((row_for(item) for item in items))
    lines.append('')
    path.write_text('\n'.join(lines), encoding='utf-8')

def write_search_guide():
    (REFERENCES / 'search-guide.md').write_text('# build-mc-bedrock-api-idx-fast Search Guide (parallel)\n\n优先查 api-index.md / interfaces.md / events.md，再查 wiki/docs/**/*.md。\n', encoding='utf-8')

def parse_args():
    parser = argparse.ArgumentParser(description='Download NetEase ModSDK docs into an external references directory.')
    parser.add_argument('--out', default=None, help='External output directory. Defaults to ./mc_bedrock_api_references.')
    return parser.parse_args()

def main():
    global REFERENCES, WIKI
    args = parse_args()
    if args.out:
        REFERENCES = Path(args.out).resolve()
        WIKI = REFERENCES / 'wiki'
    REFERENCES.mkdir(parents=True, exist_ok=True)
    print('fetching repo tree ...')
    tree = repo_tree()
    paths = sorted((item['path'] for item in tree if item.get('type') == 'blob' and should_download(item.get('path', ''))))
    total = len(paths)
    if not total:
        raise RuntimeError('no matching files found in GitHub tree')
    print('{} files to download with {} workers'.format(total, MAX_WORKERS))
    done = 0
    errors = []
    for p in paths:
        try:
            download_one(p)
        except Exception as e:
            errors.append((p, str(e)))
        done += 1
        if done % PROGRESS_EVERY == 0 or done == total:
            print('progress {}/{}'.format(done, total))
    if errors:
        print('{} files failed, retrying serially ...'.format(len(errors)))
        for p, _ in errors:
            try:
                download_one(p)
            except Exception as e:
                print('  failed again: {} -> {}'.format(p, e), file=sys.stderr)
    api_data = read_json_lenient(REFERENCES / 'api-index.raw.json')
    if not isinstance(api_data, list):
        raise RuntimeError('api-index.json did not contain a list')
    events = [i for i in api_data if i.get('type') == 'event']
    interfaces = [i for i in api_data if i.get('type') != 'event']
    write_index(REFERENCES / 'api-index.md', 'NetEase ModSDK API Index', api_data, 'Generated from api-index.json (parallel downloader).')
    write_index(REFERENCES / 'events.md', 'NetEase ModSDK Events', events, 'Event-only subset.')
    write_index(REFERENCES / 'interfaces.md', 'NetEase ModSDK Interfaces', interfaces, 'API/interface subset.')
    write_search_guide()
    print('DONE: downloaded {} files, indexed {} entries ({} interfaces, {} events)'.format(total, len(api_data), len(interfaces), len(events)))
    print('Output: {}'.format(REFERENCES))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
