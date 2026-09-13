# 回读审计与练习册迁移

提交成功 ≠ 可以结束。创建后要**回读核对**归属、题量、答案与解析，迁移既有练习册时还要处理 ID、图片和前向兼容。

## 1. 直连 Open API（CLI 没有回读命令时的通用方式）

- Header：`X-API-Key: <key>`。**后端认 `X-API-Key`，不认 `Authorization: Bearer`**（Bearer 会返回 `missing API key`，即使 Key 正确）。
- 端点：
  - `GET /open/v1/flow/exercise/:exerciseId` → 元信息：`questionCount`、`accessMode`（当前保存状态，未公开）等。
  - `GET /open/v1/flow/questions?exerciseId=<id>&limit=100` → 题目列表。

```bash
curl -s -H "X-API-Key: $PRACMO_API_KEY" \
  "https://apis.pracmo.com/open/v1/flow/questions?exerciseId=<exerciseId>&limit=100"
```

## 2. 解析回读语义（重要，别误报"解析丢失"）

读接口**不会**返回 `options[].explanation`，而是把底层存储的逐选项解析**动态组合**成题目的 `question.explanation`：

- 客观题（单选/多选/判断）：每项 `- **A** √/× <该选项解析>`，逐项之间用空行连接；
- 简答题：`question.explanation = options[0].explanation`（参考答案 option 的解析）。

正确审计方式：用本地提交包按同一规则生成 `expected_display_explanation(question)`，与读接口的 `question.explanation` **逐题比对**；同时核对题型、题干、选项 `content`、`isCorrect`、`bloomLevel` 和图片 URL。**不要**因为读接口里 options 没有 `explanation` 就判定解析丢失。

## 3. 审计骨架（Python）

```python
import json, os, urllib.request, urllib.parse

BASE = "https://apis.pracmo.com/open/v1"

def api(path, query=None):
    url = BASE + "/" + path.lstrip("/")
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"X-API-Key": os.environ["PRACMO_API_KEY"]})
    body = json.load(urllib.request.urlopen(req, timeout=60))
    assert body.get("success") is True, body
    return body["data"]

def expected_display_explanation(q):
    if q["questionType"] == "short_answer":
        return q["options"][0]["explanation"]
    return "\n\n".join(
        f"- **{chr(ord('A')+i)}** {'√' if o['isCorrect'] else '×'} {o['explanation']}"
        for i, o in enumerate(q["options"])
    )

# 用提交响应的 exerciseId 回读；与本地包逐题比对
for local, resp in zip(local_questions, api("flow/questions", {"exerciseId": exid, "limit": 100})):
    assert resp["questionType"] == local["questionType"]
    assert resp["questionContent"] == local["questionContent"]
    assert resp.get("explanation", "") == expected_display_explanation(local)
    assert [o["content"] for o in resp["options"]] == [o["content"] for o in local["options"]]
    assert [o["isCorrect"] for o in resp["options"]] == [o["isCorrect"] for o in local["options"]]
```

## 4. 迁移既有练习册到新环境/新账号

- **换环境/账号重提必须换 `clientRequestId`**：相同 ID 会命中幂等（409 或复用旧结果）；只有"同一环境同一请求超时重试"才允许保持原 ID。
- `collectionId` 只能来自**目标环境**刚读取/刚创建的响应（前一环境的练习册 ID 对当前账号越权，会被拒绝）。
- **图片必须重新 `images finalize` 到目标账号**：旧 URL 指向旧账号的 `material/<旧accountId>/practice-assets/`，跨账号不可控（可能被旧账号清理/越权），不能直接写进新请求。
- 迁移旧 manifest 到当前合同：asset 必填 `sourceType`（`primary`/`official`/`standard`/`peer_reviewed`/`reputable_secondary`），缺字段 `images validate --stage reviewed` 会拒。
- 内容不变时复用已审阅文件：上传前用 SHA-256 与旧 OSS 线上对象比对字节一致，并在 `assets[].review.notes` 追加复核记录、更新 `reviewedAt`；不要凭空改 review 结论。

## 5. 公开内容详情 ≠ 完整源

- 公开详情接口（如 `/public/public-exercise-collections/:id`）只给**预览**：`options` 为字符串，无答案、无解析。**不要从公开详情反推答案**。
- 需要完整内容（正确答案、逐选项解析、图片）时，用源提交包（本地 finalized JSON）或管理端审阅接口。
- 公开快照不可回溯：改造历史公开练习册要基于源包重提，而不是从公开详情恢复。
