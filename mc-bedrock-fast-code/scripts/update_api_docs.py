#!/usr/bin/env python3
# 并行下载版：与官方 update_docs.py 同源同输出，仅把串行下载改为线程池并发。
# 输出到本文件夹自己的 references/，不影响其它目录。
from __future__ import annotations

import json
import argparse
import re
import sys
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OWNER = "EaseCation"
REPO = "netease-modsdk-wiki"
BRANCH = "main"
API_BASE = f"https://api.github.com/repos/{OWNER}/{REPO}"
RAW_BASE = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}"
ROOT = Path(__file__).resolve().parent
REFERENCES = Path.cwd() / "mc_bedrock_api_references"
WIKI = REFERENCES / "wiki"

MAX_WORKERS = 16      # 并行下载线程数（可调）
PROGRESS_EVERY = 25   # 每完成多少个文件打印一次进度

DOWNLOAD_EXACT = {
    "api-index.json",
    "docs/mcdocs/readme.md",
    "docs/mcdocs/context7.json",
}
DOWNLOAD_PREFIXES = ("docs/",)


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "build-mc-bedrock-api-idx-fast-skill-updater"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def fetch_json(url: str):
    return json.loads(fetch_bytes(url).decode("utf-8", "replace"))


def repo_tree() -> list:
    url = f"{API_BASE}/git/trees/{BRANCH}?recursive=1"
    data = fetch_json(url)
    if data.get("truncated"):
        print("warning: GitHub tree response is truncated", file=sys.stderr, flush=True)
    return data.get("tree", [])


def should_download(path: str) -> bool:
    if path in DOWNLOAD_EXACT:
        return True
    return path.endswith(".md") and any(path.startswith(p) for p in DOWNLOAD_PREFIXES)


def raw_url(path: str) -> str:
    return f"{RAW_BASE}/{urllib.parse.quote(path, safe='/')}"


def write_binary(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def download_one(path: str):
    data = fetch_bytes(raw_url(path))
    write_binary(WIKI / path, data)
    if path == "api-index.json":
        write_binary(REFERENCES / "api-index.raw.json", data)
    return path


# ---------- 索引生成（与官方脚本一致） ----------
def read_json_lenient(path: Path):
    return json.loads(path.read_bytes().decode("utf-8", "replace"))


def md_escape(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return text.replace("|", "\\|")


def anchor(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^\w一-鿿\- ]+", "", s)
    s = re.sub(r"\s+", "-", s)
    return s or "entry"


def local_doc_link(link: str) -> str:
    if not link:
        return ""
    clean = link.split("#", 1)[0].lstrip("/")
    if not clean:
        return ""
    return (Path("wiki") / clean).as_posix()


def summarize_params(values) -> str:
    if not values:
        return ""
    parts = []
    for item in values:
        if isinstance(item, dict):
            name = item.get("name") or item.get("param") or item.get("key") or ""
            typ = item.get("type") or item.get("valueType") or ""
            desc = item.get("description") or item.get("desc") or item.get("remark") or ""
            combined = ": ".join(x for x in [name, typ] if x)
            if desc:
                combined = f"{combined} {desc}".strip()
            if combined:
                parts.append(combined)
        elif item:
            parts.append(str(item))
    return "; ".join(parts[:6])


def row_for(item: dict) -> str:
    name = md_escape(item.get("name"))
    method = md_escape(item.get("method"))
    item_type = md_escape(item.get("type"))
    side = md_escape(item.get("side"))
    description = md_escape(item.get("description"))
    params = md_escape(summarize_params(item.get("params")))
    returns = md_escape(summarize_params(item.get("return")))
    doc = local_doc_link(item.get("link") or "")
    doc_cell = f"[{md_escape(item.get('link'))}]({doc})" if doc else md_escape(item.get("link"))
    display = method or name
    entry_anchor = anchor(display)
    return f"| <a id=\"{entry_anchor}\"></a>{item_type} | {name} | {method} | {side} | {description} | {params} | {returns} | {doc_cell} |"


def write_index(path: Path, title: str, items: list, intro: str) -> None:
    lines = [
        f"# {title}", "", intro, "",
        f"Total entries: {len(items)}", "",
        "| Type | Name | Method | Side | Description | Params | Return | Source |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines.extend(row_for(item) for item in items)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_search_guide() -> None:
    (REFERENCES / "search-guide.md").write_text(
        "# build-mc-bedrock-api-idx-fast Search Guide (parallel)\n\n"
        "优先查 api-index.md / interfaces.md / events.md，再查 wiki/docs/**/*.md。\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download NetEase ModSDK docs into an external references directory.")
    parser.add_argument("--out", default=None, help="External output directory. Defaults to ./mc_bedrock_api_references.")
    return parser.parse_args()


def main() -> int:
    global REFERENCES, WIKI
    args = parse_args()
    if args.out:
        REFERENCES = Path(args.out).resolve()
        WIKI = REFERENCES / "wiki"
    REFERENCES.mkdir(parents=True, exist_ok=True)
    print("fetching repo tree ...", flush=True)
    tree = repo_tree()
    paths = sorted(item["path"] for item in tree
                   if item.get("type") == "blob" and should_download(item.get("path", "")))
    total = len(paths)
    if not total:
        raise RuntimeError("no matching files found in GitHub tree")
    print(f"{total} files to download with {MAX_WORKERS} workers", flush=True)

    done = 0
    errors = []
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(download_one, p): p for p in paths}
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                fut.result()
            except Exception as e:  # noqa: BLE001
                errors.append((p, str(e)))
            with lock:
                done += 1
                if done % PROGRESS_EVERY == 0 or done == total:
                    print(f"progress {done}/{total}", flush=True)

    # 失败的串行重试一次
    if errors:
        print(f"{len(errors)} files failed, retrying serially ...", flush=True)
        for p, _ in errors:
            try:
                download_one(p)
            except Exception as e:  # noqa: BLE001
                print(f"  failed again: {p} -> {e}", file=sys.stderr, flush=True)

    api_data = read_json_lenient(REFERENCES / "api-index.raw.json")
    if not isinstance(api_data, list):
        raise RuntimeError("api-index.json did not contain a list")
    events = [i for i in api_data if i.get("type") == "event"]
    interfaces = [i for i in api_data if i.get("type") != "event"]
    write_index(REFERENCES / "api-index.md", "NetEase ModSDK API Index", api_data,
                "Generated from api-index.json (parallel downloader).")
    write_index(REFERENCES / "events.md", "NetEase ModSDK Events", events,
                "Event-only subset.")
    write_index(REFERENCES / "interfaces.md", "NetEase ModSDK Interfaces", interfaces,
                "API/interface subset.")
    write_search_guide()

    print(f"DONE: downloaded {total} files, indexed {len(api_data)} entries "
          f"({len(interfaces)} interfaces, {len(events)} events)", flush=True)
    print(f"Output: {REFERENCES}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
