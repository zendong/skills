#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/pracmo-oss-upload.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

help_output="$("$SCRIPT" --help)"
if rg -q "source|bilibili-cover|material|资料原文件" <<<"$help_output"; then
  fail "help output should only describe practice-assets uploads"
fi

asset="$TMP_ROOT/asset.png"
printf 'fake png bytes' >"$asset"

export PRACMO_APIKEY="test-key"
export OSSUTIL_BIN="/bin/true"

unsupported_stdout="$TMP_ROOT/unsupported.out"
unsupported_stderr="$TMP_ROOT/unsupported.err"
if "$SCRIPT" --category source "$asset" >"$unsupported_stdout" 2>"$unsupported_stderr"; then
  fail "source category should not be supported"
fi
rg -q "只支持 practice-assets" "$unsupported_stderr" || fail "unsupported category did not explain allowed category"

echo "pracmo-oss-upload tests passed"
