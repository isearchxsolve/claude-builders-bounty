#!/usr/bin/env bash
# ==============================================================================
# changelog.sh - Auto-generates structured CHANGELOG.md from git history
# ==============================================================================
set -euo pipefail

# Check git repository
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Must be run inside a git repository." >&2
    exit 1
fi

OUTPUT_FILE="${1:-CHANGELOG.md}"
DATE="$(date +%Y-%m-%d)"

# 1. Determine commit range since last tag
LAST_TAG="$(git describe --tags --abbrev=0 2>/dev/null || true)"
if [ -n "$LAST_TAG" ]; then
    RANGE="${LAST_TAG}..HEAD"
    HEADER="## [Unreleased] - ${DATE} (since ${LAST_TAG})"
else
    RANGE="HEAD"
    HEADER="## [Unreleased] - ${DATE}"
fi

# 2. Temporary buckets for categorized commits
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

ADDED="${TMP_DIR}/added.txt"
FIXED="${TMP_DIR}/fixed.txt"
CHANGED="${TMP_DIR}/changed.txt"
REMOVED="${TMP_DIR}/removed.txt"

touch "$ADDED" "$FIXED" "$CHANGED" "$REMOVED"

# 3. Categorize commits based on conventional prefixes
while IFS='|' read -r HASH SUBJECT AUTHOR COMMIT_DATE; do
    [ -z "$SUBJECT" ] && continue
    LOWER="$(echo "$SUBJECT" | tr '[:upper:]' '[:lower:]')"
    ENTRY="- ${SUBJECT} (\`${HASH}\`)"

    if [[ "$LOWER" =~ ^(feat|add|new|implement) ]]; then
        echo "$ENTRY" >> "$ADDED"
    elif [[ "$LOWER" =~ ^(fix|bug|patch|resolve|close) ]]; then
        echo "$ENTRY" >> "$FIXED"
    elif [[ "$LOWER" =~ ^(remove|delete|deprecate|drop) ]]; then
        echo "$ENTRY" >> "$REMOVED"
    else
        echo "$ENTRY" >> "$CHANGED"
    fi
done < <(git log "$RANGE" --pretty=format:"%h|%s|%an|%ad" --date=short)

# 4. Assemble structured markdown
RELEASE_BLOCK="${HEADER}\n\n"

if [ -s "$ADDED" ]; then
    RELEASE_BLOCK+="$(printf "### Added\n%s\n\n" "$(cat "$ADDED")")"
fi
if [ -s "$FIXED" ]; then
    RELEASE_BLOCK+="$(printf "### Fixed\n%s\n\n" "$(cat "$FIXED")")"
fi
if [ -s "$CHANGED" ]; then
    RELEASE_BLOCK+="$(printf "### Changed\n%s\n\n" "$(cat "$CHANGED")")"
fi
if [ -s "$REMOVED" ]; then
    RELEASE_BLOCK+="$(printf "### Removed\n%s\n\n" "$(cat "$REMOVED")")"
fi

# 5. Prepend or create CHANGELOG.md
if [ -f "$OUTPUT_FILE" ]; then
    TMP_FINAL="$(mktemp)"
    printf "%b\n" "$RELEASE_BLOCK" > "$TMP_FINAL"
    cat "$OUTPUT_FILE" >> "$TMP_FINAL"
    mv "$TMP_FINAL" "$OUTPUT_FILE"
else
    printf "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n%b" "$RELEASE_BLOCK" > "$OUTPUT_FILE"
fi

echo "✅ Successfully generated ${OUTPUT_FILE} (range: ${RANGE})"
