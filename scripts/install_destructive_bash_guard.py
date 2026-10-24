#!/usr/bin/env python3
"""Install the destructive Bash guard into the current user's Claude Code config."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any


SOURCE_HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "destructive_bash_guard.py"
CLAUDE_HOME = Path.home() / ".claude"
TARGET_HOOK = CLAUDE_HOME / "hooks" / SOURCE_HOOK.name
SETTINGS_PATH = CLAUDE_HOME / "settings.json"


def load_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}

    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot safely read {SETTINGS_PATH}: {error}") from error

    if not isinstance(settings, dict):
        raise RuntimeError(f"{SETTINGS_PATH} must contain a JSON object.")
    return settings


def main() -> int:
    if not SOURCE_HOOK.is_file():
        raise RuntimeError(f"Hook source is missing: {SOURCE_HOOK}")

    TARGET_HOOK.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_HOOK, TARGET_HOOK)

    settings = load_settings()
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise RuntimeError(f"{SETTINGS_PATH} has a non-object 'hooks' value.")

    pre_tool_use = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre_tool_use, list):
        raise RuntimeError(f"{SETTINGS_PATH} has a non-list 'hooks.PreToolUse' value.")

    command = f'"{sys.executable}" "{TARGET_HOOK}"'
    registration = {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": command}],
    }

    registered = any(
        isinstance(entry, dict)
        and entry.get("matcher") == "Bash"
        and isinstance(entry.get("hooks"), list)
        and any(
            isinstance(hook, dict) and hook.get("command") == command
            for hook in entry["hooks"]
        )
        for entry in pre_tool_use
    )
    if not registered:
        pre_tool_use.append(registration)

    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = SETTINGS_PATH.with_suffix(".json.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as settings_file:
        json.dump(settings, settings_file, indent=2, ensure_ascii=False)
        settings_file.write("\n")
    temporary_path.replace(SETTINGS_PATH)

    print(f"Installed hook: {TARGET_HOOK}")
    print(f"Registered PreToolUse Bash guard: {SETTINGS_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
