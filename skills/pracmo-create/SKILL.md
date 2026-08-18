---
name: pracmo-create
description: "创建用户自己的璞奇甲程。用户说创建甲程、围绕目标规划甲程、把资料做成甲程、生成甲程与练习/行动、只生成甲程骨架时必须使用。先在本地生成 pracmo-learning-track@v1 JSON，可包含 2-8 个目标阶段、0-N 个完整练习和 0-N 个行动；本地审阅通过后，按需压缩并上传图片，再通过 Open API 原子导入 API Key 所属用户的私人甲程。"
---

# Pracmo Create

## 目标

把用户的目标、资料或对话整理成一个可审阅、可重复导入的私人甲程包。JSON 是唯一事实源；不要直接拼多个写接口，也不要回退到旧的即时创建流程。

标准产物：

```text
output/<slug>/
  learning-track.json
  learning-track.review.md
  learning-track.finalized.json
  import-result.json
  import-ledger.jsonl
  source-assets/
  assets/
```

完整字段、题型与行动合同见：

- `references/learning-track-json-contract.md`
- `references/learning-track.schema.json`
- `references/action-contract.md`

## 核心流程

```text
理解目标
  → 生成 learning-track.json
  → 离线校验
  → 导出 Markdown 审阅稿
  → 如有图片，压缩到每张 ≤ 512 KiB
  → 用户要求导入时才检查 PRACMO_APIKEY
  → 获取账号 OSS 前缀与 STS，上传图片
  → 生成 learning-track.finalized.json
  → POST /open/v1/learning-tracks/import
  → 保存 result/ledger；不确定结果先 lookup
```

## 内容决策

1. 新甲程必须有一个明确核心目标，以及 2–8 个有顺序的 State。
2. 第一个 State 是用户当前稳定状态，最后一个 State 是目标状态；每个 State 有 1–5 条可观察 criterion。
3. 练习和行动都允许为 0。用户只要规划时，创建目标/阶段骨架即可。
4. 有练习时，每个练习必须包含完整可作答题目；不得在导入时让 Server 调 LLM 补题。
5. 有行动时，按目标选择：自行完成、`puki_generated` 轻阅读/快问答、或 `follow_along` 跟练计划。
6. Exercise/Action 可关联一个 State 和 criterion，关系仅用 `advance / assess / reinforce`。
7. 私人甲程不持久化公开分类与 tags。`track.category` 只作为创作和默认封面提示，不要向用户声称已写入私人甲程分类。

## 本地生成（不需要 API Key）

先创建 `output/<slug>/learning-track.json`，使用：

```bash
python3 scripts/validate_learning_track_json.py output/<slug>/learning-track.json --authoring
python3 scripts/learning_track_json_to_markdown.py \
  output/<slug>/learning-track.json \
  -o output/<slug>/learning-track.review.md
```

authoring JSON 的图片只写安全相对路径，例如 `source-assets/cover.jpg`。禁止写 `file://`、绝对路径、base64 或第三方临时图片 URL。

CHECKPOINT · STOP：用户只要求“先生成/先看看/不要上传”时，到此停止。不得检查或要求 API Key，不得上传图片，不得调用导入接口。

## 图片处理

只在图片确有作用时添加。封面应帮助理解甲程目标；题目图片必须参与观察、判断或读数；行动图片只用于跟练内容。不要给纯文本题机械配装饰图。

```bash
python3 scripts/compress_learning_track_images.py \
  output/<slug>/learning-track.json \
  -o output/<slug>/learning-track.upload-ready.json
```

所有甲程封面、题目图和行动内容图上传前都必须不超过 524288 字节。原图留在 `source-assets/`，压缩产物写入 `assets/`。

## 导入（此时才需要 API Key）

先检查环境变量；不要让用户把 Key 贴到聊天里：

```bash
test -n "${PRACMO_APIKEY:-}"
```

缺少时停止并提示用户在本地设置：

```text
未检测到 PRACMO_APIKEY，当前本地甲程包已经准备好，但还不能上传或导入。
请访问 https://www.zendong.com.cn/app/api-key 获取 API Key，并在本地设置：
export PRACMO_APIKEY="你的_API_Key"
设置后再让我继续导入；不要把 API Key 发到聊天里。
```

上传和导入：

图片上传器复用 `pracmo-public-action` 的 Python `oss2` 路径；首次使用若缺少依赖，执行 `python3 -m pip install oss2`。

```bash
python3 scripts/finalize_learning_track_assets.py \
  output/<slug>/learning-track.upload-ready.json \
  -o output/<slug>/learning-track.finalized.json

python3 scripts/publish_learning_track.py \
  output/<slug>/learning-track.finalized.json \
  --output output/<slug>/import-result.json \
  --ledger output/<slug>/import-ledger.jsonl
```

本地服务验证时设置：

```bash
export PRACMO_OPEN_API_BASE="http://127.0.0.1:8081/open/v1"
```

默认正式入口是 `https://apis.zendong.com.cn/open/v1`。只有用户明确指定其他环境时才改 `PRACMO_OPEN_API_BASE`。

## 幂等与恢复

- `clientRequestId` 一旦生成就稳定保存；同一内容重试必须保持不变。
- 相同 request ID + 不同 JSON 会被 Server 拒绝，不能覆盖。
- HTTP 超时或断连时，publisher 自动查询 `GET /learning-tracks/imports/:clientRequestId`。
- `pending`：等待或 lookup，不换 ID 盲目重发。
- `retryable_failed`：可用同一 finalized JSON 和 request ID 重试。
- `terminal_failed`：修正内容后生成新的 request ID。
- finalized JSON 不得覆盖 authoring JSON。

## 提交前门禁

- `schemaVersion` 必须为 `pracmo-learning-track@v1`。
- State 2–8 个，首尾 key 与 current/target 一致，引用闭合。
- Exercise ≤10；每个 1–100 题；总题数 ≤300。
- Action ≤10；不得包含账号、甲程、运行态、打卡、守甲、证据结果或生成 session。
- Asset ≤50；每张 ≤512 KiB；finalized 只含 HTTPS URL 和当前账号的 `learning-track-assets/<clientRequestId>/` 对象键。
- 标题、目标、说明、题干、选项和解析面向 App 用户自包含，不依赖本地文件路径或 Agent 上下文。

## 成功反馈

返回导入后的甲程标题、`trackId`、阶段/练习/行动数量，并说明这是用户自己的私人甲程，可在璞奇 App 中继续调整与推进。不要声称它已经公开发布。
