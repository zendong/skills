#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/pracmo-open-api.sh"
FIXED_BASE_URL="https://apis.zendong.com.cn/open/v1"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

stub_dir="$TMP_ROOT/bin"
mkdir -p "$stub_dir"

cat >"$stub_dir/curl" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$PRACMO_OPEN_API_TEST_CURL_ARGS"
printf '{"ok":true}\n200\n'
SH
chmod +x "$stub_dir/curl"

export PRACMO_APIKEY="test-key"
export PRACMO_OPEN_API_BASE="http://should-not-be-used.example/open/v1"
export PRACMO_OPEN_API_TEST_CURL_ARGS="$TMP_ROOT/curl-args.txt"

PATH="$stub_dir:$PATH" "$SCRIPT" get 'learning-tracks?keyword=test' >/dev/null

rg -q "$FIXED_BASE_URL/learning-tracks\\?keyword=test" "$PRACMO_OPEN_API_TEST_CURL_ARGS" \
  || fail "get command did not use fixed API base"

if rg -q "should-not-be-used" "$PRACMO_OPEN_API_TEST_CURL_ARGS"; then
  fail "get command used PRACMO_OPEN_API_BASE"
fi

payload="$TMP_ROOT/payload.json"
printf '{"track":{"mode":"reuse","trackId":"track_1"},"exercise":{"clientRequestId":"req_1","title":"t","questions":[]}}\n' >"$payload"

PATH="$stub_dir:$PATH" "$SCRIPT" learning-track-exercise "$payload" >/dev/null

rg -q "$FIXED_BASE_URL/learning-tracks/with-exercise" "$PRACMO_OPEN_API_TEST_CURL_ARGS" \
  || fail "post command did not use fixed API base"

if rg -q "should-not-be-used" "$PRACMO_OPEN_API_TEST_CURL_ARGS"; then
  fail "post command used PRACMO_OPEN_API_BASE"
fi

echo "pracmo-open-api tests passed"
