#!/usr/bin/env bash
# Upload a local practice asset file to the account-scoped Pracmo OSS prefix.
#
# Requirements:
#   - PRACMO_APIKEY
#   - curl, jq
#   - ossutil 1.x or ossutil64 1.x available on PATH, or OSSUTIL_BIN=/path/to/ossutil

set -euo pipefail

BASE_URL="${PRACMO_OPEN_API_BASE:-https://apis.zendong.com.cn/open/v1}"
OBJECT_KEY=""
CONTENT_TYPE=""
CATEGORY="learning-track-assets"
REQUEST_ID=""
MAX_ASSET_BYTES=$((512 * 1024))

die() { echo "pracmo-oss-upload: $*" >&2; exit 1; }

usage() {
  cat <<'EOF'
璞奇 OSS 上传工具（pracmo-create 配套）

用法:
  export PRACMO_APIKEY="..."
  pracmo-oss-upload.sh [选项] <local-file>

依赖:
  - curl、jq
  - ossutil 1.x 或 ossutil64 1.x；如果不在 PATH，设置 OSSUTIL_BIN=/path/to/ossutil
  - 不要使用 ossutil 2.x；当前脚本使用 1.x 参数，2.x 会出现参数不兼容

选项:
  --category <learning-track-assets>
      私人甲程封面、题目与行动内容图片。所有图片上传前必须压缩到 512KB 以下。
  --object-key <key>
      可选。必须位于服务端返回的账号 OSS 前缀下。
  --request-id <clientRequestId>
      必填（除非显式传 --object-key）。用于隔离到 learning-track-assets/<clientRequestId>/。
  --content-type <mime>
      可选。不传时用 file --mime-type 推断，仍为空则使用 application/octet-stream。
  -h, --help

输出:
  JSON: {"objectKey":"...","url":"https://...","contentType":"...","sizeBytes":123}

示例:
  pracmo-oss-upload.sh --category learning-track-assets --content-type image/png ./diagram.png
  pracmo-oss-upload.sh --category learning-track-assets --content-type image/jpeg ./diagram.jpg
EOF
}

require_tools() {
  [[ -n "${PRACMO_APIKEY:-}" ]] || die "未设置 PRACMO_APIKEY"
  command -v curl >/dev/null 2>&1 || die "缺少 curl"
  command -v jq >/dev/null 2>&1 || die "缺少 jq"
  if [[ -z "${OSSUTIL_BIN:-}" ]]; then
    OSSUTIL_BIN="$(command -v ossutil || command -v ossutil64 || true)"
  fi
  [[ -n "${OSSUTIL_BIN:-}" && -x "$OSSUTIL_BIN" ]] || die "缺少 ossutil/ossutil64，可设置 OSSUTIL_BIN"
}

api_get() {
  local path="$1"
  local out code
  out=$(curl -sS -w "\n%{http_code}" -X GET \
    -H "X-API-Key: ${PRACMO_APIKEY}" \
    -H "Accept: application/json" \
    "${BASE_URL}/${path#\/}") || die "curl 失败: $path"
  code=$(echo "$out" | tail -n1)
  out=$(echo "$out" | sed '$d')
  [[ "$code" =~ ^2 ]] || die "HTTP $code: $out"
  echo "$out"
}

stat_size() {
  if stat -f%z "$1" >/dev/null 2>&1; then
    stat -f%z "$1"
  else
    stat -c%s "$1"
  fi
}

detect_content_type() {
  local file="$1"
  if [[ -n "$CONTENT_TYPE" ]]; then
    echo "$CONTENT_TYPE"
    return
  fi
  if command -v file >/dev/null 2>&1; then
    file --brief --mime-type "$file" 2>/dev/null || true
    return
  fi
  echo "application/octet-stream"
}

validate_practice_asset_format() {
  local file="$1"
  local content_type="$2"
  local lower_name
  lower_name="$(basename "$file" | tr '[:upper:]' '[:lower:]')"

  case "$lower_name" in
    *.svg|*.svgz)
      die "练习图片只支持 PNG/JPG；请先把 SVG 转成 PNG 或 JPG 后再上传"
      ;;
  esac

  case "$content_type" in
    image/png|image/jpeg|image/jpg)
      ;;
    image/webp) ;;
    *)
      die "练习图片只支持 PNG/JPG；当前类型为 ${content_type:-unknown}"
      ;;
  esac
}

sanitize_name() {
  basename "$1" | tr -cs 'A-Za-z0-9._-' '-' | sed 's/^-//; s/-$//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --category)
      [[ $# -ge 2 ]] || die "--category 缺少值"
	  [[ "$2" == "learning-track-assets" ]] || die "只支持 learning-track-assets 分类"
	  CATEGORY="$2"
      shift 2
      ;;
    --object-key)
      [[ $# -ge 2 ]] || die "--object-key 缺少值"
      OBJECT_KEY="$2"
      shift 2
      ;;
    --request-id)
      [[ $# -ge 2 ]] || die "--request-id 缺少值"
      REQUEST_ID="$2"
      [[ "$REQUEST_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$ ]] || die "--request-id 格式无效"
      shift 2
      ;;
    --content-type)
      [[ $# -ge 2 ]] || die "--content-type 缺少值"
      CONTENT_TYPE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      die "未知选项: $1"
      ;;
    *)
      [[ -z "${LOCAL_FILE:-}" ]] || die "只能上传一个文件"
      LOCAL_FILE="$1"
      shift
      ;;
  esac
done

[[ -n "${LOCAL_FILE:-}" ]] || { usage >&2; exit 1; }
[[ -f "$LOCAL_FILE" ]] || die "文件不存在: $LOCAL_FILE"

size_bytes="$(stat_size "$LOCAL_FILE")"
[[ "$size_bytes" =~ ^[0-9]+$ && "$size_bytes" -gt 0 ]] || die "文件为空或无法读取大小"
if [[ "$size_bytes" -gt "$MAX_ASSET_BYTES" ]]; then
  die "甲程图片超过 512KB；请先压缩后再上传"
fi

content_type="$(detect_content_type "$LOCAL_FILE" | head -n1)"
content_type="${content_type:-application/octet-stream}"
if [[ "$content_type" == "image/jpg" ]]; then
  content_type="image/jpeg"
fi
validate_practice_asset_format "$LOCAL_FILE" "$content_type"

require_tools

config_json="$(api_get "oss/config")"
sts_json="$(api_get "oss/stsToken")"

bucket="$(echo "$config_json" | jq -r '.data.bucketName // .bucketName // empty')"
endpoint="$(echo "$config_json" | jq -r '.data.ossEndpoint // .ossEndpoint // empty')"
account_prefix="$(echo "$config_json" | jq -r '.data.objectKeyPrefix // .objectKeyPrefix // empty')"
category_prefix="$(echo "$config_json" | jq -r '.data.objectKeyPrefixes.learningTrackAssets // .objectKeyPrefixes.learningTrackAssets // empty')"
[[ -n "$bucket" && -n "$endpoint" ]] || die "OSS config 缺少 bucketName/ossEndpoint"
[[ -n "$account_prefix" ]] || die "OSS config 缺少 objectKeyPrefix，请确认 server 已更新"
[[ -n "$category_prefix" ]] || die "OSS config 缺少 ${CATEGORY} object key prefix，请确认 server 已更新"

if [[ -z "$OBJECT_KEY" ]]; then
  [[ -n "$REQUEST_ID" ]] || die "必须提供 --request-id 或 --object-key"
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  name="$(sanitize_name "$LOCAL_FILE")"
  [[ -n "$name" ]] || name="upload.bin"
  OBJECT_KEY="${category_prefix}${REQUEST_ID}/${stamp}-${name}"
fi

case "$OBJECT_KEY" in
  "$account_prefix"*) ;;
  *) die "object key 必须位于账号 OSS 前缀下: $account_prefix" ;;
esac
[[ "$OBJECT_KEY" != /* && "$OBJECT_KEY" != *".."* ]] || die "object key 不能包含绝对路径或 .."

ak_id="$(echo "$sts_json" | jq -r '.AccessKeyId // .accessKeyId // empty')"
ak_secret="$(echo "$sts_json" | jq -r '.AccessKeySecret // .accessKeySecret // empty')"
token="$(echo "$sts_json" | jq -r '.SecurityToken // .securityToken // empty')"
[[ -n "$ak_id" && -n "$ak_secret" && -n "$token" ]] || die "STS token 缺少 AccessKeyId/AccessKeySecret/SecurityToken"

"$OSSUTIL_BIN" cp "$LOCAL_FILE" "oss://${bucket}/${OBJECT_KEY}" \
  -e "$endpoint" \
  -i "$ak_id" \
  -k "$ak_secret" \
  -t "$token" \
  --meta "Content-Type:${content_type}" >/dev/null

endpoint_no_scheme="${endpoint#http://}"
endpoint_no_scheme="${endpoint_no_scheme#https://}"
url="https://${bucket}.${endpoint_no_scheme}/${OBJECT_KEY}"

jq -n \
  --arg objectKey "$OBJECT_KEY" \
  --arg url "$url" \
  --arg contentType "$content_type" \
  --argjson sizeBytes "$size_bytes" \
  '{objectKey:$objectKey,url:$url,contentType:$contentType,sizeBytes:$sizeBytes}'
