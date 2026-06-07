#!/usr/bin/env python3
"""Check and prepare the Python environment expected by NetEase ModSDK projects."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import detect_project


REQUIRED_VERSION = (2, 7, 18)
SDK_PACKAGE = "mc-netease-sdk"


def command_display(command: list[str]) -> str:
    return subprocess.list2cmdline(command) if os.name == "nt" else " ".join(command)


def normalize_package_name(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace(".", "-")


def version_tuple(value: str) -> tuple[int, int, int] | None:
    parts = value.strip().split(".")
    if len(parts) < 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None


def python_command_from_path(value: str) -> list[str]:
    path = Path(value).expanduser()
    if path.is_dir():
        candidates = [path / "python.exe", path / "python", path / "bin" / "python"]
        for candidate in candidates:
            if candidate.exists():
                return [str(candidate)]
    return [str(path)]


def run_python(command: list[str], code: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command + ["-c", code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )


def inspect_python(command: list[str]) -> dict[str, object]:
    code = "import sys; sys.stdout.write('%d.%d.%d' % sys.version_info[:3])"
    try:
        completed = run_python(command, code, timeout=10)
    except Exception as exc:
        return {
            "command": command_display(command),
            "ok": False,
            "error": str(exc),
        }
    version = completed.stdout.strip()
    return {
        "argv": command,
        "command": command_display(command),
        "ok": completed.returncode == 0 and bool(version_tuple(version)),
        "version": version,
        "error": completed.stderr.strip() if completed.returncode else "",
    }


def candidate_python_commands(user_python: str | None) -> list[list[str]]:
    commands: list[list[str]] = []
    commands.append([sys.executable])
    if user_python:
        commands.append(python_command_from_path(user_python))

    names = ["python2", "python2.7", "python"]
    if os.name == "nt":
        names = ["python", "python2", "python2.7"]
        if shutil.which("py"):
            commands.extend([["py", "-2.7"], ["py", "-2"]])
    for name in names:
        found = shutil.which(name)
        if found:
            commands.append([found])

    if os.name == "nt":
        for path in (
            r"C:\Python27\python.exe",
            str(Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python27" / "python.exe"),
        ):
            if Path(path).exists():
                commands.append([path])

    seen: set[str] = set()
    unique: list[list[str]] = []
    for command in commands:
        key = command_display(command).lower()
        if key not in seen:
            seen.add(key)
            unique.append(command)
    return unique


def pip_list(command: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command + ["-m", "pip", "list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=40,
        )
    except Exception as exc:
        return {"ok": False, "packages": [], "error": str(exc)}
    packages: list[str] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("-") or line.lower().startswith("package "):
            continue
        packages.append(line.split()[0])
    return {
        "ok": completed.returncode == 0,
        "packages": packages,
        "error": completed.stderr.strip() if completed.returncode else "",
    }


def install_sdk(command: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command + ["-m", "pip", "install", SDK_PACKAGE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": completed.returncode == 0,
        "stdout_tail": "\n".join(completed.stdout.splitlines()[-20:]),
        "error": completed.stderr.strip() if completed.returncode else "",
    }


def ensure_modsdk_python(
    project: Path,
    user_python: str | None = None,
    install_missing_sdk: bool = True,
    accept_unsupported_python: bool = False,
) -> dict[str, object]:
    project_info = detect_project.detect_project(project)
    result: dict[str, object] = {
        "project": str(project),
        "is_netease_bedrock_project": project_info["is_netease_bedrock_project"],
        "required_python": ".".join(str(part) for part in REQUIRED_VERSION),
        "sdk_package": SDK_PACKAGE,
        "messages": [],
    }
    messages: list[str] = result["messages"]  # type: ignore[assignment]
    if not project_info["is_netease_bedrock_project"]:
        result["status"] = "skipped"
        messages.append("Workspace is not detected as a NetEase ModSDK project; Python 2.7.18 check skipped.")
        return result

    inspections = [inspect_python(command) for command in candidate_python_commands(user_python)]
    result["python_candidates"] = inspections
    usable_exact = []
    python2_candidates = []
    for inspection in inspections:
        vt = version_tuple(str(inspection.get("version", ""))) if inspection.get("ok") else None
        if vt == REQUIRED_VERSION:
            usable_exact.append(inspection)
        if vt and vt[0] == 2:
            python2_candidates.append(inspection)

    current = inspections[0] if inspections else {}
    result["current_python"] = current
    current_version = version_tuple(str(current.get("version", ""))) if current.get("ok") else None
    selected = usable_exact[0] if usable_exact else None
    if current_version != REQUIRED_VERSION:
        messages.append(
            "The current Python is not 2.7.18. Ask the user to switch/update the project Python to Python 2.7.18."
        )

    if not selected:
        if python2_candidates:
            found = ", ".join(f"{item.get('command')} ({item.get('version')})" for item in python2_candidates)
            messages.append(f"Python 2 was found, but not Python 2.7.18: {found}. Ask the user to update it to 2.7.18 or specify a 2.7.18 path.")
        else:
            messages.append("No Python 2 interpreter was detected automatically. Ask the user to specify the Python 2.7.18 executable or install Python 2.7.18.")
        if accept_unsupported_python:
            result["status"] = "unsupported_python_accepted"
            messages.append("User accepted an unsupported Python version. Syntax compilation checks may not reliably validate the project; skip further Python-version handling.")
            return result
        result["status"] = "action_required"
        result["requested_action"] = "Provide a Python 2.7.18 executable path or install Python 2.7.18."
        return result

    selected_command = str(selected["command"])
    result["selected_python"] = selected
    selected_argv = list(selected["argv"])  # type: ignore[index]
    if current_version != REQUIRED_VERSION:
        messages.append(f"Python 2.7.18 was detected at {selected_command}. Use this interpreter for ModSDK syntax checks.")
    else:
        messages.append("Current Python is Python 2.7.18.")

    pip_state = pip_list(selected_argv)
    result["pip_list"] = {
        "ok": pip_state["ok"],
        "has_sdk": SDK_PACKAGE in {normalize_package_name(name) for name in pip_state.get("packages", [])},
        "error": pip_state.get("error", ""),
    }
    if not pip_state["ok"]:
        result["status"] = "pip_unavailable"
        messages.append(f"Could not run pip list with {selected_command}. Ensure pip is installed for Python 2.7.18.")
        return result

    if result["pip_list"]["has_sdk"]:  # type: ignore[index]
        result["status"] = "ok"
        messages.append(f"{SDK_PACKAGE} is already installed.")
        return result

    messages.append(f"{SDK_PACKAGE} is missing from pip list.")
    if not install_missing_sdk:
        result["status"] = "sdk_missing"
        messages.append(f"Install it with: {selected_command} -m pip install {SDK_PACKAGE}")
        return result

    install_state = install_sdk(selected_argv)
    result["sdk_install"] = install_state
    if not install_state["ok"]:
        result["status"] = "sdk_install_failed"
        messages.append(f"Failed to install {SDK_PACKAGE}. Ask the user to install it manually with Python 2.7.18 pip.")
        return result

    recheck = pip_list(selected_argv)
    result["pip_list_after_install"] = {
        "ok": recheck["ok"],
        "has_sdk": SDK_PACKAGE in {normalize_package_name(name) for name in recheck.get("packages", [])},
        "error": recheck.get("error", ""),
    }
    if result["pip_list_after_install"]["has_sdk"]:  # type: ignore[index]
        result["status"] = "ok"
        messages.append(f"Installed {SDK_PACKAGE}.")
    else:
        result["status"] = "sdk_install_unverified"
        messages.append(f"{SDK_PACKAGE} install command completed, but pip list did not confirm the package.")
    return result


def print_human(result: dict[str, object]) -> None:
    print(f"Project: {result['project']}")
    print(f"NetEase Bedrock project: {result['is_netease_bedrock_project']}")
    print(f"Required Python: {result['required_python']}")
    print(f"Status: {result.get('status')}")
    current = result.get("current_python")
    if isinstance(current, dict):
        print(f"Current Python: {current.get('command')} ({current.get('version', 'unknown')})")
    selected = result.get("selected_python")
    if isinstance(selected, dict):
        print(f"Selected Python: {selected.get('command')} ({selected.get('version')})")
    pip_state = result.get("pip_list")
    if isinstance(pip_state, dict):
        print(f"{SDK_PACKAGE} installed: {pip_state.get('has_sdk')}")
    for message in result.get("messages", []):
        print(f"- {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Workspace/project directory to inspect.")
    parser.add_argument("--python", help="Path to a Python 2.7.18 executable or its install directory.")
    parser.add_argument("--no-install", action="store_true", help=f"Only report whether {SDK_PACKAGE} is missing.")
    parser.add_argument(
        "--accept-unsupported-python",
        action="store_true",
        help="Warn and stop checking Python if the user declines Python 2.7.18.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = ensure_modsdk_python(
        Path(args.project).resolve(),
        user_python=args.python,
        install_missing_sdk=not args.no_install,
        accept_unsupported_python=args.accept_unsupported_python,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    status = result.get("status")
    if status in {"ok", "skipped", "unsupported_python_accepted"}:
        return 0
    if status in {"action_required", "pip_unavailable"}:
        return 4
    return 5


if __name__ == "__main__":
    raise SystemExit(main())
