# Destructive Bash Guard for Claude Code

Blocks dangerous Bash tool calls before execution:

- `rm -rf` and equivalent recursive-force flag combinations
- `DROP TABLE`
- `TRUNCATE`
- `DELETE FROM` without `WHERE`
- `git push --force`, `--force-with-lease`, and `-f`

Blocked attempts are appended to `~/.claude/hooks/blocked.log` as JSONL records.

## Install

