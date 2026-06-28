#!/usr/bin/env bash
# 璞奇开放 API 命令行封装（与 pracmo-create skill 对齐）。
# 依赖：curl；可选 jq（用于 --pretty 美化输出）。
#
# 用法：
#   export PRACMO_APIKEY="..."   # 勿将 Key 写入仓库或粘贴到聊天
#   skills/pracmo-create/scripts/pracmo-open-api.sh learning-track-exercise path/to/body.json
#   cat body.json | skills/pracmo-create/scripts/pracmo-open-api.sh learning-track-exercise -
#
#   skills/pracmo-create/scripts/pracmo-open-api.sh get 'learning-tracks?keyword=线性代数'
#   skills/pracmo-create/scripts/pracmo-open-api.sh get 'learning-tracks/track_xxx/timeline?nodeType=exercise&pageSize=20'
#   skills/pracmo-create/scripts/pracmo-open-api.sh get 'learning-tracks/track_xxx/concepts?limit=50'
#   skills/pracmo-create/scripts/pracmo-open-api.sh dismiss-node node_xxx
#
# 子命令：
#   learning-track-exercise <file|-   POST /open/v1/learning-tracks/with-exercise，请求体为 JSON 文件或 stdin（-）
#   get <path>               GET /open/v1/learning-tracks...（仅限甲程相关查询）
#   dismiss-node <nodeId>    POST /open/v1/learning-tracks/nodes/<nodeId>/dismiss
#
# 选项：
#   --pretty    若已安装 jq，则对 JSON 响应格式化（失败时仍输出原文）

set -euo pipefail

BASE_URL="https://apis.zendong.com.cn/open/v1"
PRETTY=0

die() { echo "pracmo-open-api: $*" >&2; exit 1; }

require_key() {
  [[ -n "${PRACMO_APIKEY:-}" ]] || die "未设置 PRACMO_APIKEY。请 export PRACMO_APIKEY=... 后重试（见 https://www.zendong.com.cn/app/api-key ）"
}

curl_json_get() {
  local path="$1"
  require_key
  local url="${BASE_URL}/${path#\/}"
  local out code
  out=$(curl -sS -w "\n%{http_code}" -X GET \
    -H "X-API-Key: ${PRACMO_APIKEY}" \
    -H "Accept: application/json" \
    "$url") || die "curl 失败"
  code=$(echo "$out" | tail -n1)
  out=$(echo "$out" | sed '$d')
  _emit "$out" "$code"
}

validate_get_path() {
  local path="${1#\/}"
  case "$path" in
    learning-tracks|learning-tracks\?*|learning-tracks/*) ;;
    *) die "get 仅支持 learning-tracks 相关查询" ;;
  esac
}

curl_json_post_file() {
  local path="$1"
  local file="$2"
  require_key
  local url="${BASE_URL}/${path#\/}"
  [[ -n "$file" ]] || die "缺少 JSON 文件路径或使用 - 表示 stdin"
  if [[ "$file" == "-" ]]; then
    local out code
    out=$(curl -sS -w "\n%{http_code}" -X POST \
      -H "X-API-Key: ${PRACMO_APIKEY}" \
      -H "Content-Type: application/json" \
      --data-binary @- \
      "$url") || die "curl 失败"
  else
    [[ -f "$file" ]] || die "文件不存在: $file"
    out=$(curl -sS -w "\n%{http_code}" -X POST \
      -H "X-API-Key: ${PRACMO_APIKEY}" \
      -H "Content-Type: application/json" \
      --data-binary @"$file" \
      "$url") || die "curl 失败"
  fi
  code=$(echo "$out" | tail -n1)
  out=$(echo "$out" | sed '$d')
  _emit "$out" "$code"
}

curl_json_post_empty() {
  local path="$1"
  require_key
  local url="${BASE_URL}/${path#\/}"
  local out code
  out=$(curl -sS -w "\n%{http_code}" -X POST \
    -H "X-API-Key: ${PRACMO_APIKEY}" \
    -H "Accept: application/json" \
    "$url") || die "curl 失败"
  code=$(echo "$out" | tail -n1)
  out=$(echo "$out" | sed '$d')
  _emit "$out" "$code"
}

_emit() {
  local body="$1"
  local code="$2"
  if [[ "$PRETTY" -eq 1 ]] && command -v jq >/dev/null 2>&1; then
    echo "$body" | jq . 2>/dev/null || echo "$body"
  else
    echo "$body"
  fi
  if [[ "$code" =~ ^2 ]]; then
    return 0
  fi
  echo "HTTP $code" >&2
  return 1
}

usage() {
  cat <<'EOF'
璞奇开放 API（pracmo-create 配套）

用法:
  export PRACMO_APIKEY="..."
  pracmo-open-api.sh learning-track-exercise <json-file|->
  pracmo-open-api.sh get 'learning-tracks?keyword=线性代数'
  pracmo-open-api.sh get 'learning-tracks/track_xxx/timeline?nodeType=exercise&pageSize=20'
  pracmo-open-api.sh get 'learning-tracks/track_xxx/concepts?limit=50'
  pracmo-open-api.sh dismiss-node node_xxx

选项: --pretty（需 jq）  -h

示例:
  pracmo-open-api.sh learning-track-exercise ./payload.json
  cat payload.json | pracmo-open-api.sh learning-track-exercise -
EOF
}

# 解析前置 --pretty
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pretty) PRETTY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- "${ARGS[@]}"

[[ $# -ge 1 ]] || { usage >&2; exit 1; }

case "$1" in
  learning-track-exercise)
    shift
    [[ $# -ge 1 ]] || die "用法: ... learning-track-exercise <json-file|->"
    curl_json_post_file "learning-tracks/with-exercise" "$1"
    ;;
  get)
    shift
    [[ $# -ge 1 ]] || die "用法: ... get <learning-tracks path>  例如 learning-tracks?keyword=线性代数"
    validate_get_path "$1"
    curl_json_get "$1"
    ;;
  dismiss-node)
    shift
    [[ $# -ge 1 ]] || die "用法: ... dismiss-node <nodeId>"
    node_id="${1#/}"
    [[ -n "$node_id" ]] || die "nodeId 不能为空"
    curl_json_post_empty "learning-tracks/nodes/${node_id}/dismiss"
    ;;
  *)
    die "未知子命令: $1。可用: learning-track-exercise | get | dismiss-node"
    ;;
esac
