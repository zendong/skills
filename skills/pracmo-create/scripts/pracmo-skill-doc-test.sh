#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
SKILL_MD="$SKILL_DIR/SKILL.md"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

[[ -f "$SKILL_MD" ]] || fail "SKILL.md not found"

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

if rg -n "private-skills/skills/pracmo-create|skills/pracmo-create" "$SKILL_MD" >"$TMP_ROOT/path.err"; then
  cat "$TMP_ROOT/path.err" >&2
  fail "SKILL.md should use skill-relative paths such as scripts/..."
fi

if rg -n "PRACMO_OPEN_API_BASE" "$SKILL_MD" >"$TMP_ROOT/api-base.err"; then
  cat "$TMP_ROOT/api-base.err" >&2
  fail "SKILL.md should not mention PRACMO_OPEN_API_BASE"
fi

if rg -n "\\b(GET|POST)\\b" "$SKILL_MD" >"$TMP_ROOT/http.err"; then
  cat "$TMP_ROOT/http.err" >&2
  fail "SKILL.md should route API access through scripts, not raw GET/POST instructions"
fi

echo "pracmo skill doc tests passed"
