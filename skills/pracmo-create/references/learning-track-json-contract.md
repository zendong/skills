# `pracmo-learning-track@v1` 合同

## 顶层

| 字段 | 要求 |
|---|---|
| `schemaVersion` | 固定 `pracmo-learning-track@v1` |
| `clientRequestId` | 8–128 位稳定幂等键；同一内容重试不得改变 |
| `track` | 私人甲程基础信息与目标画像 |
| `path` | 当前到目标的 2–8 个有序 State |
| `concepts` | 包内概念字典；练习题通过 `conceptKey` 引用 |
| `exercises` | 0–10 个完整练习；每个 1–100 题，总题数不超过 300 |
| `actions` | 0–10 个 portable Action |
| `assets` | 0–50 个图片资产 |
| `metadata` | 可选审计信息；不得含 API Key 或 STS 凭证 |

## State

State 描述“用户稳定处于什么状态”，不是章节或任务。第一个 State 必须匹配 `currentStateKey`，最后一个匹配 `targetStateKey`。每个 State 具有 1–5 条可以观察或验证的 criterion；`criterionId` 在该 State 内唯一。

## Exercise

支持 `single_choice / multiple_choice / true_false / short_answer`。选择题和判断题必须有选项与正确答案；简答题的解析应给出评分依据。每题必须引用一个已声明的 `conceptKey`，并给出具体 `testableClaim`。

可选 `stateLink`：

```json
{
  "stateKey": "stable",
  "relationRole": "advance",
  "criterionIds": ["stable-1"],
  "whyNow": "先掌握能独立执行的最小方法"
}
```

## Asset

authoring：

```json
{
  "assetId": "cover",
  "role": "cover",
  "localPath": "source-assets/cover.jpg",
  "alt": "清晨公园里正在散步的人"
}
```

finalized：

```json
{
  "assetId": "cover",
  "role": "cover",
  "objectKey": "material/1001/learning-track-assets/request-v1/cover.jpg",
  "url": "https://example.oss-cn-hangzhou.aliyuncs.com/material/1001/learning-track-assets/request-v1/cover.jpg",
  "sha256": "...",
  "contentType": "image/jpeg",
  "sizeBytes": 183421,
  "width": 1200,
  "height": 800,
  "alt": "清晨公园里正在散步的人"
}
```

authoring 与 finalized 形态互斥。finalized 不允许遗留 `localPath`。

## 最小骨架示例

见 `references/examples/skeleton.json`。该包没有练习和行动，但仍创建核心目标、两个 State 和 current State baseline。
