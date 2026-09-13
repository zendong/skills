# 甲程行动 JSON 合同

顶层只允许 `schemaVersion`、`clientRequestId`、`action`。版本固定为 `pracmo-track-action@v1`。

`clientRequestId` 长 8–64，只使用字母、数字、点、下划线、短横线，首字符为字母或数字。同一内容重试保持不变。

行动通用必填：`title`、`scheduleType`、`timezone`、`startDate`、`deadlineLocalTime`、`completionMode`。`scheduleType` 为 `daily / weekdays / weekly_quota / once`；日期为 `YYYY-MM-DD`，本地截止时间为 `HH:mm`。

内容模式：`self_directed` 不带生成配置或跟练计划；`puki_generated` 带 `generatedContentConfig`；`follow_along` 带 `followPlan`。具体组合必须符合 Server Action 校验。

`followPlan.levels` 包含 1–20 个练阶，每个练阶包含 1–20 个 `contentBlocks`。文字 block 使用非空 `textContent`；图片 block 使用 `blockType=image`、非空 `caption` 和 `mediaUrl`。创作阶段 `mediaUrl` 为 `asset://<assetId>`，最终请求必须是带 host 的绝对 HTTPS URL。

图片内部来源和审阅信息保存在独立 `pracmo-action-images@v1` manifest，不发送给 Server。最终 action JSON 禁止 `assetId`、manifest、`asset://`、`file://`、data URL 或本地路径。

不得携带 accountId、trackId、sourceType、sourceRefId、publicActionId、catalog、审核/发布状态、运行态、打卡或守甲数据。Server 从 URL 和 API Key 绑定 owner 与 active 甲程，并固定来源为 `open_api`。
