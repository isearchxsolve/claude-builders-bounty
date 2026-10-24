---
name: generate-changelog
description: Automatically generates a structured CHANGELOG.md from git commit history since the last tag.
---
# Generate Changelog Skill

Run this skill to inspect git history since the latest release tag and generate or prepend a structured `CHANGELOG.md`.

## Instructions:
1. Identify the latest git tag using `git describe --tags --abbrev=0 2>/dev/null`.
2. Inspect all commits in `${LAST_TAG}..HEAD`.
3. Categorize each commit into:
   - **Added**: new features, endpoints, capabilities (`feat:`, `add:`)
   - **Fixed**: bug fixes, patches, regressions (`fix:`, `patch:`)
   - **Changed**: refactoring, dependencies, performance (`refactor:`, `perf:`, `chore:`)
   - **Removed**: deletions, deprecated functions (`remove:`, `deprecate:`)
4. Output structured section under `## [Unreleased] - YYYY-MM-DD` adhering to Keep a Changelog.
