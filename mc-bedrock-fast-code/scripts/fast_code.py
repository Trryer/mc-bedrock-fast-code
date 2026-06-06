#!/usr/bin/env python3
"""Generate NetEase Bedrock ModSDK starter packs and common files."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path


def safe_namespace(value: str) -> str:
    ns = re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")
    if not ns:
        raise SystemExit("namespace cannot be empty")
    return ns


def split_identifier(namespace: str, local_id: str) -> tuple[str, str]:
    if ":" in local_id:
        ns, ident = local_id.split(":", 1)
        if namespace and safe_namespace(namespace) != safe_namespace(ns):
            raise SystemExit(f"identifier namespace {ns!r} does not match --namespace {namespace!r}")
        return safe_namespace(ns), safe_namespace(ident)
    return safe_namespace(namespace), safe_namespace(local_id)


def class_name(namespace: str, suffix: str) -> str:
    base = "".join(part.capitalize() for part in namespace.split("_") if part)
    return f"{base}{suffix}"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def manifest(name: str, description: str, pack_type: str) -> dict:
    module_type = "data" if pack_type == "behavior" else "resources"
    return {
        "format_version": 1,
        "header": {
            "description": description,
            "name": name,
            "uuid": str(uuid.uuid4()),
            "version": [0, 0, 1],
        },
        "modules": [
            {
                "description": description,
                "type": module_type,
                "uuid": str(uuid.uuid4()),
                "version": [0, 0, 1],
            }
        ],
    }


def create_pack(args: argparse.Namespace) -> None:
    ns = safe_namespace(args.namespace)
    out = Path(args.out).resolve()
    beh = out / f"{ns}_behavior"
    res = out / f"{ns}_resource"
    script_dir = beh / f"{ns}Scripts"
    beh_manifest = manifest(f"{ns} behavior", f"{ns} behavior pack", "behavior")
    res_manifest = manifest(f"{ns} resource", f"{ns} resource pack", "resource")
    write_json(beh / "manifest.json", beh_manifest)
    write_json(res / "manifest.json", res_manifest)
    write_json(out / "world_behavior_packs.json", [{"pack_id": beh_manifest["header"]["uuid"], "version": [0, 0, 1]}])
    write_json(out / "world_resource_packs.json", [{"pack_id": res_manifest["header"]["uuid"], "version": [0, 0, 1]}])
    write_text(script_dir / "__init__.py", "")
    write_text(script_dir / "modConfig.py", mod_config(ns))
    write_text(script_dir / "modMain.py", mod_main(ns, args.with_server, args.with_client))
    if args.with_server:
        write_text(script_dir / f"{ns}ServerSystem.py", server_system(ns))
    if args.with_client:
        write_text(script_dir / f"{ns}ClientSystem.py", client_system(ns, args.with_ui))
    if args.with_ui:
        add_ui(argparse.Namespace(project=str(out), namespace=ns, screen="main"))
    print(f"Created starter pack at {out}")


def mod_config(ns: str) -> str:
    return f'''# -*- coding: utf-8 -*-

MOD_NAMESPACE = "{ns}"
MOD_VERSION = "0.0.1"
SERVER_SYSTEM = "{class_name(ns, "ServerSystem")}"
CLIENT_SYSTEM = "{class_name(ns, "ClientSystem")}"
UI_NAMESPACE = "{ns}_ui"
UI_MAIN_SCREEN = "main"
'''


def mod_main(ns: str, with_server: bool, with_client: bool) -> str:
    lines = [
        "# -*- coding: utf-8 -*-",
        "from mod.common.mod import Mod",
        "import mod.server.extraServerApi as serverApi",
        "import mod.client.extraClientApi as clientApi",
        f"from {ns}Scripts import modConfig",
        "",
        '@Mod.Binding(name=modConfig.MOD_NAMESPACE, version=modConfig.MOD_VERSION)',
        f"class {class_name(ns, 'Mod')}(object):",
        "    def __init__(self):",
        '        print "===== init %s =====" % modConfig.MOD_NAMESPACE',
        "",
    ]
    if with_server:
        lines += [
            "    @Mod.InitServer()",
            "    def ServerInit(self):",
            f'        serverApi.RegisterSystem(modConfig.MOD_NAMESPACE, modConfig.SERVER_SYSTEM, "{ns}Scripts.{ns}ServerSystem.{class_name(ns, "ServerSystem")}")',
            "",
            "    @Mod.DestroyServer()",
            "    def ServerDestroy(self):",
            "        pass",
            "",
        ]
    if with_client:
        lines += [
            "    @Mod.InitClient()",
            "    def ClientInit(self):",
            f'        clientApi.RegisterSystem(modConfig.MOD_NAMESPACE, modConfig.CLIENT_SYSTEM, "{ns}Scripts.{ns}ClientSystem.{class_name(ns, "ClientSystem")}")',
            "",
            "    @Mod.DestroyClient()",
            "    def ClientDestroy(self):",
            "        pass",
            "",
        ]
    return "\n".join(lines)


def server_system(ns: str) -> str:
    return f'''# -*- coding: utf-8 -*-
import mod.server.extraServerApi as serverApi
from {ns}Scripts import modConfig

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()


class {class_name(ns, "ServerSystem")}(ServerSystem):
    def __init__(self, namespace, systemName):
        super({class_name(ns, "ServerSystem")}, self).__init__(namespace, systemName)
        self.ListenEvent()

    def ListenEvent(self):
        pass

    def UnListenEvent(self):
        pass

    def Destroy(self):
        self.UnListenEvent()
'''


def client_system(ns: str, with_ui: bool) -> str:
    ui_methods = ""
    if with_ui:
        ui_methods = '''
    def OpenMainScreen(self):
        # Register and open UI here when wiring the screen to gameplay.
        pass
'''
    return f'''# -*- coding: utf-8 -*-
import mod.client.extraClientApi as clientApi
from {ns}Scripts import modConfig

ClientSystem = clientApi.GetClientSystemCls()


class {class_name(ns, "ClientSystem")}(ClientSystem):
    def __init__(self, namespace, systemName):
        super({class_name(ns, "ClientSystem")}, self).__init__(namespace, systemName)
{ui_methods}
    def Destroy(self):
        pass
'''


def project_dirs(project: str, ns: str) -> tuple[Path, Path, Path]:
    root = Path(project).resolve()
    return root, root / f"{ns}_behavior", root / f"{ns}_resource"


def add_ui(args: argparse.Namespace) -> None:
    ns = safe_namespace(args.namespace)
    root, _beh, res = project_dirs(args.project, ns)
    screen = safe_namespace(args.screen)
    ui_file = f"{screen}.json"
    ui_defs = res / "ui" / "_ui_defs.json"
    existing = {"ui_defs": []}
    if ui_defs.exists():
        try:
            existing = json.loads(ui_defs.read_text(encoding="utf-8-sig"))
        except Exception:
            existing = {"ui_defs": []}
    entry = f"ui/{ui_file}"
    defs = existing.setdefault("ui_defs", [])
    if entry not in defs:
        defs.append(entry)
    write_json(ui_defs, existing)
    write_json(res / "ui" / ui_file, {
        "namespace": f"{ns}_ui",
        f"{screen}_screen": {
            "type": "screen",
            "controls": [
                {
                    "root_panel": {
                        "type": "panel",
                        "size": ["100%", "100%"],
                        "controls": []
                    }
                }
            ]
        }
    })
    print(f"Added UI screen {screen} under {root}")


def add_item(args: argparse.Namespace) -> None:
    ns, item_id = split_identifier(args.namespace, args.id)
    _root, beh, res = project_dirs(args.project, ns)
    identifier = f"{ns}:{item_id}"
    write_json(beh / "netease_items_beh" / f"{item_id}.json", {
        "format_version": "1.10",
        "minecraft:item": {
            "description": {"identifier": identifier, "category": "Items"},
            "components": {"minecraft:max_stack_size": args.max_stack_size},
        },
    })
    write_json(res / "netease_items_res" / f"{item_id}.json", {
        "format_version": "1.10",
        "minecraft:item": {
            "description": {"identifier": identifier, "category": "Items"},
            "components": {"minecraft:icon": f"{ns}:{item_id}"},
        },
    })
    update_texture_atlas(res / "textures" / "item_texture.json", ns, item_id, f"textures/items/{item_id}")
    append_lang(res / "texts" / "zh_CN.lang", f"item.{identifier}.name", args.display_name or item_id)
    print(f"Added item {identifier}")


def add_block(args: argparse.Namespace) -> None:
    ns, block_id = split_identifier(args.namespace, args.id)
    _root, beh, res = project_dirs(args.project, ns)
    identifier = f"{ns}:{block_id}"
    write_json(beh / "netease_blocks" / f"{block_id}.json", {
        "format_version": "1.10",
        "minecraft:block": {
            "description": {"identifier": identifier},
            "components": {
                "minecraft:block_light_absorption": 0,
                "minecraft:destroy_time": 1.0,
                "netease:render_layer": {"value": "opaque"},
            },
        },
    })
    update_blocks_json(res / "blocks.json", identifier, block_id)
    update_texture_atlas(res / "textures" / "terrain_texture.json", ns, block_id, f"textures/blocks/{block_id}")
    append_lang(res / "texts" / "zh_CN.lang", f"tile.{identifier}.name", args.display_name or block_id)
    print(f"Added block {identifier}")


def add_entity(args: argparse.Namespace) -> None:
    ns, ent_id = split_identifier(args.namespace, args.id)
    _root, beh, res = project_dirs(args.project, ns)
    identifier = f"{ns}:{ent_id}"
    write_json(beh / "entities" / f"{ent_id}.json", {
        "format_version": "1.10.0",
        "minecraft:entity": {
            "description": {
                "identifier": identifier,
                "is_spawnable": True,
                "is_summonable": True,
            },
            "components": {
                "minecraft:type_family": {"family": [ent_id]},
                "minecraft:health": {"value": 20, "max": 20},
                "minecraft:movement": {"value": 0.25},
                "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_water": True},
                "minecraft:behavior.float": {"priority": 0},
                "minecraft:behavior.random_stroll": {"priority": 6, "speed_multiplier": 0.8},
                "minecraft:physics": {},
                "minecraft:collision_box": {"width": 0.6, "height": 1.8},
            },
            "events": {},
        },
    })
    write_json(res / "entity" / f"{ent_id}.entity.json", {
        "format_version": "1.8.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": identifier,
                "spawn_egg": {"base_color": "#6BA7D6", "overlay_color": "#FFFFFF"},
                "render_controllers": [f"controller.render.{ent_id}"],
                "geometry": {"default": f"geometry.{ent_id}"},
                "textures": {"default": f"textures/entity/{ent_id}/{ent_id}"},
                "materials": {"default": "entity_alphatest"},
            }
        },
    })
    write_json(res / "render_controllers" / f"{ent_id}.render_controllers.json", {
        "format_version": "1.8.0",
        "render_controllers": {
            f"controller.render.{ent_id}": {
                "geometry": "Geometry.default",
                "materials": [{"*": "Material.default"}],
                "textures": ["Texture.default"],
            }
        },
    })
    if args.base:
        note = res / "entity" / f"{ent_id}.base_note.txt"
        write_text(note, f"Requested base vanilla entity: {args.base}\nQuery local vanilla index before copying components.\n")
    append_lang(res / "texts" / "zh_CN.lang", f"entity.{identifier}.name", args.display_name or ent_id)
    print(f"Added entity {identifier}")


def add_animation(args: argparse.Namespace) -> None:
    ns = safe_namespace(args.namespace)
    anim_id = safe_namespace(args.id)
    _root, _beh, res = project_dirs(args.project, ns)
    key = f"animation.{ns}.{anim_id}"
    write_json(res / "animations" / f"{anim_id}.animation.json", {
        "format_version": "1.8.0",
        "animations": {
            key: {
                "loop": True,
                "animation_length": 1.0,
                "bones": {},
            }
        },
    })
    print(f"Added animation {key}")


def add_animation_controller(args: argparse.Namespace) -> None:
    ns = safe_namespace(args.namespace)
    ctrl_id = safe_namespace(args.id)
    _root, beh, res = project_dirs(args.project, ns)
    base = beh if args.side == "behavior" else res
    key = f"controller.animation.{ns}.{ctrl_id}"
    write_json(base / "animation_controllers" / f"{ctrl_id}.animation_controllers.json", {
        "format_version": "1.8.0",
        "animation_controllers": {
            key: {
                "initial_state": "default",
                "states": {
                    "default": {
                        "animations": [],
                        "transitions": []
                    }
                }
            }
        },
    })
    print(f"Added {args.side} animation controller {key}")


def add_render_controller(args: argparse.Namespace) -> None:
    ns = safe_namespace(args.namespace)
    ctrl_id = safe_namespace(args.id)
    _root, _beh, res = project_dirs(args.project, ns)
    key = f"controller.render.{ns}.{ctrl_id}"
    write_json(res / "render_controllers" / f"{ctrl_id}.render_controllers.json", {
        "format_version": "1.8.0",
        "render_controllers": {
            key: {
                "geometry": "Geometry.default",
                "materials": [{"*": "Material.default"}],
                "textures": ["Texture.default"],
            }
        },
    })
    print(f"Added render controller {key}")


def add_material(args: argparse.Namespace) -> None:
    ns = safe_namespace(args.namespace)
    mat_id = safe_namespace(args.id)
    _root, _beh, res = project_dirs(args.project, ns)
    write_json(res / "materials" / "common.json", {
        "materials": {
            f"version.{ns}.{mat_id}": {"materials": {"default": mat_id}},
            mat_id: {
                "+defines": ["USE_TEXTURE"],
                "vertexShader": "shaders/entity.vertex",
                "fragmentShader": "shaders/entity.fragment",
            },
        }
    })
    print(f"Added material {mat_id}")


def add_particle(args: argparse.Namespace) -> None:
    ns, particle_id = split_identifier(args.namespace, args.id)
    _root, _beh, res = project_dirs(args.project, ns)
    identifier = f"{ns}:{particle_id}"
    write_json(res / "particles" / f"{particle_id}.json", {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {
                "identifier": identifier,
                "basic_render_parameters": {
                    "material": "particles_alpha",
                    "texture": f"textures/particle/{particle_id}",
                },
            },
            "components": {
                "minecraft:emitter_rate_instant": {"num_particles": 1},
                "minecraft:emitter_lifetime_once": {"active_time": 1},
                "minecraft:particle_lifetime_expression": {"max_lifetime": 1},
                "minecraft:particle_appearance_billboard": {
                    "size": [0.25, 0.25],
                    "facing_camera_mode": "rotate_xyz",
                    "uv": {"texture_width": 16, "texture_height": 16, "uv": [0, 0], "uv_size": [16, 16]},
                },
            },
        },
    })
    print(f"Added particle {identifier}")


def update_texture_atlas(path: Path, ns: str, key: str, texture: str) -> None:
    atlas_name = "atlas.terrain" if path.name == "terrain_texture.json" else "atlas.items"
    data = {"resource_pack_name": ns, "texture_name": atlas_name, "texture_data": {}}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    data.setdefault("texture_data", {})[f"{ns}:{key}"] = {"textures": texture}
    write_json(path, data)


def update_blocks_json(path: Path, identifier: str, texture_key: str) -> None:
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    data[identifier] = {"textures": texture_key, "sound": "stone"}
    write_json(path, data)


def append_lang(path: Path, key: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{key}={value}\n"
    if path.exists() and key in path.read_text(encoding="utf-8", errors="ignore"):
        return
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-pack")
    p.add_argument("--namespace", required=True, help="Required namespace, e.g. demo_mod.")
    p.add_argument("--out", required=True, help="Required output project path.")
    p.add_argument("--with-client", action="store_true", default=True)
    p.add_argument("--with-server", action="store_true", default=True)
    p.add_argument("--with-ui", action="store_true")
    p.set_defaults(func=create_pack)
    p = sub.add_parser("add-ui")
    p.add_argument("--project", required=True, help="Required existing project path.")
    p.add_argument("--namespace", required=True, help="Required namespace, e.g. demo_mod.")
    p.add_argument("--screen", default="main", help="Required UI screen id; defaults to main when the user asked for a generic starter UI.")
    p.set_defaults(func=add_ui)
    p = sub.add_parser("add-item")
    p.add_argument("--project", required=True, help="Required existing project path.")
    p.add_argument("--namespace", required=True, help="Required namespace part of <namespace>:<item_id>.")
    p.add_argument("--id", required=True, help="Required local item id part of <namespace>:<item_id>.")
    p.add_argument("--display-name")
    p.add_argument("--max-stack-size", type=int, default=64)
    p.set_defaults(func=add_item)
    p = sub.add_parser("add-block")
    p.add_argument("--project", required=True, help="Required existing project path.")
    p.add_argument("--namespace", required=True, help="Required namespace part of <namespace>:<block_id>.")
    p.add_argument("--id", required=True, help="Required local block id part of <namespace>:<block_id>.")
    p.add_argument("--display-name")
    p.set_defaults(func=add_block)
    p = sub.add_parser("add-entity")
    p.add_argument("--project", required=True, help="Required existing project path.")
    p.add_argument("--namespace", required=True, help="Required namespace part of <namespace>:<entity_id>.")
    p.add_argument("--id", required=True, help="Required local entity id part of <namespace>:<entity_id>.")
    p.add_argument("--display-name")
    p.add_argument("--base", help="Optional vanilla entity identifier to query from local indexes before refinement.")
    p.set_defaults(func=add_entity)
    p = sub.add_parser("add-animation")
    p.add_argument("--project", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--id", required=True)
    p.set_defaults(func=add_animation)
    p = sub.add_parser("add-animation-controller")
    p.add_argument("--project", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--side", choices=["resource", "behavior"], default="resource")
    p.set_defaults(func=add_animation_controller)
    p = sub.add_parser("add-render-controller")
    p.add_argument("--project", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--id", required=True)
    p.set_defaults(func=add_render_controller)
    p = sub.add_parser("add-material")
    p.add_argument("--project", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--id", required=True)
    p.set_defaults(func=add_material)
    p = sub.add_parser("add-particle")
    p.add_argument("--project", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--id", required=True)
    p.set_defaults(func=add_particle)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
