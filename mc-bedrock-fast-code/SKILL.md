---
name: mc-bedrock-fast-code
description: Edit, generate, query, and diagnose NetEase Minecraft Bedrock/MCStudio ModSDK projects. Use for everyday project code changes, API/event/interface lookup, official identifier lookup, pack generation, linting, or troubleshooting. Also supports explicit first-time or maintenance-only knowledge setup from official docs, demos, installed MinecraftPE_Netease data, and authorized local projects; do not start knowledge preparation during normal code work unless the user asks or a required query reports that its index is missing.
---

# mc-bedrock-fast-code

Route the request before loading detailed instructions. Treat project editing and API lookup as the normal paths. Treat knowledge preparation as an installation or maintenance path.

## Route First

### Project Editing And Diagnosis

Use this path for requests to inspect, create, modify, fix, lint, or explain a ModSDK project.

1. Read [references/project-editing.md](references/project-editing.md).
2. Inspect the project and make the requested change.
3. Load [references/api-search.md](references/api-search.md) only when API validation or identifier lookup is needed.
4. Do not check, rebuild, or update every knowledge index preemptively.
5. Enter knowledge setup only if a required query reports a missing registry/index and the task cannot proceed safely without it.

### API And Official-Name Search

Use this path for questions about interfaces, events, components, materials, textures, models, animations, render controllers, official examples, or supported behavior.

1. Read [references/api-search.md](references/api-search.md).
2. Query existing indexes directly.
3. Do not run project detection or knowledge preparation first.
4. If the requested index is missing, report that specific gap. Read the setup workflow only when the user wants to create/update it or the current task requires it.

### Knowledge Installation And Maintenance

Use this path only for first installation, explicit index creation/update, index repair, version discovery, official-demo indexing, vanilla-data indexing, or authorized custom-project indexing.

1. Read [references/knowledge-setup.md](references/knowledge-setup.md).
2. Ask only for inputs required by the selected source.
3. Run the selected preparation command and verify its registry entry.
4. Keep downloaded/generated knowledge outside the distributed skill folder.

### Mixed Requests

Let project editing own the task. Use API search as a bounded supporting step. Do not invoke knowledge setup unless an actual missing-index condition blocks the requested result.

## Optional Delegation

When the runtime supports subagents, delegate only concrete, non-overlapping work:

- Delegate long-running first-time knowledge preparation to a setup worker while the primary agent continues read-only project inspection.
- Delegate a bounded API search when project editing can continue independently.
- Keep project file ownership with one editing agent; do not let multiple agents modify the same project tree.
- Do not spawn a setup worker during ordinary editing or API questions merely to verify that indexes exist.

Subagents are optional execution helpers, not persistent skill configuration. The three reference workflows remain the source of truth in runtimes without subagents.

## Core Guardrails

- Prefer an authorized custom local project index for project-specific style, then validate API names against official indexes.
- Do not invent namespace IDs, entity/item/block IDs, API names, or unsupported behavior.
- Require project path, namespace, and local resource ID when those values determine valid output files.
- Treat NetEase project JSON as JSONC-compatible.
- Support behavior/resource suffixes such as `_beh`, `_res`, `_behavior`, `_resource`, `beh`, `res`, `behavior`, and `resource`.
- Run Python 2.7.18 environment checks only during setup or explicit runtime/syntax troubleshooting.
- Keep downloaded docs, demo indexes, vanilla indexes, custom indexes, and generated projects outside the release zip.

## Bundled Entry Points

- Project editing: `scripts/detect_project.py`, `scripts/fast_code.py`, `scripts/lint_project.py`, `scripts/check_python_syntax.py`
- Search: `scripts/query_knowledge.py`, `scripts/local_query_index.py`
- Knowledge setup: `scripts/prepare_knowledge.py`, `scripts/update_api_docs.py`, `scripts/index_demos.py`, `scripts/local_index_versions.py`, `scripts/index_custom_project.py`

Repository: `https://github.com/Trryer/mc-bedrock-fast-code`
