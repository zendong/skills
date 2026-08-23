#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${PRACMO_OPEN_API_BASE:-https://apis.zendong.com.cn/open/v1}"

die() { echo "pracmo-add-exercise: $*" >&2; exit 1; }
require_key() {
  [[ -n "${PRACMO_APIKEY:-}" ]] || die "未设置 PRACMO_APIKEY。请在本地 export PRACMO_APIKEY=...；不要把 Key 发到聊天里。"
}
emit_response() {
  local response="$1" code="$2"
  echo "$response"
  [[ "$code" =~ ^2 ]] || die "HTTP $code"
  if grep -Eq '"success"[[:space:]]*:[[:space:]]*false' <<<"$response"; then
	return 1
  fi
}
list_tracks() {
  local keyword="${1:-}" response code
  require_key
  response=$(curl -sS -w $'\n%{http_code}' --get \
    -H "X-API-Key: ${PRACMO_APIKEY}" -H "Accept: application/json" \
    --data-urlencode "state=active" --data-urlencode "pageSize=100" \
    --data-urlencode "keyword=${keyword}" "${BASE_URL}/learning-tracks") || die "curl 失败"
  code="${response##*$'\n'}"; response="${response%$'\n'*}"
  emit_response "$response" "$code"
}
add_exercise() {
  local track_id="$1" file="$2" response code
  require_key
  [[ -n "$track_id" ]] || die "trackId 不能为空"
  [[ -f "$file" ]] || die "文件不存在: $file"
  response=$(curl -sS -w $'\n%{http_code}' -X POST \
    -H "X-API-Key: ${PRACMO_APIKEY}" -H "Content-Type: application/json" \
    --data-binary @"$file" "${BASE_URL}/learning-tracks/${track_id}/exercises") || die "curl 失败"
  code="${response##*$'\n'}"; response="${response%$'\n'*}"
  emit_response "$response" "$code"
}

case "${1:-}" in
  list-tracks) shift; list_tracks "${1:-}" ;;
  add-exercise)
    [[ $# -eq 3 ]] || die "用法: $0 add-exercise <trackId> <json-file>"
    add_exercise "$2" "$3"
    ;;
  *) die "用法: $0 list-tracks [keyword] | add-exercise <trackId> <json-file>" ;;
esac
