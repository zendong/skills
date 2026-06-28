#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/pracmo-cache.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_eq() {
  local expected="$1"
  local actual="$2"
  local label="$3"
  if [[ "$expected" != "$actual" ]]; then
    fail "$label: expected '$expected', got '$actual'"
  fi
}

assert_file_exists() {
  local path="$1"
  [[ -f "$path" ]] || fail "expected file to exist: $path"
}

command -v jq >/dev/null 2>&1 || fail "jq is required for tests"

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

unset PRACMO_CREATE_CACHE_DIR
unset PRACMO_CACHE_ACCOUNT_SCOPE
unset PRACMO_OPEN_API_BASE

expected_default_cache_dir="$(cd "$SCRIPT_DIR/.." && pwd -P)/cache"
default_cache_dir="$("$SCRIPT" cache-dir)"
assert_eq "$expected_default_cache_dir" "$default_cache_dir" "cache-dir defaults to skill-local cache directory"
[[ -d "$expected_default_cache_dir/payloads" ]] || fail "skill-local payloads directory was not created"

export PRACMO_CREATE_CACHE_DIR="$TMP_ROOT/cache"
export PRACMO_CACHE_ACCOUNT_SCOPE="acct-test"
export PRACMO_OPEN_API_BASE="http://api-one.example/open/v1"

cache_dir="$("$SCRIPT" cache-dir)"
assert_eq "$PRACMO_CREATE_CACHE_DIR" "$cache_dir" "cache-dir respects PRACMO_CREATE_CACHE_DIR"
[[ -d "$PRACMO_CREATE_CACHE_DIR/payloads" ]] || fail "payloads directory was not created"

source_file="$TMP_ROOT/source.md"
printf 'Concept A\nConcept B\n' >"$source_file"
fingerprint_json="$("$SCRIPT" fingerprint-file "$source_file")"
source_fingerprint="$(jq -r '.fingerprint' <<<"$fingerprint_json")"
assert_eq "sha256:" "${source_fingerprint:0:7}" "file fingerprint has sha256 prefix"
assert_eq "file" "$(jq -r '.kind' <<<"$fingerprint_json")" "file fingerprint kind"

url_fingerprint_a="$("$SCRIPT" fingerprint-url 'https://example.com/a#section' | jq -r '.fingerprint')"
url_fingerprint_b="$("$SCRIPT" fingerprint-url 'https://example.com/a' | jq -r '.fingerprint')"
assert_eq "$url_fingerprint_b" "$url_fingerprint_a" "URL fingerprint strips fragments"

text_fingerprint_a="$("$SCRIPT" fingerprint-text $'  Alpha\n Beta  ' | jq -r '.fingerprint')"
text_fingerprint_b="$("$SCRIPT" fingerprint-text 'Alpha Beta' | jq -r '.fingerprint')"
assert_eq "$text_fingerprint_b" "$text_fingerprint_a" "text fingerprint normalizes whitespace"

mapping_json="$(jq -n \
  --arg fp "$source_fingerprint" \
  --arg sourcePath "$source_file" \
  '{
    source: {kind: "file", uri: $sourcePath, fingerprint: $fp, displayName: "source.md"},
    track: {trackId: "track_123", title: "缓存测试甲程"},
    lastExercise: {exerciseId: "flow_123", nodeId: "node_123", title: "缓存测试练习"}
  }')"
printf '%s' "$mapping_json" | "$SCRIPT" record-source - >/dev/null
lookup_json="$("$SCRIPT" lookup-source "$source_fingerprint")"
assert_eq "track_123" "$(jq -r '.track.trackId' <<<"$lookup_json")" "lookup-source returns recorded track"
assert_eq "acct-test" "$(jq -r '.accountScope' <<<"$lookup_json")" "source mapping is scoped by account"
assert_eq "https://apis.zendong.com.cn/open/v1" "$(jq -r '.apiBase' <<<"$lookup_json")" "source mapping uses fixed API base"

export PRACMO_OPEN_API_BASE="http://api-two.example/open/v1"
lookup_json_after_env_change="$("$SCRIPT" lookup-source "$source_fingerprint")"
assert_eq "track_123" "$(jq -r '.track.trackId' <<<"$lookup_json_after_env_change")" "lookup-source ignores PRACMO_OPEN_API_BASE"
export PRACMO_OPEN_API_BASE="http://api-one.example/open/v1"

payload_file="$TMP_ROOT/payload.json"
cat >"$payload_file" <<'JSON'
{
  "track": {
    "mode": "reuse",
    "trackId": "track_123",
    "title": "缓存测试甲程"
  },
  "exercise": {
    "clientRequestId": "req-cache-1",
    "title": "缓存台账练习",
    "questions": [
      {
        "type": "single_choice",
        "questionContent": "A 是什么？",
        "concept": "Concept A",
        "testableClaim": "能识别 Concept A",
        "bloomLevel": 1,
        "options": [
          {"content": "正确", "isCorrect": true},
          {"content": "错误", "isCorrect": false}
        ]
      }
    ]
  }
}
JSON

"$SCRIPT" ledger-start "$payload_file" "$source_fingerprint" >/dev/null
assert_file_exists "$PRACMO_CREATE_CACHE_DIR/payloads/req-cache-1.json"
pending_json="$("$SCRIPT" ledger-lookup req-cache-1)"
assert_eq "pending" "$(jq -r '.status' <<<"$pending_json")" "ledger-start records pending status"
assert_eq "$source_fingerprint" "$(jq -r '.sourceFingerprint' <<<"$pending_json")" "ledger stores source fingerprint"

response_file="$TMP_ROOT/response.json"
cat >"$response_file" <<'JSON'
{
  "success": true,
  "data": {
    "trackId": "track_123",
    "trackTitle": "缓存测试甲程",
    "exerciseId": "flow_456",
    "nodeId": "node_456",
    "exerciseTitle": "缓存台账练习",
    "questionCount": 1,
    "shareUrl": "https://u.zendong.com.cn/s/demo",
    "shortShareUrl": "https://u.zendong.com.cn/s/demo",
    "reusedExisting": false
  }
}
JSON

"$SCRIPT" ledger-success req-cache-1 "$response_file" >/dev/null
succeeded_json="$("$SCRIPT" ledger-lookup req-cache-1)"
assert_eq "succeeded" "$(jq -r '.status' <<<"$succeeded_json")" "ledger-success records succeeded status"
assert_eq "flow_456" "$(jq -r '.result.exerciseId' <<<"$succeeded_json")" "ledger-success stores exercise id"
assert_eq "1" "$(jq -r '.result.questionCount' <<<"$succeeded_json")" "ledger-success stores question count"

payload_changed="$TMP_ROOT/payload-changed.json"
jq '.exercise.title = "缓存台账练习 - 修改后"' "$payload_file" >"$payload_changed"
hash_mismatch_stdout="$TMP_ROOT/hash-mismatch.out"
hash_mismatch_stderr="$TMP_ROOT/hash-mismatch.err"
if "$SCRIPT" ledger-start "$payload_changed" "$source_fingerprint" >"$hash_mismatch_stdout" 2>"$hash_mismatch_stderr"; then
  fail "ledger-start should reject a changed payload for an existing clientRequestId"
fi
rg -q "payload hash mismatch" "$hash_mismatch_stderr" || fail "payload hash mismatch error was not reported"

payload_uncertain="$TMP_ROOT/payload-uncertain.json"
jq '.exercise.clientRequestId = "req-cache-uncertain"' "$payload_file" >"$payload_uncertain"
"$SCRIPT" ledger-start "$payload_uncertain" "$source_fingerprint" >/dev/null
"$SCRIPT" ledger-uncertain req-cache-uncertain "curl timeout" >/dev/null
uncertain_json="$("$SCRIPT" ledger-lookup req-cache-uncertain)"
assert_eq "uncertain" "$(jq -r '.status' <<<"$uncertain_json")" "ledger-uncertain records uncertain status"
assert_eq "curl timeout" "$(jq -r '.errorReason' <<<"$uncertain_json")" "ledger-uncertain stores reason"

echo "pracmo-cache tests passed"
