# mc-bedrock-fast-code

[中文说明](README.zh-CN.md)

`mc-bedrock-fast-code` is a Codex skill and script toolkit for NetEase Minecraft Bedrock / MCStudio ModSDK addon work.

It follows a knowledge-first workflow:

1. Detect whether the current workspace looks like a NetEase Bedrock/MCStudio project.
2. Prepare or download reusable knowledge indexes.
3. Query official API/demo/vanilla names before writing code.
4. Generate fixed-routine starter files only after required identifiers are known.
5. Diagnose common reference errors in generated or edited packs.

## What Is Included

- `mc-bedrock-fast-code/`: the Codex skill folder.
- `mc-bedrock-fast-code.zip`: installable skill zip.
- `build_public_index.py`: builds a lightweight public metadata index from local generated indexes.
- `mc-bedrock-fast-code-public-index.zip`: rough fallback index for users who cannot build local indexes.

The public index is intentionally coarse. It contains metadata summaries such as identifiers, kinds, paths, components, and reference names. It does not include official Minecraft/NetEase assets, original demo source scripts, textures, models, sounds, or full game data JSON.

## Install

Copy or install the skill folder/zip into your Codex skills directory:

```powershell
Copy-Item -Recurse .\mc-bedrock-fast-code $env:USERPROFILE\.codex\skills\
```

Or use the zip through your normal Codex skill installation flow.

## Prepare Knowledge Locally

Local indexes are preferred because they match the versions installed on your machine.

```bash
python mc-bedrock-fast-code/scripts/prepare_knowledge.py --root ~/.codex/mc-bedrock-fast-code-data --api-docs --demo-source ./6-1DemoMod --demo-source "<path-to-6-4-resource-demo>" --mc-root "<.../MCStudioDownload/game/MinecraftPE_Netease>" --list-versions-only
```

After choosing representative versions:

```bash
python mc-bedrock-fast-code/scripts/prepare_knowledge.py --root ~/.codex/mc-bedrock-fast-code-data --vanilla-index --mc-root "<.../MinecraftPE_Netease>" --pretty
```

## Download Rough Public Index

For users who do not want to generate local indexes or do not have the original game data installed:

```bash
python mc-bedrock-fast-code/scripts/prepare_knowledge.py --root ~/.codex/mc-bedrock-fast-code-data --remote-indexes --remote-url "https://github.com/Trryer/mc-bedrock-fast-code/releases/latest/download/mc-bedrock-fast-code-public-index.zip"
```

## Download Official Public Demos

NetEase's official ModSDK demo page provides a public 3.8 demo package:

- Page: <https://mc.163.com/dev/mcmanual/mc-dev/mcguide/20-%E7%8E%A9%E6%B3%95%E5%BC%80%E5%8F%91/13-%E6%A8%A1%E7%BB%84SDK%E7%BC%96%E7%A8%8B/60-Demo%E7%A4%BA%E4%BE%8B.html>
- Official download: <https://g79.gdl.netease.com/3.8Demo.zip>

The skill downloader defaults to the official URL:

```bash
python mc-bedrock-fast-code/scripts/download_demo_mirror.py --out ./mc-bedrock-official-public-demos
```

The script also has a `--private-mirror` option for the repository owner's personal backup of the same official public package. That backup is not part of the public repository and may require private GitHub access.

## Generate Code

```bash
python mc-bedrock-fast-code/scripts/fast_code.py create-pack --namespace demo_mod --out ./DemoMod --with-client --with-server --with-ui
python mc-bedrock-fast-code/scripts/fast_code.py add-item --project ./DemoMod --namespace demo_mod --id copper_coin
python mc-bedrock-fast-code/scripts/fast_code.py add-entity --project ./DemoMod --namespace demo_mod --id squirrel --base minecraft:zombie
```

Required identifiers are not guessed. For example, adding an item requires a project path, namespace, and item id because both behavior and resource JSON files must contain `<namespace>:<item_id>`.

## Query And Diagnose

```bash
python mc-bedrock-fast-code/scripts/query_knowledge.py zombie --kind render_controller --source remote
python mc-bedrock-fast-code/scripts/lint_project.py --project ./DemoMod --namespace demo_mod
```

## Sources

This project is designed around public/local references:

- NetEase Minecraft/MCStudio public demo packs supplied by NetEase official documentation/downloads.
- NetEase ModSDK documentation mirrored from public documentation sources such as `EaseCation/netease-modsdk-wiki`.
- Local `MinecraftPE_Netease` game data folders installed on the user's own machine.

See `NOTICE.md` for source and disclaimer details.

## Disclaimer

This project is unofficial. It is not affiliated with, endorsed by, sponsored by, or approved by Mojang, Microsoft, NetEase, or MCStudio.

Minecraft and related names/assets belong to their respective owners. NetEase Minecraft/MCStudio/ModSDK materials belong to their respective owners. The included public index is a metadata-only summary intended for developer lookup and does not redistribute original game assets or official source packages.

## License

Code in this repository is released under the MIT License. See `LICENSE`.
