# 跟练图片取证与严格审阅

本规范适用于 `followPlan.levels[].contentBlocks[]` 的 image block。图片的价值是准确示范可观察动作，不是装饰。

## 来源优先级

1. 用户提供且实际读取的原始资料。
2. 官方健康/体育指南、正式标准、原始论文或动作体系的一手说明。
3. 专业组织、大学、医院或公共机构资料。
4. 能链接回一手证据的可靠二手材料。

搜索摘要、无出处转载、社交媒体内容和模型参数记忆不能作为唯一证据。健康、安全或伤病相关内容属于高风险事实；来源不足或相互冲突时停止，不编造通用结论。

## Manifest 合同

顶层使用 `pracmo-action-images@v1`，`clientRequestId` 与 action 一致，并包含 `resources`、`assets`。每个 resource 记录唯一 `resourceId`、`title`、`publisher`、HTTPS `url`、`sourceType`、`retrievedAt` 以及 `version` 或 `publishedAt`。`sourceType` 仅允许 `primary`、`official`、`standard`、`peer_reviewed`、`reputable_secondary`。

每个 asset：

```json
{
  "assetId": "wall-pushup-start",
  "localPath": "assets/wall-pushup-start.png",
  "altText": "墙壁俯卧撑起始姿势",
  "factuality": "factual",
  "provenance": "generated_from_sources",
  "license": "original",
  "claims": [{"claimId": "claim-1", "text": "图片完整表达的事实", "resourceIds": ["r1"]}],
  "expectedVisibleText": [],
  "containsNumbers": false,
  "expectedValues": [],
  "expectedRelations": [{"subject": "躯干", "relation": "保持", "object": "稳定直线", "notes": "起始姿势"}],
  "usedBy": [{"levelIndex": 0, "blockIndex": 1}],
  "review": {}
}
```

图片包含执行所需数字时将 `containsNumbers` 设为 true，并在 `expectedValues` 为每个值登记 `label`、精确 `displayValue`、可选 `unit` 和 `resourceIds`，不得抽查数字。本地路径必须是 manifest 目录内的相对路径；禁止绝对路径、`..` 和指向目录外的 symlink。

## 审阅

必须打开压缩后的最终待上传文件，放大并逐项比较：文字与数字；身体、关节、支撑点和器材位置；箭头、镜像、运动方向和步骤；与 caption、练阶目标、训练量和进阶条件的一致性；热身、呼吸、停止条件和风险；手机可读性与压缩伪影。

通过后写入：

```json
{
  "sourceVerified": true,
  "pixelInspected": true,
  "textVerified": true,
  "numbersVerified": true,
  "motionLogicVerified": true,
  "planConsistencyVerified": true,
  "safetyVerified": true,
  "mobileReadabilityVerified": true,
  "misleadingCueChecked": true,
  "reviewedSha256": "压缩后文件的 64 位小写 SHA-256",
  "reviewedAt": "ISO-8601",
  "notes": "具体记录姿态、关系、安全条件和计划一致性核对结果"
}
```

不得为了通过脚本虚填 true。图片变化后 SHA 会失配，必须重新审阅。
