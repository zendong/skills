#!/usr/bin/env bash
# Upload a local material/practice asset file to the account-scoped Pracmo OSS prefix.
#
# Requirements:
#   - PRACMO_APIKEY
#   - curl, jq
#   - ossutil or ossutil64 available on PATH, or OSSUTIL_BIN=/path/to/ossutil

set -euo pipefail

BASE_URL="https://apis.zendong.com.cn/open/v1"
CATEGORY="practice-assets"
OBJECT_KEY=""
CONTENT_TYPE=""
MAX_SOURCE_BYTES=$((1024 * 1024))
MAX_ASSET_BYTES=$((10 * 1024 * 1024))

die() { echo "pracmo-oss-upload: $*" >&2; exit 1; }

usage() {
  cat <<'EOF'
璞奇 OSS 上传工具（pracmo-create 配套）

用法:
  export PRACMO_APIKEY="..."
  pracmo-oss-upload.sh [选项] <local-file>

选项:
  --category <source|practice-assets|bilibili-cover|material>
      默认 practice-assets。source 用于资料原文件；practice-assets 用于题干/选项/解析图片。
  --object-key <key>
      可选。必须位于服务端返回的 material/{accountId}/ 前缀下。
  --content-type <mime>
      可选。不传时用 file --mime-type 推断，仍为空则使用 application/octet-stream。
  -h, --help

输出:
  JSON: {"objectKey":"...","url":"https://...","contentType":"...","sizeBytes":123}

示例:
  pracmo-oss-upload.sh --category source ./notes.pdf
  pracmo-oss-upload.sh --category practice-assets --content-type image/png ./diagram.png
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

sanitize_name() {
  basename "$1" | tr -cs 'A-Za-z0-9._-' '-' | sed 's/^-//; s/-$//'
}

category_json_key() {
  case "$1" in
    source) echo "source" ;;
    practice-assets) echo "practiceAssets" ;;
    bilibili-cover) echo "bilibiliCover" ;;
    material) echo "material" ;;
    *) die "未知 category: $1" ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --category)
      [[ $# -ge 2 ]] || die "--category 缺少值"
      CATEGORY="$2"
      shift 2
      ;;
    --object-key)
      [[ $# -ge 2 ]] || die "--object-key 缺少值"
      OBJECT_KEY="$2"
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

require_tools

size_bytes="$(stat_size "$LOCAL_FILE")"
[[ "$size_bytes" =~ ^[0-9]+$ && "$size_bytes" -gt 0 ]] || die "文件为空或无法读取大小"
if [[ "$CATEGORY" == "source" && "$size_bytes" -gt "$MAX_SOURCE_BYTES" ]]; then
  die "source 资料原文件超过 1MB，当前后端 material 登记会拒绝该 sizeBytes"
fi
if [[ "$CATEGORY" != "source" && "$size_bytes" -gt "$MAX_ASSET_BYTES" ]]; then
  die "图片/练习资产超过 10MB"
fi

content_type="$(detect_content_type "$LOCAL_FILE" | head -n1)"
content_type="${content_type:-application/octet-stream}"

config_json="$(api_get "oss/config")"
sts_json="$(api_get "oss/stsToken")"

bucket="$(echo "$config_json" | jq -r '.data.bucketName // .bucketName // empty')"
endpoint="$(echo "$config_json" | jq -r '.data.ossEndpoint // .ossEndpoint // empty')"
material_prefix="$(echo "$config_json" | jq -r '.data.objectKeyPrefix // .objectKeyPrefix // empty')"
prefix_key="$(category_json_key "$CATEGORY")"
category_prefix="$(echo "$config_json" | jq -r --arg k "$prefix_key" '.data.objectKeyPrefixes[$k] // .objectKeyPrefixes[$k] // empty')"
[[ -n "$bucket" && -n "$endpoint" ]] || die "OSS config 缺少 bucketName/ossEndpoint"
[[ -n "$material_prefix" ]] || die "OSS config 缺少 objectKeyPrefix，请确认 server 已更新"
[[ -n "$category_prefix" ]] || category_prefix="$material_prefix"

if [[ -z "$OBJECT_KEY" ]]; then
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  name="$(sanitize_name "$LOCAL_FILE")"
  [[ -n "$name" ]] || name="upload.bin"
  OBJECT_KEY="${category_prefix}${stamp}-${name}"
fi

case "$OBJECT_KEY" in
  "$material_prefix"*) ;;
  *) die "object key 必须位于账号 material 前缀下: $material_prefix" ;;
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
