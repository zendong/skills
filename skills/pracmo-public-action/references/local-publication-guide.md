# 本地与 prepub 公开 Action 投稿指南

本流程以 `public-action.json` 为权威输入，目标服务为 `http://127.0.0.1:8081/open/v1`。投稿只创建 `draft + pending`，不会自动审核或公开。

## 1. 启动并验证服务

```bash
cd /Users/huanxin.shx/go/src/github.com/evertrain/shixizhi-server
make run
```

另开终端设置本地环境。API Key 只放在本机环境变量，不写进 JSON、Markdown、脚本参数或提交台账：

```bash
export PRACMO_APIKEY='<本地测试账号 API Key>'
export PRACMO_OPEN_API_BASE='http://127.0.0.1:8081/open/v1'
```

验证认证与分类配置：

```bash
curl -sS "$PRACMO_OPEN_API_BASE/public-actions/categories" \
  -H "X-API-Key: $PRACMO_APIKEY" \
  -H 'Accept-Language: zh-CN'
```

## 2. 准备、压缩与校验

```bash
cd /Users/huanxin.shx/go/src/github.com/evertrain/public-skills
action_dir='skills/pracmo-public-action/output/<slug>'

python3 skills/pracmo-public-action/scripts/compress_public_action_images.py \
  "$action_dir/public-action.json" \
  -o "$action_dir/public-action.json" \
  --assets-dir assets

python3 skills/pracmo-public-action/scripts/validate_public_action_json.py \
  "$action_dir/public-action.json" --check-assets --json

python3 skills/pracmo-public-action/scripts/public_action_json_to_markdown.py \
  "$action_dir/public-action.json" \
  -o "$action_dir/public-action.md"
```

压缩后每张图片必须不超过 512 KiB。`source-assets/` 只保留原图；实际上传文件位于 `assets/`。

## 3. 一键上传并投稿

```bash
python3 skills/pracmo-public-action/scripts/publish_public_action.py \
  "$action_dir/public-action.json" \
  --finalized-output "$action_dir/public-action.finalized.json" \
  --ledger "$action_dir/submission-ledger.jsonl" \
  --output "$action_dir/submission-result.json"
```

发布器依次执行：本地校验、服务端分类预检、STS 获取、OSS 上传、最终 JSON 固化、v2 投稿、网络不确定状态恢复。Python 环境需要 Pillow 与 `oss2`。

## 4. 查询闭环

```bash
client_request_id=$(python3 -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["clientRequestId"])' \
  "$action_dir/public-action.finalized.json")

curl -sS \
  "$PRACMO_OPEN_API_BASE/public-actions/submissions/$client_request_id" \
  -H "X-API-Key: $PRACMO_APIKEY"
```

成功投稿的普通结果必须是 `status=draft`、`reviewStatus=pending`。同时检查 `publicActionId` 非空、`actionType` 与本地模式一致、所有资产 URL 为 HTTPS、最终 JSON 不含 `localPath`、图片 `sizeBytes <= 524288`。

## 5. 幂等与失败处理

- 原样重试使用同一个 `clientRequestId`，服务端返回已有投稿。
- 内容发生真实修订时才创建新的 `clientRequestId`；不要用旧 ID 覆盖新内容。
- 分类预检、压缩或本地校验失败时不会上传。
- 上传完成但 POST 超时时，先查 submission；台账出现 `uncertain` 不代表失败。
- `LIMIT_EXCEEDED` 表示账号当日 Open API 创建总数达到 10，次日再提交，不绕过配额。
- `draft + pending` 只是待审核，不得描述为“已公开”。

## 6. 将已有 finalized JSON 原样同步到 prepub

适用于本地已经完成 JSON 和图片准备，且用户明确要求“不修改内容，只同步环境”的情况。prepub Open API 基址为：

```bash
export PRACMO_OPEN_API_BASE='https://apis-pre.zendong.com.cn/open/v1'
export PRACMO_APIKEY='<prepub API Key，仅保存在本机环境变量>'
```

不要重新生成或压缩图片，也不要修改 `public-action.json`、模板、分类、Tags、图片字节或 `clientRequestId`。OSS staging 对象键带有账号隔离前缀 `material/<accountId>/action-assets/`：当本地与 prepub 使用不同 API Key 账号时，本地 finalized 对象键不能直接提交到 prepub，必须用原有 authoring JSON 和已经压缩好的 `assets/*` 进行环境上传：

```bash
python3 skills/pracmo-public-action/scripts/publish_public_action.py \
  "$action_dir/public-action.json" \
  --finalized-output "$action_dir/public-action.prepub.finalized.json" \
  --ledger "$action_dir/submission-ledger.prepub.jsonl" \
  --output "$action_dir/submission-result.prepub.json"
```

上述流程上传的是现有压缩图片的相同字节，不会重新生图或修改图片内容；`public-action.prepub.finalized.json` 只固化 prepub 所需的账号级对象键和 URL。只有当两个环境明确使用同一账号 ID 与 managed staging 前缀时，才可以直接以 `public-action.finalized.json` 为输入。

prepub 结果文件必须独立命名，不能覆盖本地的 `submission-result.json` 和 `submission-ledger.jsonl`。服务端会读取 prepub 账号管理前缀下的 OSS 源对象，并复制到 prepub Action 自己的公开对象键；这是服务端固化流程，不是图片编辑。

完成后必须用同一个 `clientRequestId` 查询 prepub：

```bash
curl -sS \
  "$PRACMO_OPEN_API_BASE/public-actions/submissions/$client_request_id" \
  -H "X-API-Key: $PRACMO_APIKEY"
```

以 prepub 查询结果为准，确认 `publicActionId` 非空、`status=draft`、`reviewStatus=pending`、`actionType` 正确且资产 URL 使用 HTTPS；不得拿本地投稿结果代替 prepub 闭环证据。
