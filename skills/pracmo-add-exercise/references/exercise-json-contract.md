# 甲程练习 JSON 合同

顶层只允许 `schemaVersion`、`clientRequestId`、`exercise`。版本固定为 `pracmo-track-exercise@v1`。

`clientRequestId` 长 8–64，只使用字母、数字、点、下划线、短横线，首字符为字母或数字。同一语义内容重试不得改变。

`exercise` 必填 `title` 和 `questions`；最终提交还必须包含 `collectionId`。`collectionId` 为 1–64 字符的真实练习册 ID，必须来自刚查询或刚创建的目标甲程练习册响应，不得传显示名称、猜测值或其他甲程的 ID。草案/审阅包可以暂缺该字段，以支持确认后才创建新练习册；`--stage finalized` 必须拒绝缺失值。

可选字段包括 `userRequest`、`difficultyLevel`、来源及材料上下文字段。不得包含甲程创建信息、公开状态或分享请求。

每题须有 `questionType`、`questionContent`、`concept`、`testableClaim`、`bloomLevel` 和 `options`。题目对象不得包含解析字段；所有解析统一写入非空的 `options[].explanation`，并且必须针对对应 option 分别说明其成立或不成立的理由，不能使用一段通用解析覆盖整题。

`concept` 是包含非空 `name` 或 `conceptId` 的对象，不是字符串。单选和判断恰好一个正确 option，多选至少两个正确 option；这些题型的每个 option 都必须包含 `content`、布尔值 `isCorrect` 和非空 `explanation`。简答题必须有且只有一个参考答案 option：`content` 为可判定的参考答案，`isCorrect` 为 `true`，`explanation` 为评分要点、成立边界和常见遗漏。总题数 3–100。

Server 以 API Key 账号为 owner 保存练习；创建接口暂不接受公开/分享参数，后续公开可走公开内容流程。

## 目的地合同

- 查询练习册：`GET /open/v1/learning-tracks/:trackId/exercise-collections`
- 创建练习册：`POST /open/v1/learning-tracks/:trackId/exercise-collections`
- 创建成品练习：`POST /open/v1/learning-tracks/:trackId/exercises`

最终练习请求的 `exercise.collectionId` 必须与已确认目的地一致。Server 对省略值保留旧客户端的默认册兼容，但本 skill 不得利用该兼容路径。成功响应的 `collection.collectionId` 是底层实际归属，必须回读核对。

## 图片

Server 当前通过 Markdown 承载图片，不使用额外图片字段。图片可出现在：

- `questions[].questionContent`
- `questions[].options[].content`

创作阶段使用 `![替代文字](asset://asset-id)`，并以独立的 `pracmo-exercise-images@v1` manifest 记录来源和复核。最终请求必须把占位符替换为 `![替代文字](https://...)`，且顶层仍只能包含 `schemaVersion`、`clientRequestId`、`exercise`。

最终请求禁止 `asset://`、`file://`、本地绝对/相对路径、base64/data URL 和 HTTP 明文图片。内部 manifest、来源清单与审阅记录不得塞进 API 请求。
