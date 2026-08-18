# Portable Action 合同

允许字段仅包括：

- 展示：`actionKey/title/description/iconCode/colorCode`
- 计划：`scheduleType/scheduleConfigJson/timezone/startDate/endDate/deadlineLocalTime/gracePolicy`
- 完成：`completionMode/reminderConfigJson`
- 内容：`contentMode/generatedContentConfig/followPlan`
- 目标关系：`stateLink/evidencePlan`

不得提供 `accountId/trackId/actionId/now/sourceType/sourceRefId/proposal*`，也不得携带 occurrence、completion、guardian、buffer、session 或任何历史运行状态。Server 注入账号、甲程、来源与时间。

## 内容模式

- `self_directed`：用户自行完成；不得有 `generatedContentConfig` 或 `followPlan`。
- `puki_generated`：小璞准备；`completionMode` 必须为 `one_tap`。
  - 轻阅读：`generatedContentConfig.type=reading`，提示词明确受众、主题边界、每日差异、篇幅、结构和安全边界。
  - 快问答：`type=quick_qa`，另设 `quickQa.questionType`。
- `follow_along`：跟练计划；`completionMode=one_tap`，包含 1–20 个 level，每个 level 有文字或图片内容块。

`deadlineLocalTime` 必须是 `HH:mm`。一次性行动的 `startDate` 必须晚于用户时区的今天。

`reminderConfigJson` 不需要提醒时写空字符串；需要提醒时写 JSON 字符串，例如
`{"times":["20:00"]}`，最多 5 个不重复的 `HH:mm` 时间。也可使用
`{"defaultBeforeDeadlineMinutes":30}`，取值必须为 1–1440。不要写空对象 `{}`。
