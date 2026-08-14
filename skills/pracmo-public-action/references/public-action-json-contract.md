# Pracmo Public Action JSON v2

`pracmo-public-action@v2` is the authoring and Open API submission contract. JSON is authoritative; Markdown is generated review material only. `public-action.schema.json` defines the shape, while server validation remains authoritative for schedules, categories, assets, and Action semantics.

## Envelope

```json
{
  "schemaVersion": "pracmo-public-action@v2",
  "clientRequestId": "daily-three-good-things-20260811-v1",
  "catalog": {
    "category": "mind",
    "tags": ["三件好事", "每日复盘"],
    "coverImage": { "localPath": "assets/cover.jpg", "alt": "记录一天中三件具体的好事" }
  },
  "template": {},
  "assets": [
    { "assetId": "cover", "role": "cover", "localPath": "assets/cover.jpg", "alt": "记录一天中三件具体的好事" }
  ]
}
```

- `clientRequestId` is 8–128 characters and stable for retries of exactly the same revision.
- `catalog.category` is fetched from the server before upload. `references/categories.json` is an authoring aid, not runtime authority.
- Tags contain at most 8 items, each at most 32 characters.
- Exactly one cover is required. Authoring images use safe relative `localPath`; finalized images use `objectKey`, HTTPS `url`, SHA-256, MIME type, and `sizeBytes <= 524288`.

## Common template

Every template contains:

```json
{
  "title": "行动标题",
  "description": "可独立理解的公开说明",
  "iconCode": "spark",
  "colorCode": "mint",
  "scheduleType": "daily",
  "scheduleConfigJson": "{}",
  "timezone": "Asia/Shanghai",
  "deadlineLocalTime": "21:00",
  "gracePolicy": "none",
  "completionMode": "one_tap",
  "contentMode": "self_directed"
}
```

Schedules: `daily`, `weekdays`, `weekly_quota`, `once`. Grace policies: `none`, `two_hours`, `next_day_noon`. Deadline must be `HH:mm` without seconds.

## Mode matrix

| Public type | `contentMode` | Completion | Required extension | Forbidden extension |
|---|---|---|---|---|
| 自行完成 | `self_directed` | `one_tap`, `text`, `rich_media` | none | `generatedContentConfig`, `followPlan` |
| 小璞准备·轻阅读 | `puki_generated` | `one_tap` | generated type `reading` | `quickQa`, `followPlan` |
| 小璞准备·快问答 | `puki_generated` | `one_tap` | generated type `quick_qa` + `quickQa` | `followPlan` |
| 跟练计划 | `follow_along` | `one_tap` | `followPlan` | `generatedContentConfig` |

### 小璞准备

```json
"generatedContentConfig": {
  "schemaVersion": 1,
  "type": "quick_qa",
  "instruction": "不超过 1000 字符的完整生成要求",
  "quickQa": { "questionType": "short_answer" }
}
```

Reading omits `quickQa`. Quick-QA question types are `auto`, `single_choice`, `multiple_choice`, `true_false`, `short_answer`, or `mixed`.

### 跟练计划

```json
"followPlan": {
  "afterCompletionPolicy": "continue_last_level",
  "levels": [{
    "title": "第一练阶",
    "description": "阶段目标",
    "targetSessions": 4,
    "promotionCriterion": "可观察的进阶条件",
    "estMinutes": 8,
    "contentBlocks": [{ "blockType": "text", "textContent": "完整步骤" }]
  }],
  "checkpoints": [{ "levelIndex": 0, "title": "完成入门", "description": "节点说明", "isKey": true }]
}
```

Plans contain 1–20 repeatable levels. A text block requires `textContent`. An image block references a content asset by `assetId`; after upload it also contains the asset HTTPS `mediaUrl`. Checkpoint indexes are zero-based and must reference an existing level.

## Forbidden private/runtime state

Do not include target Track IDs, start dates, reminders, guardian configuration, occurrences, completion records, account identity, private state links, evidence plans, API keys, absolute paths, or chat-only context. The server copies the portable template into a new user-owned Action on import.
