#!/usr/bin/env python3
"""
Claude Code PreToolUse guard for destructive Bash commands.

Install this file at ~/.claude/hooks/destructive_bash_guard.py and register it
under hooks.PreToolUse with matcher "Bash".
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


HOOK_EVENT_NAME = "PreToolUse"
DEFAULT_LOG_PATH = Path.home() / ".claude" / "hooks" / "blocked.log"

SQL_CLIENTS = {
    "psql",
    "mysql",
    "mariadb",
    "sqlite3",
    "sqlcmd",
    "isql",
    "pgcli",
    "mycli",
}

COMMAND_SEPARATORS = {";", "&&", "||", "|", "&"}

DROP_TABLE_PATTERN = re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE)
TRUNCATE_PATTERN = re.compile(r"\bTRUNCATE(?:\s+TABLE)?\b", re.IGNORECASE)
DELETE_FROM_PATTERN = re.compile(r"\bDELETE\s+FROM\s+[\w.$`\"\[\]-]+", re.IGNORECASE)
WHERE_PATTERN = re.compile(r"\bWHERE\b", re.IGNORECASE)


def hook_log_path() -> Path:
    """Return the production log path, with a test-only environment override."""
    configured = os.environ.get("CLAUDE_HOOK_LOG_PATH")
    return Path(configured).expanduser() if configured else DEFAULT_LOG_PATH


def read_payload() -> dict[str, Any] | None:
    """Read one Claude Code hook JSON object from stdin."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def shell_segments(command: str) -> Iterable[list[str]]:
    """
    Split a shell command into argv-like segments.

    Quotes are handled by shlex, preventing quoted documentation or echo text
    from being interpreted as an executable rm command.
    """
    try:
        tokens = shlex.split(command, posix=True, comments=False)
    except ValueError:
        # An unterminated quote must not crash or block unrelated work.
        return []

    segment: list[str] = []
    segments: list[list[str]] = []

    for token in tokens:
        if token in COMMAND_SEPARATORS:
            if segment:
                segments.append(segment)
                segment = []
            continue
        segment.append(token)

    if segment:
        segments.append(segment)

    return segments


def executable_name(segment: list[str]) -> str:
    """Return the basename of the executable after common environment prefixes."""
    index = 0
    while index < len(segment):
        token = segment[index]
        if token == "env":
            index += 1
            while index < len(segment) and "=" in segment[index]:
                index += 1
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            index += 1
            continue
        return Path(token).name.lower()
    return ""


def is_recursive_force_rm(segment: list[str]) -> bool:
    """Detect rm with both recursive and force semantics."""
    if executable_name(segment) != "rm":
        return False

    recursive = False
    force = False

    for argument in segment[1:]:
        if argument == "--":
            break
        if argument in {"--recursive", "--dir"}:
            recursive = True
        elif argument == "--force":
            force = True
        elif argument.startswith("-") and not argument.startswith("--"):
            flags = argument[1:]
            recursive = recursive or "r" in flags or "R" in flags
            force = force or "f" in flags

    return recursive and force


def is_force_push(segment: list[str]) -> bool:
    """Detect git push force variants, including compact short options."""
    if executable_name(segment) != "git" or len(segment) < 2 or segment[1] != "push":
        return False

    for argument in segment[2:]:
        if argument in {"--force", "--force-with-lease"}:
            return True
        if argument.startswith("-") and not argument.startswith("--") and "f" in argument[1:]:
            return True
    return False


def is_sql_execution_segment(segment: list[str]) -> bool:
    """Avoid blocking harmless searches or echo statements containing SQL text."""
    return executable_name(segment) in SQL_CLIENTS


def sql_statements(command: str) -> Iterable[str]:
    """
    Yield SQL statements that are plausibly being executed.

    Shell clients execute SQL supplied as arguments. SQL-only input is also
    supported for wrappers which send the complete statement as Bash input.
    """
    segments = list(shell_segments(command))
    if any(is_sql_execution_segment(segment) for segment in segments):
        yield from re.split(r";", command)
        return

    if DROP_TABLE_PATTERN.search(command) or TRUNCATE_PATTERN.search(command) or DELETE_FROM_PATTERN.search(command):
        first_executable = executable_name(segments[0]) if segments else ""
        if first_executable not in {"echo", "printf", "rg", "grep", "git"}:
            yield from re.split(r";", command)


def destructive_sql_reason(command: str) -> str | None:
    """Return a reason when SQL contains an explicitly prohibited operation."""
    for statement in sql_statements(command):
        if DROP_TABLE_PATTERN.search(statement):
            return "DROP TABLE permanently removes a database table."
        if TRUNCATE_PATTERN.search(statement):
            return "TRUNCATE removes all rows from a table."
        delete_match = DELETE_FROM_PATTERN.search(statement)
        if delete_match and not WHERE_PATTERN.search(statement[delete_match.end():]):
            return "DELETE FROM without a WHERE clause can remove every row in a table."
    return None


def blocked_reason(command: str) -> str | None:
    """Return the first matching policy violation, or None when allowed."""
    for segment in shell_segments(command):
        if is_recursive_force_rm(segment):
            return "rm with recursive and force flags can irreversibly delete files."
        if is_force_push(segment):
            return "git push --force can overwrite shared remote history."

    return destructive_sql_reason(command)


def append_block_log(command: str, project_path: str, reason: str) -> None:
    """Append a durable JSONL audit record without exposing a logging failure."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attempted_command": command,
        "project_path": project_path,
        "reason": reason,
    }

    path = hook_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as log_file:
            log_file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except OSError:
        # The safety decision remains deny even when an audit destination is unavailable.
        pass


def deny(reason: str) -> None:
    """Emit Claude Code's PreToolUse deny response."""
    response = {
        "hookSpecificOutput": {
            "hookEventName": HOOK_EVENT_NAME,
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Blocked destructive Bash command: {reason} "
                "Use a scoped, reversible operation or obtain explicit human approval."
            ),
        }
    }
    print(json.dumps(response, separators=(",", ":")))


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0

    if payload.get("hook_event_name") != HOOK_EVENT_NAME:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0

    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    reason = blocked_reason(command)
    if reason is None:
        return 0

    project_path = payload.get("cwd")
    append_block_log(command, project_path if isinstance(project_path, str) else "", reason)
    deny(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
