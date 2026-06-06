---
name: mc-bedrock-fast-code
description: Generate, query, and diagnose NetEase Minecraft Bedrock/MCStudio ModSDK starter packs and common addon files. Use when Codex needs to detect whether the current workspace is a NetEase Bedrock project, prepare or verify local knowledge indexes, create a clean namespaced empty mod, UI starter, client/server script scaffold, custom entity/item/block/resource configuration, query official vanilla/demo/API names such as render controllers, materials, textures, components, or animation controllers, or inspect likely project errors using local indexes.
---

# mc-bedrock-fast-code

Use this skill for fast NetEase Bedrock/MCStudio ModSDK project setup, repetitive addon file generation, quick official-name lookup, and project diagnosis. The intended flow is knowledge-first generation: prepare local API/demo/vanilla indexes, then query or generate code from those indexed rules plus the user's namespace and identifiers. Keep the skill package lean: scripts belong in the skill, but downloaded API docs, local vanilla indexes, generated demo indexes, and generated projects must live outside the final distribution zip.

## Workflow

1. On skill use, first inspect the current workspace with `scripts/detect_project.py --project <cwd>` unless the user is only asking about the skill itself. If it looks like a NetEase Bedrock/MCStudio project, also check whether a usable `knowledge_registry.json`, API docs, demo index, and vanilla local index exist.
2. If the workspace is a NetEase Bedrock project but required indexes are missing, enter the knowledge-preparation flow before writing non-trivial code:
   - Ask for MCStudio/MinecraftPE_Netease install root or version folder before slow auto-search.
   - Ask which major game versions to index; recommend one representative per major version.
   - Ask where to store the reusable knowledge root; default to `~/.codex/mc-bedrock-fast-code-data`.
   - If the user does not want local generation or does not have game data installed, offer `--remote-indexes` to download a lightweight public index package as a rough fallback.
3. Prepare or discover local knowledge before generating non-trivial code:
   - Official ModSDK API docs and API index.
   - Local vanilla Bedrock/NetEase indexes from installed game `data` folders.
   - Official demo indexes from public demo roots such as `6-1DemoMod` and the `6-4` resource-making demo directory.
4. Use `scripts/prepare_knowledge.py` to build/update those external indexes and write a `knowledge_registry.json` that later generation can reuse across projects.
5. When implementing features, prefer official API calls, documented ModSDK events, vanilla components, and indexed official examples. Avoid inventing unsupported APIs when the knowledge base is absent or has no matching result; state the gap and ask to prepare/update indexes or search docs.
6. If a requested code pattern or troubleshooting question depends on a fixed official routine, consult the demo index and API docs first. If it depends on vanilla behavior, official render controllers, materials, textures, components, animation controllers, or entity definitions, consult the vanilla local index first.
7. Before generating, verify the required inputs for the requested artifact. If any required input is missing, ask the user for it before writing files. Do not invent namespace ids, item ids, entity ids, or output project paths when they are required for valid file contents.
8. Generate files with `scripts/fast_code.py`. Start with `create-pack`, then use `add-ui`, `add-entity`, `add-item`, or `add-block` for focused additions.
9. When generating from a base vanilla entity, query the local vanilla index and copy only useful shape/components; keep new namespace identifiers clean.
10. Do not place generated demo indexes, downloaded wiki files, local vanilla indexes, or created packs inside the final skill zip.

## Query And Diagnose

Use `scripts/query_knowledge.py` when the user asks what an official identifier/name/path should be, such as "how does zombie render controller look", "what is the official material name", "which texture key does this entity use", or "find examples of UI button definitions".

```bash
python scripts/query_knowledge.py --registry ~/.codex/mc-bedrock-fast-code-data/knowledge_registry.json zombie --kind render_controller
python scripts/query_knowledge.py --registry ~/.codex/mc-bedrock-fast-code-data/knowledge_registry.json entity_alphatest --kind material
python scripts/query_knowledge.py --registry ~/.codex/mc-bedrock-fast-code-data/knowledge_registry.json UIDemo --kind ui
python scripts/query_knowledge.py --registry ~/.codex/mc-bedrock-fast-code-data/knowledge_registry.json zombie --kind render_controller --source remote
```

Use `scripts/lint_project.py` when the user asks why a pack is broken or when generated/edited files need a sanity pass:

```bash
python scripts/lint_project.py --project ./DemoMod --namespace demo_mod
```

The linter checks common fixed-routine mistakes: missing behavior/resource pack folders, malformed JSON, missing `_ui_defs.json` entries, client entities that reference missing render controllers/materials/textures/geometry/animation controllers, and behavior entities without matching client entity files.

## Project Detection

Quick detection and knowledge status:

```bash
python scripts/detect_project.py --project <cwd>
python scripts/detect_project.py --project <cwd> --registry ~/.codex/mc-bedrock-fast-code-data/knowledge_registry.json
```

Treat a workspace as a NetEase ModSDK or MCStudio AddOn project when any of these signs appear:

- `studio.json` exists.
- Directories match `*_beh`, `*_res`, `*Scripts`, or `netease_*`.
- Python imports `from mod.common.mod import Mod`, `mod.client.extraClientApi`, or `mod.server.extraServerApi`.
- Code calls `RegisterSystem`, `ListenForEvent`, `GetEngineCompFactory`, `CreateEngineCompFactory`, `BroadcastToServer`, or `NotifyToClient`.

When the project context is unclear, use `rg` or file globs to confirm these signs.

## Fast Generation

Prepare reusable local knowledge first:

```bash
python scripts/prepare_knowledge.py --root ~/.codex/mc-bedrock-fast-code-data --api-docs --demo-source ./6-1DemoMod --demo-source "<path-to-6-4-resource-demo>" --mc-root <.../MCStudioDownload/game/MinecraftPE_Netease> --list-versions-only
```

If the user cannot or does not want to build local indexes, download the rough public fallback index package:

```bash
python scripts/prepare_knowledge.py --root ~/.codex/mc-bedrock-fast-code-data --remote-indexes --remote-url <public-index-zip-url>
```

Prefer full local indexes when available. Remote public indexes are intentionally coarse: use them for lookup and rough guidance, not as the final authority for version-specific behavior.

After the user chooses representative versions, build vanilla indexes:

```bash
python scripts/prepare_knowledge.py --root ~/.codex/mc-bedrock-fast-code-data --vanilla-index --mc-root <.../MinecraftPE_Netease> --pretty
```

Create a clean script-only/client-server starter:

```bash
python scripts/fast_code.py create-pack --namespace demo_mod --out ./DemoMod --with-client --with-server
```

Create a UI starter pack:

```bash
python scripts/fast_code.py create-pack --namespace demo_ui --out ./DemoUi --with-client --with-server --with-ui
python scripts/fast_code.py add-ui --project ./DemoUi --namespace demo_ui --screen main
```

Add common content:

```bash
python scripts/fast_code.py add-entity --project ./DemoMod --namespace demo_mod --id squirrel --display-name Squirrel
python scripts/fast_code.py add-item --project ./DemoMod --namespace demo_mod --id copper_coin --display-name Copper Coin
python scripts/fast_code.py add-block --project ./DemoMod --namespace demo_mod --id bright_block --display-name Bright Block
python scripts/fast_code.py add-render-controller --project ./DemoMod --namespace demo_mod --id squirrel
python scripts/fast_code.py add-animation-controller --project ./DemoMod --namespace demo_mod --id squirrel --side resource
```

The generator writes variables into `<namespace>Scripts/modConfig.py` and keeps identifiers namespaced so later one-click generation can reuse the same config.

## Required Inputs

Treat these as hard requirements. If the user request omits any required field, ask for the missing value first and explain that the files cannot be valid without it.

| Task | Required inputs | Why required |
|---|---|---|
| Create a new pack | `namespace`, output path/project name | Pack folders, manifests, script package, and `modConfig.py` all derive from the namespace. |
| Add item | project path, `namespace`, `item_id` | Must create both `netease_items_beh/<item_id>.json` and `netease_items_res/<item_id>.json`; both need identifier `<namespace>:<item_id>`. |
| Add block | project path, `namespace`, `block_id` | Behavior block JSON, resource `blocks.json`, texture atlas keys, and lang keys require `<namespace>:<block_id>`. |
| Add entity | project path, `namespace`, `entity_id` | Behavior entity and client entity files both require `<namespace>:<entity_id>`; optional vanilla base can be queried after these are known. |
| Add UI | project path, `namespace`, screen id | UI file and `_ui_defs.json` entry need a stable screen id and resource pack path. |
| Add animation/controller/render/material/particle | project path, `namespace`, resource id | File names and keys such as `controller.render.<namespace>.<id>` or `<namespace>:<particle_id>` require both parts. |

Identifier rules:

- `namespace` and local ids should use lowercase letters, digits, and underscores.
- Full identifiers must be `<namespace>:<local_id>`, for example `demo_mod:copper_coin`.
- If the user provides a full identifier, split it into namespace and local id before calling scripts.
- Display names, stack size, spawn egg colors, base vanilla entity, and UI layout details are optional refinements; do not block basic generation on them.

## Demo Index

Build an external index from official demo packs:

```bash
python scripts/index_demos.py --source ./6-1DemoMod --source "<path-to-6-4-resource-demo>" --out ./mc_bedrock_demo_index
```

The index summarizes categories, pack pairs, scripts, manifests, UI files, entity/item/block/resource files, models, animation controllers, render controllers, particles, sounds, shaders/materials, textures, and source assets. Use it to choose the closest official example before generating specialized starters.

## Official Public Demo Downloads

NetEase's public ModSDK demo page:

- Official page: `https://mc.163.com/dev/mcmanual/mc-dev/mcguide/20-%E7%8E%A9%E6%B3%95%E5%BC%80%E5%8F%91/13-%E6%A8%A1%E7%BB%84SDK%E7%BC%96%E7%A8%8B/60-Demo%E7%A4%BA%E4%BE%8B.html`
- Official public `3.8Demo.zip`: `https://g79.gdl.netease.com/3.8Demo.zip`

The indexed API docs may also contain older public demo links, including:

- Official public `3.6Demo.zip`: `https://g79.gdl.netease.com/3.6Demo.zip`

The documentation also says SDK demos are available from the MC Studio content library starting with version 3.5: Content Library -> Work Templates -> the `SDK demo/examples` tag.

Download the official 3.8 public demo package:

```bash
python scripts/download_demo_mirror.py --out ./mc-bedrock-official-public-demos
```

For the repository owner's personal convenience, the downloader can also use a private GitHub backup mirror of the locally available 3.8 official public demo folders. Treat that mirror as a backup of official public demo materials, not as content owned by this project; it may require private GitHub access:

```bash
python scripts/download_demo_mirror.py --private-mirror --out ./mc-bedrock-official-public-demos
```

Use either source only if you are allowed to access and use the official public demo materials under their original terms.

## Integrated Indexes

This skill can subsume the old split workflow:

- Use `scripts/update_api_docs.py` to download/update ModSDK docs into an external references directory.
- Use `scripts/local_index_versions.py`, `scripts/local_build_index.py`, and `scripts/local_query_index.py` for vanilla game data indexes. Ask the user for install root, versions, and output root first; prefer one representative index per major version unless the user requests all versions.
- Store generated API docs, vanilla indexes, and demo indexes in stable external roots so multiple projects can reuse them.
