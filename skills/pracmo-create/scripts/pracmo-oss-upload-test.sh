#!/usr/bin/env bash
set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")" && pwd)/pracmo-oss-upload.sh"
fail() { echo "FAIL: $*" >&2; exit 1; }
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

help="$($SCRIPT --help)"
rg -q "learning-track-assets" <<<"$help" || fail "help must document learning-track-assets"
rg -q "512KB" <<<"$help" || fail "help must document 512KB limit"
rg -q "request-id" <<<"$help" || fail "help must document request isolation"

printf '<svg xmlns="http://www.w3.org/2000/svg"></svg>' >"$tmp/asset.svg"
if "$SCRIPT" --request-id test-request-v1 --content-type image/svg+xml "$tmp/asset.svg" >/dev/null 2>"$tmp/svg.err"; then
  fail "SVG should be rejected"
fi
rg -q "PNG/JPG" "$tmp/svg.err" || fail "SVG error should explain formats"

dd if=/dev/zero of="$tmp/large.jpg" bs=1024 count=513 >/dev/null 2>&1
if "$SCRIPT" --request-id test-request-v1 --content-type image/jpeg "$tmp/large.jpg" >/dev/null 2>"$tmp/large.err"; then
  fail "oversized image should be rejected"
fi
rg -q "512KB" "$tmp/large.err" || fail "oversize error should explain limit"

if "$SCRIPT" --category practice-assets --request-id test-request-v1 "$tmp/large.jpg" >/dev/null 2>"$tmp/category.err"; then
  fail "legacy category should be rejected"
fi
rg -q "learning-track-assets" "$tmp/category.err" || fail "category error should show allowed category"

echo "pracmo-oss-upload tests passed"
