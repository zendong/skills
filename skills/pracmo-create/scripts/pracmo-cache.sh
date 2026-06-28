#!/usr/bin/env bash
set -euo pipefail

DEFAULT_API_BASE="https://apis.zendong.com.cn/open/v1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
DEFAULT_CACHE_DIR="$SKILL_DIR/cache"

usage() {
  cat <<'EOF'
Usage:
  pracmo-cache.sh cache-dir
  pracmo-cache.sh fingerprint-file <path>
  pracmo-cache.sh fingerprint-url <url>
  pracmo-cache.sh fingerprint-text <text>
  pracmo-cache.sh lookup-source <sourceFingerprint>
  pracmo-cache.sh record-source <json-file|->
  pracmo-cache.sh ledger-start <payload-json-file> [sourceFingerprint]
  pracmo-cache.sh ledger-success <clientRequestId> <response-json-file|->
  pracmo-cache.sh ledger-uncertain <clientRequestId> [reason]
  pracmo-cache.sh ledger-lookup <clientRequestId>

Environment:
  PRACMO_CREATE_CACHE_DIR     Override cache directory. Defaults to skill-local cache/.
  PRACMO_CACHE_ACCOUNT_SCOPE  Optional test/automation override for account scope.

The cache stores only source->track mappings, creation ledger entries, and
payload copies. It never stores API keys, full source materials, mastery
snapshots, answer history, or SRS state.
EOF
}

die() {
  echo "pracmo-cache: $*" >&2
  exit 1
}

need_jq() {
  command -v jq >/dev/null 2>&1 || die "jq is required"
}

sha_string() {
  printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
}

sha_file() {
  shasum -a 256 "$1" | awk '{print $1}'
}

now_iso() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

cache_dir() {
  if [[ -n "${PRACMO_CREATE_CACHE_DIR:-}" ]]; then
    printf '%s\n' "$PRACMO_CREATE_CACHE_DIR"
    return
  fi
  printf '%s\n' "$DEFAULT_CACHE_DIR"
}

ensure_cache_dir() {
  local dir
  dir="$(cache_dir)"
  mkdir -p "$dir/payloads"
  if [[ "$dir" == "$DEFAULT_CACHE_DIR" && ! -f "$dir/.gitignore" ]]; then
    printf '*\n!.gitignore\n' >"$dir/.gitignore"
  fi
}

source_map_path() {
  printf '%s/source-track-map.jsonl\n' "$(cache_dir)"
}

ledger_path() {
  printf '%s/creation-ledger.jsonl\n' "$(cache_dir)"
}

payloads_dir() {
  printf '%s/payloads\n' "$(cache_dir)"
}

api_base() {
  printf '%s\n' "$DEFAULT_API_BASE"
}

account_scope() {
  if [[ -n "${PRACMO_CACHE_ACCOUNT_SCOPE:-}" ]]; then
    printf '%s\n' "$PRACMO_CACHE_ACCOUNT_SCOPE"
    return
  fi
  if [[ -n "${PRACMO_APIKEY:-}" ]]; then
    local digest
    digest="$(sha_string "$PRACMO_APIKEY")"
    printf 'api-key-%s\n' "${digest:0:16}"
    return
  fi
  printf 'no-api-key\n'
}

sanitize_client_request_id() {
  printf '%s' "$1" | LC_ALL=C tr -c 'A-Za-z0-9._-' '_'
}

input_to_temp_file() {
  local input="$1"
  local tmp
  tmp="$(mktemp)"
  if [[ "$input" == "-" ]]; then
    cat >"$tmp"
  else
    [[ -f "$input" ]] || die "file not found: $input"
    cp "$input" "$tmp"
  fi
  printf '%s\n' "$tmp"
}

latest_source_mapping() {
  local fingerprint="$1"
  local file
  file="$(source_map_path)"
  [[ -s "$file" ]] || return 1

  jq -s -c \
    --arg accountScope "$(account_scope)" \
    --arg apiBase "$(api_base)" \
    --arg fingerprint "$fingerprint" \
    'map(select(
      .cacheType == "source_track_mapping"
      and .accountScope == $accountScope
      and .apiBase == $apiBase
      and .source.fingerprint == $fingerprint
    )) | last // empty' "$file" | {
      local output
      output="$(cat)"
      [[ -n "$output" ]] || return 1
      printf '%s\n' "$output"
    }
}

latest_ledger_entry() {
  local client_request_id="$1"
  local file
  file="$(ledger_path)"
  [[ -s "$file" ]] || return 1

  jq -s -c \
    --arg accountScope "$(account_scope)" \
    --arg apiBase "$(api_base)" \
    --arg clientRequestId "$client_request_id" \
    'map(select(
      .cacheType == "creation_ledger"
      and .accountScope == $accountScope
      and .apiBase == $apiBase
      and .clientRequestId == $clientRequestId
    )) | last // empty' "$file" | {
      local output
      output="$(cat)"
      [[ -n "$output" ]] || return 1
      printf '%s\n' "$output"
    }
}

append_jsonl() {
  local file="$1"
  local json="$2"
  printf '%s\n' "$json" >>"$file"
}

command_cache_dir() {
  ensure_cache_dir
  cache_dir
}

command_fingerprint_file() {
  need_jq
  [[ $# -eq 1 ]] || die "fingerprint-file requires <path>"
  local file="$1"
  [[ -f "$file" ]] || die "file not found: $file"

  local dir base abs digest
  dir="$(cd "$(dirname "$file")" && pwd -P)"
  base="$(basename "$file")"
  abs="$dir/$base"
  digest="$(sha_file "$abs")"

  jq -n -c \
    --arg kind "file" \
    --arg uri "$abs" \
    --arg displayName "$base" \
    --arg fingerprint "sha256:$digest" \
    '{kind: $kind, uri: $uri, fingerprint: $fingerprint, displayName: $displayName}'
}

command_fingerprint_url() {
  need_jq
  [[ $# -eq 1 ]] || die "fingerprint-url requires <url>"
  local url="$1"
  local normalized digest
  normalized="${url%%#*}"
  while [[ "$normalized" != "/" && "$normalized" == */ ]]; do
    normalized="${normalized%/}"
  done
  digest="$(sha_string "$normalized")"

  jq -n -c \
    --arg kind "url" \
    --arg uri "$normalized" \
    --arg displayName "$normalized" \
    --arg fingerprint "sha256:$digest" \
    '{kind: $kind, uri: $uri, fingerprint: $fingerprint, displayName: $displayName}'
}

command_fingerprint_text() {
  need_jq
  [[ $# -ge 1 ]] || die "fingerprint-text requires <text>"
  local text normalized digest display_name
  text="$*"
  normalized="$(printf '%s' "$text" | tr '\r\n\t' '   ' | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//')"
  digest="$(sha_string "$normalized")"
  display_name="${normalized:0:60}"
  [[ -n "$display_name" ]] || display_name="text"

  jq -n -c \
    --arg kind "text" \
    --arg uri "text:$digest" \
    --arg displayName "$display_name" \
    --arg fingerprint "sha256:$digest" \
    '{kind: $kind, uri: $uri, fingerprint: $fingerprint, displayName: $displayName}'
}

command_lookup_source() {
  need_jq
  ensure_cache_dir
  [[ $# -eq 1 ]] || die "lookup-source requires <sourceFingerprint>"
  latest_source_mapping "$1"
}

command_record_source() {
  need_jq
  ensure_cache_dir
  [[ $# -eq 1 ]] || die "record-source requires <json-file|->"

  local tmp now json
  tmp="$(input_to_temp_file "$1")"
  now="$(now_iso)"

  jq -e '.source.fingerprint and .track.trackId and .track.title' "$tmp" >/dev/null \
    || die "source mapping requires source.fingerprint, track.trackId and track.title"

  json="$(jq -c \
    --arg accountScope "$(account_scope)" \
    --arg apiBase "$(api_base)" \
    --arg now "$now" \
    '.schemaVersion = (.schemaVersion // 1)
     | .cacheType = "source_track_mapping"
     | .accountScope = $accountScope
     | .apiBase = $apiBase
     | .createdAt = (.createdAt // $now)
     | .updatedAt = $now' "$tmp")"
  append_jsonl "$(source_map_path)" "$json"
  rm -f "$tmp"
  printf '%s\n' "$json"
}

extract_payload_field() {
  local filter="$1"
  local file="$2"
  jq -r "$filter // empty" "$file"
}

command_ledger_start() {
  need_jq
  ensure_cache_dir
  [[ $# -eq 1 || $# -eq 2 ]] || die "ledger-start requires <payload-json-file> [sourceFingerprint]"

  local payload="$1"
  local source_fingerprint="${2:-}"
  [[ -f "$payload" ]] || die "payload file not found: $payload"

  local client_request_id track_mode track_id track_title exercise_title payload_hash existing existing_hash safe_id payload_path now json
  client_request_id="$(extract_payload_field '.exercise.clientRequestId' "$payload")"
  [[ -n "$client_request_id" ]] || die "payload missing exercise.clientRequestId"

  payload_hash="sha256:$(sha_file "$payload")"
  if existing="$(latest_ledger_entry "$client_request_id" 2>/dev/null)"; then
    existing_hash="$(jq -r '.payloadHash // empty' <<<"$existing")"
    if [[ -n "$existing_hash" && "$existing_hash" != "$payload_hash" ]]; then
      die "payload hash mismatch for existing clientRequestId: $client_request_id"
    fi
  fi

  safe_id="$(sanitize_client_request_id "$client_request_id")"
  payload_path="$(payloads_dir)/$safe_id.json"
  cp "$payload" "$payload_path"

  track_mode="$(extract_payload_field '.track.mode' "$payload")"
  track_id="$(extract_payload_field '.track.trackId' "$payload")"
  track_title="$(extract_payload_field '.track.title' "$payload")"
  exercise_title="$(extract_payload_field '.exercise.title' "$payload")"
  now="$(now_iso)"

  json="$(jq -n -c \
    --arg accountScope "$(account_scope)" \
    --arg apiBase "$(api_base)" \
    --arg clientRequestId "$client_request_id" \
    --arg sourceFingerprint "$source_fingerprint" \
    --arg trackMode "$track_mode" \
    --arg trackId "$track_id" \
    --arg trackTitle "$track_title" \
    --arg exerciseTitle "$exercise_title" \
    --arg payloadPath "$payload_path" \
    --arg payloadHash "$payload_hash" \
    --arg now "$now" \
    'def optional($value): if $value == "" then null else $value end;
    {
      schemaVersion: 1,
      cacheType: "creation_ledger",
      accountScope: $accountScope,
      apiBase: $apiBase,
      clientRequestId: $clientRequestId,
      sourceFingerprint: optional($sourceFingerprint),
      trackMode: optional($trackMode),
      trackId: optional($trackId),
      trackTitle: optional($trackTitle),
      exerciseTitle: optional($exerciseTitle),
      payloadPath: $payloadPath,
      payloadHash: $payloadHash,
      status: "pending",
      result: null,
      createdAt: $now,
      updatedAt: $now
    }
    | with_entries(select(.value != null))')"
  append_jsonl "$(ledger_path)" "$json"
  printf '%s\n' "$json"
}

command_ledger_success() {
  need_jq
  ensure_cache_dir
  [[ $# -eq 2 ]] || die "ledger-success requires <clientRequestId> <response-json-file|->"

  local client_request_id="$1"
  local tmp existing now json
  tmp="$(input_to_temp_file "$2")"
  if ! existing="$(latest_ledger_entry "$client_request_id" 2>/dev/null)"; then
    existing="{}"
  fi
  now="$(now_iso)"

  json="$(jq -n -c \
    --argjson existing "$existing" \
    --slurpfile response "$tmp" \
    --arg accountScope "$(account_scope)" \
    --arg apiBase "$(api_base)" \
    --arg clientRequestId "$client_request_id" \
    --arg now "$now" \
    '
      ($response[0].data // $response[0]) as $data
      | $existing
      | .schemaVersion = 1
      | .cacheType = "creation_ledger"
      | .accountScope = $accountScope
      | .apiBase = $apiBase
      | .clientRequestId = $clientRequestId
      | .trackId = (.trackId // $data.trackId // null)
      | .trackTitle = (.trackTitle // $data.trackTitle // null)
      | .exerciseTitle = (.exerciseTitle // $data.exerciseTitle // null)
      | .status = "succeeded"
      | .result = {
          trackId: ($data.trackId // null),
          trackTitle: ($data.trackTitle // null),
          exerciseId: ($data.exerciseId // null),
          nodeId: ($data.nodeId // null),
          exerciseTitle: ($data.exerciseTitle // null),
          questionCount: ($data.questionCount // null),
          shareUrl: ($data.shareUrl // null),
          shortShareUrl: ($data.shortShareUrl // null),
          shareToken: ($data.shareToken // null),
          reusedExisting: (if $data | has("reusedExisting") then $data.reusedExisting else null end)
        }
      | .result |= with_entries(select(.value != null))
      | .createdAt = (.createdAt // $now)
      | .updatedAt = $now
    ')"
  append_jsonl "$(ledger_path)" "$json"
  rm -f "$tmp"
  printf '%s\n' "$json"
}

command_ledger_uncertain() {
  need_jq
  ensure_cache_dir
  [[ $# -eq 1 || $# -eq 2 ]] || die "ledger-uncertain requires <clientRequestId> [reason]"

  local client_request_id="$1"
  local reason="${2:-uncertain submission result}"
  local existing now json
  if ! existing="$(latest_ledger_entry "$client_request_id" 2>/dev/null)"; then
    existing="{}"
  fi
  now="$(now_iso)"

  json="$(jq -n -c \
    --argjson existing "$existing" \
    --arg accountScope "$(account_scope)" \
    --arg apiBase "$(api_base)" \
    --arg clientRequestId "$client_request_id" \
    --arg reason "$reason" \
    --arg now "$now" \
    '$existing
     | .schemaVersion = 1
     | .cacheType = "creation_ledger"
     | .accountScope = $accountScope
     | .apiBase = $apiBase
     | .clientRequestId = $clientRequestId
     | .status = "uncertain"
     | .errorReason = $reason
     | .createdAt = (.createdAt // $now)
     | .updatedAt = $now')"
  append_jsonl "$(ledger_path)" "$json"
  printf '%s\n' "$json"
}

command_ledger_lookup() {
  need_jq
  ensure_cache_dir
  [[ $# -eq 1 ]] || die "ledger-lookup requires <clientRequestId>"
  latest_ledger_entry "$1"
}

main() {
  [[ $# -gt 0 ]] || {
    usage
    exit 2
  }
  local command="$1"
  shift

  case "$command" in
    cache-dir) command_cache_dir "$@" ;;
    fingerprint-file) command_fingerprint_file "$@" ;;
    fingerprint-url) command_fingerprint_url "$@" ;;
    fingerprint-text) command_fingerprint_text "$@" ;;
    lookup-source) command_lookup_source "$@" ;;
    record-source) command_record_source "$@" ;;
    ledger-start) command_ledger_start "$@" ;;
    ledger-success) command_ledger_success "$@" ;;
    ledger-uncertain) command_ledger_uncertain "$@" ;;
    ledger-lookup) command_ledger_lookup "$@" ;;
    -h|--help|help) usage ;;
    *) usage >&2; die "unknown command: $command" ;;
  esac
}

main "$@"
