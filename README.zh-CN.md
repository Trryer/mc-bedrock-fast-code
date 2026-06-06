# mc-bedrock-fast-code

[English README](README.md)

`mc-bedrock-fast-code` 是一个面向网易《我的世界》基岩版 / MCStudio ModSDK AddOn 开发的 Codex skill 和脚本工具集。

它的目标不是盲目生成代码，而是先建立或下载知识库，再基于官方 API、官方 demo、原版资源索引和用户提供的命名空间/ID，生成更稳定的固定套路代码。

## 核心流程

1. 检测当前工作目录是否像网易基岩版 / MCStudio 项目。
2. 准备或下载可复用知识库。
3. 写代码前优先查询官方 API、demo 示例、原版组件/渲染器/材质/动画控制器等。
4. 必填信息缺失时先询问用户，例如命名空间、item id、entity id、项目路径。
5. 生成空白包、UI、客户端/服务端脚本、生物、物品、方块、动画、控制器、材质、粒子等固定结构。
6. 对项目做基础检查，发现常见引用错误。

## 仓库内容

- `mc-bedrock-fast-code/`：Codex skill 源码目录。
- `mc-bedrock-fast-code.zip`：可安装的 skill 压缩包。
- `build_public_index.py`：从本地生成的索引中构建公开粗略索引。
- `mc-bedrock-fast-code-public-index.zip`：给不想本地生成索引、或没有安装原版包库的用户使用的粗略远程索引。

公开索引只包含元数据摘要，例如类型、标识符、路径、组件名、引用名等。它不包含官方 Minecraft/网易资源文件、官方 demo 原始脚本、贴图、模型、声音或完整游戏数据 JSON。

## 安装

把 skill 目录复制到 Codex skills 目录：

```powershell
Copy-Item -Recurse .\mc-bedrock-fast-code $env:USERPROFILE\.codex\skills\
```

也可以使用 `mc-bedrock-fast-code.zip` 通过你的 Codex skill 安装流程安装。

## 本地准备知识库

推荐优先使用本地索引，因为它能匹配你电脑上实际安装的游戏版本。

```bash
python mc-bedrock-fast-code/scripts/prepare_knowledge.py --root ~/.codex/mc-bedrock-fast-code-data --api-docs --demo-source ./6-1DemoMod --demo-source "<path-to-6-4-resource-demo>" --mc-root "<.../MCStudioDownload/game/MinecraftPE_Netease>" --list-versions-only
```

选择代表版本后再建立原版索引：

```bash
python mc-bedrock-fast-code/scripts/prepare_knowledge.py --root ~/.codex/mc-bedrock-fast-code-data --vanilla-index --mc-root "<.../MinecraftPE_Netease>" --pretty
```

一般建议一个大版本只建一个代表索引，例如 3.7 一个、3.8 一个。除非你需要比较小版本差异，否则没有必要把所有补丁版本都建一遍。

## 下载远程粗略索引

如果你不想本地生成，或者没有安装原版包库，可以下载公开粗略索引：

```bash
python mc-bedrock-fast-code/scripts/prepare_knowledge.py --root ~/.codex/mc-bedrock-fast-code-data --remote-indexes --remote-url "https://github.com/Trryer/mc-bedrock-fast-code/releases/latest/download/mc-bedrock-fast-code-public-index.zip"
```

远程索引适合做名称、路径、常见写法查询；它不是完整权威数据。需要版本精确行为时，仍建议使用本地索引。

## 下载官方公开 Demo

网易官方 ModSDK Demo 示例页面提供了公开的 3.8 demo 包：

- 页面：<https://mc.163.com/dev/mcmanual/mc-dev/mcguide/20-%E7%8E%A9%E6%B3%95%E5%BC%80%E5%8F%91/13-%E6%A8%A1%E7%BB%84SDK%E7%BC%96%E7%A8%8B/60-Demo%E7%A4%BA%E4%BE%8B.html>
- 官方下载：<https://g79.gdl.netease.com/3.8Demo.zip>

skill 下载脚本默认使用官方地址：

```bash
python mc-bedrock-fast-code/scripts/download_demo_mirror.py --out ./mc-bedrock-official-public-demos
```

脚本也提供 `--private-mirror`，用于仓库所有者自己的私人备份下载。这个备份只是官方公开包的个人镜像，不属于本公开仓库内容，并且可能需要 GitHub 私人仓库权限。

## 生成代码

创建一个带客户端、服务端、UI 初始结构的空白包：

```bash
python mc-bedrock-fast-code/scripts/fast_code.py create-pack --namespace demo_mod --out ./DemoMod --with-client --with-server --with-ui
```

添加物品：

```bash
python mc-bedrock-fast-code/scripts/fast_code.py add-item --project ./DemoMod --namespace demo_mod --id copper_coin
```

添加生物，并说明它想参考原版僵尸：

```bash
python mc-bedrock-fast-code/scripts/fast_code.py add-entity --project ./DemoMod --namespace demo_mod --id squirrel --base minecraft:zombie
```

添加渲染控制器或动画控制器：

```bash
python mc-bedrock-fast-code/scripts/fast_code.py add-render-controller --project ./DemoMod --namespace demo_mod --id squirrel
python mc-bedrock-fast-code/scripts/fast_code.py add-animation-controller --project ./DemoMod --namespace demo_mod --id squirrel --side resource
```

## 必填信息

生成固定结构时，不能缺少关键 ID。

例如添加一个 item 时，必须提供：

- 项目路径
- 命名空间 `namespace`
- 物品局部 ID `item_id`

因为脚本必须同时创建：

- `netease_items_beh/<item_id>.json`
- `netease_items_res/<item_id>.json`

并且两个文件里都必须写入完整标识符：

```text
<namespace>:<item_id>
```

如果用户没有提供这些信息，skill 应该先询问，而不是猜测或写占位无效文件。

## 查询和诊断

查询官方/远程索引里的名字或常见写法：

```bash
python mc-bedrock-fast-code/scripts/query_knowledge.py zombie --kind render_controller --source remote
python mc-bedrock-fast-code/scripts/query_knowledge.py entity_alphatest --kind material --source remote
```

检查项目里常见引用错误：

```bash
python mc-bedrock-fast-code/scripts/lint_project.py --project ./DemoMod --namespace demo_mod
```

诊断脚本会检查常见问题，例如：

- JSON 格式错误
- 缺少 behavior/resource pack 目录
- UI 文件未写入 `_ui_defs.json`
- client entity 引用了不存在的 render controller
- client entity 引用了不存在的 material、geometry、texture、animation controller
- behavior entity 没有对应的 client entity 文件

## 来源说明

本项目围绕以下公开或本地资料构建：

- 网易 Minecraft / MCStudio 官方公开 demo 包和教程。
- 网易 ModSDK 公开文档，例如 `EaseCation/netease-modsdk-wiki` 等公开镜像。
- 用户本机安装的 `MinecraftPE_Netease` 游戏数据目录。

详见 [NOTICE.md](NOTICE.md)。

## 免责声明

本项目是非官方工具，不隶属于 Mojang、Microsoft、NetEase 或 MCStudio，也未获得其背书、赞助或认可。

Minecraft 及相关名称/资产归其权利方所有。网易 Minecraft、MCStudio、ModSDK 相关资料归其权利方所有。

仓库中的公开索引是元数据摘要，目的是帮助开发者查询和生成代码，不重新分发官方游戏资源、原始 demo 源码或完整游戏数据。

## 许可证

本仓库中的代码使用 MIT License。详见 [LICENSE](LICENSE)。
