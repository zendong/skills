---
name: pracmo-public-action
description: "Create, validate, review-export, or submit a Pracmo public Action in any supported mode: 自行完成、小璞准备·轻阅读、小璞准备·快问答、跟练计划. Use this skill whenever the user asks to 创建公开行动、公开 Action、行动 JSON、投稿行动、制作可审核或可下载行动、生成小璞内容行动、生成公开跟练计划，or export a public Action JSON as Markdown. JSON is the executable source of truth; images are compressed and uploaded before submission. Do not use it for creating or editing a user's private Action."
---

# Pracmo Public Action

Create a portable public Action that the Pracmo server can review and users can later import into a Track. The authoritative artifact is `pracmo-public-action@v2` JSON. Markdown is a deterministic review export only; never parse Markdown back into submission JSON.

## Required references

Before authoring, read:

- `references/public-action-json-contract.md` for semantic rules and mode matrix.
- `references/public-action.schema.json` for the machine-readable shape.
- `references/categories.json` for planning labels. Before upload, the server category endpoint is authoritative.
- `references/local-publication-guide.md` for a reproducible localhost submission runbook.

## Choose one mode

- `self_directed`: the user performs the described behavior. Completion may be `one_tap`, `text`, or `rich_media`. Do not include `generatedContentConfig` or `followPlan`.
- `puki_generated` + `reading`: 小璞 prepares a new reading. Completion must be `one_tap`. Include `generatedContentConfig` with `schemaVersion: 1`, `type: reading`, and a detailed instruction of at most 1000 characters. Do not include `quickQa` or `followPlan`.
- `puki_generated` + `quick_qa`: 小璞 prepares questions. Completion must be `one_tap`. Include a detailed instruction and `quickQa.questionType`; do not include `followPlan`.
- `follow_along`: repeated progressive levels. Completion must be `one_tap`. Include 1–20 levels and optional checkpoints; do not include `generatedContentConfig`.

## Workflow

1. Confirm the Action goal, audience, mode, category, cadence, completion evidence, and safety boundary. Do not invent private user state.
2. Create `output/<slug>/public-action.json`. It must include a stable revision-specific `clientRequestId`, catalog category, 4–6 useful tags, one cover, and the complete portable template.
3. Author mode-specific content:
   - Self-directed descriptions state the smallest observable behavior and what counts as complete.
   - Generated instructions specify goal, Track-context use, output structure, length/difficulty, variation, factual boundary, safety boundary, and self-check. Stay within 1000 characters.
   - Follow-along levels are repeatable stages, not calendar days. Each level states steps, expected effort, common errors, progression criteria, and safety limits when relevant.
4. Produce a publishable 16:9 cover. Content images are optional except when visual form or technique cannot be explained safely with text. Use only original, generated, or clearly licensed images.
5. Keep originals in `source-assets/`. Compress every upload image before any OSS request:

   ```bash
   python3 scripts/compress_public_action_images.py \
     output/<slug>/public-action.json \
     -o output/<slug>/public-action.json \
     --assets-dir assets
   ```

   Every result must be at most 512 KiB. The script rewrites matching `localPath` fields; do not upload originals from `source-assets/`.
6. Validate locally:

   ```bash
   python3 scripts/validate_public_action_json.py \
     output/<slug>/public-action.json --check-assets --json
   ```

7. Export Markdown for review when useful:

   ```bash
   python3 scripts/public_action_json_to_markdown.py \
     output/<slug>/public-action.json \
     -o output/<slug>/public-action.md
   ```

8. Stop here for a draft. Submit only when the user explicitly asks to publish, post, or make it public. Require `PRACMO_APIKEY` in the local environment; never ask the user to paste it into chat. For local development set `PRACMO_OPEN_API_BASE=http://127.0.0.1:8081/open/v1`. For prepub set `PRACMO_OPEN_API_BASE=https://apis-pre.zendong.com.cn/open/v1`; keep the prepub API key only in the environment.
9. Run the one-click publisher:

   ```bash
   python3 scripts/publish_public_action.py \
     output/<slug>/public-action.json \
     --finalized-output output/<slug>/public-action.finalized.json \
     --ledger output/<slug>/submission-ledger.jsonl \
     --output output/<slug>/submission-result.json
   ```

   The publisher validates local images, fetches `/public-actions/categories` before upload, rejects a disabled category, uploads staged OSS assets, writes the finalized remote-only JSON, submits once, and resolves uncertain transport results through the idempotency lookup.
10. Report `publicActionId`, `status`, and `reviewStatus`. Ordinary submissions are `draft + pending` and must be described as “已提交待审核”. Say “已公开” only for `published + approved`.

## Sync an existing finalized package to prepub

When the user explicitly asks to synchronize an already prepared Action without changing its business JSON or image bytes:

1. Do not rerun generation or compression. Keep `public-action.json`, `assets/*`, the template, tags, category, image bytes, and `clientRequestId` unchanged.
2. Set `PRACMO_OPEN_API_BASE=https://apis-pre.zendong.com.cn/open/v1` and use the prepub `PRACMO_APIKEY` from the environment.
3. OSS staging keys are account-scoped (`material/<accountId>/action-assets/`). If local and prepub use different API-key accounts, a local `public-action.finalized.json` will be rejected with `asset objectKey is outside the account public-action staging prefix`. In that case, use the unchanged `public-action.json` as input so the publisher uploads the already compressed image bytes into the prepub account prefix. Do not manually edit the local finalized JSON.
4. Keep environment-specific evidence separate so the local result is preserved:

   ```bash
   python3 scripts/publish_public_action.py \
     output/<slug>/public-action.json \
     --finalized-output output/<slug>/public-action.prepub.finalized.json \
     --ledger output/<slug>/submission-ledger.prepub.jsonl \
     --output output/<slug>/submission-result.prepub.json
   ```

5. When both environments intentionally use the same account ID and managed staging prefix, `public-action.finalized.json` may be used directly; otherwise the authoring JSON path above is required.
6. The image upload and server-side public-object copy preserve the prepared image content; they are environment migration, not image editing.
7. Query prepub by the unchanged `clientRequestId` and verify `draft + pending`, a non-empty prepub `publicActionId`, the expected `actionType`, and HTTPS assets. Never infer prepub success from a local submission result.

## Output layout

```text
output/<slug>/
  public-action.json             # authoritative authoring JSON
  public-action.md               # generated review export
  public-action.finalized.json   # exact remote-only submitted payload
  submission-result.json
  submission-ledger.jsonl
  source-assets/                 # originals, never uploaded directly
  assets/
    cover.jpg                    # required, <= 512 KiB
    step-01.jpg                  # optional content image, <= 512 KiB
```

## Public and safety boundaries

- Never include Track IDs, start dates, reminders, guardians, occurrences, completions, account data, private state links, evidence plans, API keys, local absolute paths, or Agent-only context.
- `catalog.category` must be one server-enabled code. Tags are search terms, not promises; use at most 8.
- New submissions contain exactly one cover asset. Every image block references an `assets[].assetId`; finalized blocks also contain the uploaded HTTPS `mediaUrl`.
- Use the user's language unless requested otherwise. Backend enum codes remain unchanged.
- For health, exercise, medicine, injury, rehabilitation, legal, psychological, or financial topics, use conservative wording, clear stop conditions, and no diagnosis, guarantees, or personalized high-risk advice.
- Do not fabricate sources, studies, statistics, quotations, current events, or private company facts. Do not reproduce copyrighted text or submit images without publication rights.

## Failure and recovery

- Validation or compression failure: repair the local package; do not upload.
- Missing API key: stop before network mutation.
- Category preflight failure: refresh server configuration or choose an enabled code; do not upload.
- Upload failure: keep `public-action.json` unchanged and rerun with the same genuine revision.
- POST timeout: use the submission lookup result and ledger before retrying.
- Same `clientRequestId` with different content: do not overwrite. Create a new ID only for a genuine revision.
- Rejected or offline: report the server state and review reason; never claim it is discoverable.
