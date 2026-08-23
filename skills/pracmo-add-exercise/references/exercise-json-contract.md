# 私人甲程练习 JSON 合同

顶层只允许 `schemaVersion`、`clientRequestId`、`exercise`。版本固定为 `pracmo-track-exercise@v1`。

`clientRequestId` 长 8–64，只使用字母、数字、点、下划线、短横线，首字符为字母或数字。同一语义内容重试不得改变。

`exercise` 必填 `title` 和 `questions`；可包含 `userRequest`、`difficultyLevel`、来源及材料上下文字段。不得包含甲程创建信息、公开状态或分享请求。

每题须有 `questionType`、`questionContent`、`concept`、`testableClaim`、`bloomLevel` 和 `explanation`。`concept` 是包含非空 `name` 或 `conceptId` 的对象，不是字符串。客观题给出完整 options 和 `isCorrect`：单选/判断恰好一个正确项，多选至少两个正确项；简答题给出可判定的参考答案/解析。总题数 10–100。

Server 始终以 API Key 账号为 owner，并把练习强制保存为 private。

## 图片

Server 当前通过 Markdown 承载图片，不使用额外图片字段。图片可出现在：

- `questions[].questionContent`
- `questions[].options[].content`

创作阶段使用 `![替代文字](asset://asset-id)`，并以独立的 `pracmo-exercise-images@v1` manifest 记录来源和复核。最终请求必须把占位符替换为 `![替代文字](https://...)`，且顶层仍只能包含 `schemaVersion`、`clientRequestId`、`exercise`。

最终请求禁止 `asset://`、`file://`、本地绝对/相对路径、base64/data URL 和 HTTP 明文图片。内部 manifest、来源清单与审阅记录不得塞进 API 请求。
