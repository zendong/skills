# 俯卧撑十式公开 Action：本地全链路操作指南

本目录已经完成实际闭环验证：旧版 `follow-plan.md` 的内容已人工迁移为标准 `pracmo-public-action@v1` JSON；原始 PNG 已在上传前压缩，图片已由服务端固化，压缩版投稿已经审核发布。首版未压缩 Public Action 已下线，之前导入本地甲程的 Action 保持不变。

## 文件职责

- `follow-plan.md`：迁移前的旧版 Markdown，只保留为内容来源。
- `public-action.json`：JSON-first 的可编辑源文件，也是后续修订的唯一事实来源。
- `public-action.md`：由 JSON 确定性导出的审阅文件，不可反向解析后投稿。
- `images/`：原始 PNG，仅用于保留源素材，不直接上传。
- `assets/`：压缩后的上传资产；本例最大图片为 193,970 字节。
- `public-action.finalized.json`：当前已发布版本的远程资产快照，用于核验，不作为原投稿的幂等重试文件。
- `public-action.v1-uncompressed.finalized.json`：已下线首版的历史快照。
- `submission-ledger.jsonl`：本地投稿与恢复账本。
- `submission-result.json`：最近一次服务端投稿结果。

所有命令从 `evertrain/` 工作区根目录执行。不要把真实 API Key 写进仓库。

## 1. 启动本地服务

本地 MySQL 必须已经包含 Public Action P0 DDL，server 必须包含 Open Public Action 使用 API Key 解析账号的修复。

```bash
cd shixizhi-server
make run
```

服务地址为 `http://127.0.0.1:8081`。

## 2. 配置发布环境

发布图片需要 `jq` 和 `ossutil 1.x`。当前上传脚本不兼容 `ossutil 2.x`。

```bash
export PRACMO_APIKEY='在本地设置，不要提交'
export PRACMO_OPEN_API_BASE='http://127.0.0.1:8081/open/v1'
export OSSUTIL_BIN='/path/to/ossutil-v1.7.19'
```

## 3. 上传前压缩、校验 JSON 与导出 Markdown

```bash
ACTION_DIR='public-skills/skills/pracmo-follow-plan-markdown/output/convict-conditioning-pushups'
SKILL_DIR='public-skills/skills/pracmo-follow-plan-markdown'

python3 "$SKILL_DIR/scripts/compress_public_action_images.py" \
  "$ACTION_DIR/public-action.json" \
  -o "$ACTION_DIR/public-action.json" \
  --assets-dir assets

python3 "$SKILL_DIR/scripts/validate_public_action_json.py" \
  "$ACTION_DIR/public-action.json" \
  --check-assets --json

python3 "$SKILL_DIR/scripts/public_action_json_to_markdown.py" \
  "$ACTION_DIR/public-action.json" \
  -o "$ACTION_DIR/public-action.md"
```

压缩脚本会保留原始 `images/`，把投稿 JSON 的 `localPath` 改为 `assets/*.jpg`。校验器和 OSS 上传器都会在发生网络上传前再次拒绝超过 512 KiB 的公开 Action 图片。

## 4. 上传并固化图片

首次投稿前应显式保存 finalized JSON，避免同一投稿重试时重新上传 11 个图片资产。生成后不要重复执行本步骤；应复用同一个 finalized 文件和 `clientRequestId`：

```bash
python3 "$SKILL_DIR/scripts/finalize_public_action_assets.py" \
  "$ACTION_DIR/public-action.json" \
  -o "$ACTION_DIR/public-action.finalized.json"
```

服务端投稿时会再次读取 OSS 对象，核验 MIME、大小、图片尺寸和 SHA-256，并复制到受管理的 `public-action/<publicActionId>/cover|content/` 目录。

## 5. 投稿与幂等重试

```bash
python3 "$SKILL_DIR/scripts/publish_public_action.py" \
  "$ACTION_DIR/public-action.finalized.json" \
  --ledger "$ACTION_DIR/submission-ledger.jsonl" \
  --output "$ACTION_DIR/submission-result.json"

PUBLIC_ACTION_ID=$(jq -r '.publicActionId' "$ACTION_DIR/submission-result.json")
jq '{publicActionId,status,reviewStatus,reusedExisting}' \
  "$ACTION_DIR/submission-result.json"
```

首次投稿应为 `draft + pending`。再次执行相同命令应返回同一个 `publicActionId`，且 `reusedExisting=true`。

## 6. 本地管理员审核

以下固定验证码仅适用于本地测试环境：

```bash
curl -sS -X POST 'http://127.0.0.1:8081/public/user/login' \
  -H 'Content-Type: application/json' \
  -d '{"phone":"18888888888","code":"1","accountName":"Local E2E"}' \
  -o /tmp/pracmo-local-login.json

ACCOUNT_TOKEN=$(jq -r '.data.token' /tmp/pracmo-local-login.json)

curl -sS -X POST \
  "http://127.0.0.1:8081/system/actions/public/${PUBLIC_ACTION_ID}/approve" \
  -H "x-account-token: ${ACCOUNT_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"reason":"local end-to-end verification passed","expectedStatus":"draft","expectedReviewStatus":"pending"}' \
  | jq '{success,data:{publicActionId:.data.publicActionId,status:.data.status,reviewStatus:.data.reviewStatus}}'
```

测试账号必须位于本地 `AdminConfig` 白名单中。审核成功后状态为 `published + approved`。

## 7. 验证发现目录

```bash
curl -sS \
  'http://127.0.0.1:8081/client/v1/public-actions?keyword=%E4%BF%AF%E5%8D%A7%E6%92%91&category=fitness&sort=newest&limit=20&offset=0' \
  -H "x-account-token: ${ACCOUNT_TOKEN}" \
  | jq --arg id "$PUBLIC_ACTION_ID" \
    '.data.items[] | select(.publicActionId==$id) | {publicActionId,title,coverImageUrl,actionType,planSummary}'
```

## 8. 创建目标甲程并导入

```bash
curl -sS -X POST 'http://127.0.0.1:8081/client/v1/learning-tracks' \
  -H "x-account-token: ${ACCOUNT_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "{\"title\":\"囚徒健身六艺（本地闭环验证）\",\"description\":\"公开行动全链路验证\",\"category\":\"fitness\",\"originType\":\"public_action_e2e\",\"originRefId\":\"${PUBLIC_ACTION_ID}\"}" \
  -o /tmp/pracmo-local-track-created.json

TRACK_ID=$(jq -r '.data.trackId' /tmp/pracmo-local-track-created.json)

curl -sS -X POST \
  "http://127.0.0.1:8081/client/v1/public-actions/${PUBLIC_ACTION_ID}/import" \
  -H "x-account-token: ${ACCOUNT_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "{\"targetTrackId\":\"${TRACK_ID}\",\"startDate\":\"$(date +%F)\",\"timezone\":\"Asia/Shanghai\",\"downgradeRichMedia\":false}" \
  -o /tmp/pracmo-local-import.json

ACTION_ID=$(jq -r '.data.actionId' /tmp/pracmo-local-import.json)
```

## 9. 验证导入后的跟练数据

```bash
curl -sS \
  "http://127.0.0.1:8081/client/v1/actions/${ACTION_ID}/follow-plan" \
  -H "x-account-token: ${ACCOUNT_TOKEN}" \
  | jq '{
      actionId:.data.actionId,
      levelCount:(.data.levels|length),
      checkpointCount:(.data.checkpoints|length),
      imageBlockCount:([.data.levels[].contentBlocks[]|select(.blockType=="image")]|length),
      firstLevel:.data.levels[0].title,
      lastLevel:.data.levels[-1].title
    }'
```

预期结果：10 个练阶、4 个成就节点、10 个远程图片块，首阶为“墙壁俯卧撑”，末阶为“单臂俯卧撑”。

## 本次闭环结果

- 当前 Public Action：`1s4MAATUY7R4yvNjXSQiQF`
- 已下线未压缩版本：`8vvA8oAOvT3yrfTwjReYW`
- 本地目标甲程：`3Hbg2XAtrchqw4l3os6uXy`
- 导入后的 Action：`5Uu4u1CpAaBYGeoIx7fLTH`
- 状态：`published + approved`
- 公开资产：1 张封面、10 张跟练内容图
- 图片大小：最大 193,970 字节，全部低于 512 KiB
- 发现目录：可检索
- 旧版本：`offline + approved`，发现目录不可见
- 既有导入：继续引用首版固化资产，不受公开版本下线影响
