from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


HOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / ".claude"
    / "hooks"
    / "destructive_bash_guard.py"
)

SPEC = importlib.util.spec_from_file_location("destructive_bash_guard", HOOK_PATH)
assert SPEC is not None and SPEC.loader is not None
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def payload(command: str, tool_name: str = "Bash") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"command": command},
        "cwd": "/work/community-bounty",
    }


class DestructiveBashGuardTests(unittest.TestCase):
    def test_blocks_recursive_force_rm_short_flags(self) -> None:
        self.assertIn("rm with recursive", guard.blocked_reason("rm -rf ./build") or "")

    def test_blocks_recursive_force_rm_split_flags(self) -> None:
        self.assertIn("rm with recursive", guard.blocked_reason("rm -r -f ./build") or "")

    def test_allows_non_force_rm(self) -> None:
        self.assertIsNone(guard.blocked_reason("rm -r ./build"))

    def test_does_not_treat_echo_text_as_rm(self) -> None:
        self.assertIsNone(guard.blocked_reason('echo "rm -rf /"'))

    def test_blocks_force_push(self) -> None:
        self.assertIn("force", guard.blocked_reason("git push origin main --force") or "")

    def test_blocks_force_with_lease(self) -> None:
        self.assertIn(
            "force",
            guard.blocked_reason("git push --force-with-lease origin main") or "",
        )

    def test_allows_standard_git_push(self) -> None:
        self.assertIsNone(guard.blocked_reason("git push origin main"))

    def test_blocks_drop_table_via_psql(self) -> None:
        self.assertIn(
            "DROP TABLE",
            guard.blocked_reason('psql -c "DROP TABLE accounts"') or "",
        )

    def test_blocks_truncate_via_mysql(self) -> None:
        self.assertIn(
            "TRUNCATE",
            guard.blocked_reason('mysql -e "TRUNCATE TABLE sessions"') or "",
        )

    def test_blocks_unscoped_delete(self) -> None:
        self.assertIn(
            "without a WHERE",
            guard.blocked_reason('sqlite3 app.db "DELETE FROM sessions"') or "",
        )

    def test_allows_scoped_delete(self) -> None:
        self.assertIsNone(
            guard.blocked_reason(
                'sqlite3 app.db "DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP"'
            )
        )

    def test_does_not_block_sql_search_text(self) -> None:
        self.assertIsNone(guard.blocked_reason('rg "DROP TABLE" migrations'))

    def test_non_bash_tool_is_ignored(self) -> None:
        stdin = io.StringIO(json.dumps(payload("rm -rf /tmp/test", tool_name="Read")))
        stdout = io.StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(guard.main(), 0)
        self.assertEqual(stdout.getvalue(), "")

    def test_blocked_command_logs_and_returns_deny_response(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "blocked.log"
            stdin = io.StringIO(json.dumps(payload("rm -rf ./generated")))
            stdout = io.StringIO()

            with patch.dict(
                os.environ,
                {"CLAUDE_HOOK_LOG_PATH": str(log_path)},
                clear=False,
            ), patch("sys.stdin", stdin), redirect_stdout(stdout):
                self.assertEqual(guard.main(), 0)

            response = json.loads(stdout.getvalue())
            hook_output = response["hookSpecificOutput"]
            self.assertEqual(hook_output["hookEventName"], "PreToolUse")
            self.assertEqual(hook_output["permissionDecision"], "deny")
            self.assertIn("rm with recursive", hook_output["permissionDecisionReason"])

            records = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(records), 1)
            record = json.loads(records[0])
            self.assertEqual(record["attempted_command"], "rm -rf ./generated")
            self.assertEqual(record["project_path"], "/work/community-bounty")
            self.assertIn("timestamp", record)
            self.assertIn("rm with recursive", record["reason"])

    def test_normal_bash_command_returns_no_interference_output(self) -> None:
        stdin = io.StringIO(json.dumps(payload("git status --short")))
        stdout = io.StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(guard.main(), 0)
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
