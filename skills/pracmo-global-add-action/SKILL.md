---
name: pracmo-global-add-action
display_name: Pracmo Action Authoring
description: "Create actions in the user's existing Pracmo track, including self-directed completion, Puki-prepared content and layered follow-along plans with text/image blocks. Use when the user says create an action, daily task, light reading, quick Q&A, follow-along plan, movement demonstration image or staged training. You MUST read and select an existing track owned by the API Key's user; you MUST NOT create a track. Content may later be promoted to public through the public-content flow. Follow-along images MUST go through reliable-source grounding, movement and safety review, account upload and HTTPS finalization."
description_en: "Create actions in an existing track: self-directed, Puki-prepared layered content, or step-by-step follow-along with text/image blocks, including image grounding, review and upload."
category: productivity
version: 0.1.9
author: Pracmo (evertrain)
user-invocable: true
---

# Pracmo Add Action

Create actions in a track that the user selects from what already exists. Created content belongs to the user and may later be promoted to public through the public-content flow; this skill does not create tracks and does not include public action submission/review operations.

Before starting, read `references/action-json-contract.md` in full. When follow-along images, factual movement specifications, repetitions/duration or health-safety content are involved, also read `references/follow-image-grounding-and-review.md` in full.

## Mandatory Prerequisite: Read and Select a Track

Call `GET /open/v1/learning-tracks?state=active&pageSize=100` (with `pracmocli --env global tracks list`); installing `pracmocli`: `npm install -g @pracmo/pracmo-cli` (no Python/Pillow/oss2 dependencies). Confirm login first: `pracmocli --env global auth status`, or supply the Key through the environment variable `PRACMO_API_KEY`. When not logged in, tell the user to run `pracmocli --env global auth login` (or get a Key at `https://www.pracmo.app/app/api-key`); do not let the user send the Key into the chat.

```bash
pracmocli --env global tracks list "track keyword"
```

When there is exactly one unambiguous match, use it, and state the track name before creating. 🔴 STOP: when there are several reasonable matches, list the titles and the `trackId` values and ask the user to choose; do not guess, and do not continue until the user confirms. When there is no active track, stop and prompt exactly as follows:

```text
No existing track is available. Please create a track in the Pracmo mobile app first, then tell me once it is created, and I will be able to read it and continue adding actions.
```

You MUST NOT create a track. When the user asks to create a new track, likewise only point to creating it in the mobile app.

## Designing an Action

- `self_directed`: the user completes it by themselves; the completion mode may be `one_tap`, `text` or `rich_media`.
- `puki_generated`: Puki prepares light reading or quick Q&A; the completion mode is `one_tap`, and a complete `generatedContentConfig` is provided.
- `follow_along`: layered follow-along; the completion mode is `one_tap`, with 1–20 repeatable levels, text/image blocks and optional checkpoints.

Make the title, the minimum observable behaviour, the frequency, the timezone, the dates, the deadline, the completion criteria, the progression criteria and the safety boundaries explicit. Do not generate accounts, track ownership, check-in records, guardian relationships, review status or public category fields.

Minimal complete request for a no-image `self_directed` action (`follow_along` additionally adds `followPlan.levels` inside `action`):

```json
{
  "schemaVersion": "pracmo-track-action@v1",
  "clientRequestId": "action-20260919-daily-plank",
  "action": {
    "title": "Bedtime plank",
    "scheduleType": "daily",
    "timezone": "Asia/Shanghai",
    "startDate": "2026-09-19",
    "deadlineLocalTime": "22:00",
    "completionMode": "one_tap",
    "contentMode": "self_directed"
  }
}
```

Factual movement specifications, health and safety, repetitions, duration and professional relationships MUST come from the user's material or from reliable material that was actually opened. Prefer official guidelines, formal standards, professional organizations, original papers and first-hand explanations; you MUST NOT rely on model parameter memory. Search snippets can only locate material, and cannot serve as the sole evidence. When you cannot confirm something, delete that assertion, reduce it to a non-factual statement, or ask the user for material.

## Deadline and Reminders (Hard Requirements)

`deadlineLocalTime` decides when that day's occurrence becomes due, and it anchors the `defaultBeforeDeadlineMinutes` reminder (the reminder fires that many minutes before the deadline). **The default MUST NOT be 23:59**: it pushes completion to the last minute of the day and drops the reminder late at night, which amounts to encouraging a pre-sleep rush.

- `23:59` is forbidden, as is `00:00–05:00`; use whole or half hours, never a boundary value.
- By default the deadline MUST NOT be later than 22:00; a genuinely pre-sleep action may go as late as 22:30, with the reason stated in the action description.
- The deadline SHOULD sit slightly after the moment the action naturally happens, leaving a buffer without hugging the user's bedtime.
- Order of decisions: read the track's `targetUserDescription` and `requirements` to judge the user's daily rhythm, then the nature of the action itself, and take the earlier of the two.
- Prefer `two_hours` grace as the safety net rather than pushing the deadline itself into the night.
- Reminder times MUST be clearly earlier than the deadline; do not remind only minutes before it, and do not use all five slots.

### By the Nature of the Action

| Nature | Typical examples | Suggested deadline |
| --- | --- | --- |
| Morning | Early rising, morning exercise, planning the day | around 09:00 |
| Daytime | A walk, outdoor activity, chores | 12:00–18:00 |
| Wrap-up | End-of-work review, counting the day | 18:00–20:00 |
| Pre-sleep | Stretching, meditation, a good-night note | 21:00–22:00 |
| All-day flexible | Noting one discovery, drinking water | around 20:00 |

### By the Person the Action Serves

| Who it serves | Suggested window |
| --- | --- |
| Older adults, retirees | 17:00–20:00, shifted earlier |
| Office workers, commuters | 19:00–21:30, not into pre-sleep |
| Students and children | 20:00–21:00, without cutting sleep |
| Night shifts, cross-timezone | Take their real rhythm and state the basis |

A `weekly_quota` deadline falls on the Sunday of the quota week (the server sets the due date to Sunday and only fires reminders on that due date); take the value from the tables above and do not write 23:59 just because the action is weekly.

**Self-check before creating**: the deadline is not 23:59; it is not later than 22:00 (pre-sleep at most 22:30); it matches the user's rhythm and the action's nature; reminders come earlier than the deadline; grace is the `two_hours` safety net.

## Action Output and Grounding (Hard Requirements)

An action MUST NOT only ask the user to "think about it" or "pay attention". This section carries the same weight as action design and the safety gate: if any one is not satisfied, you MUST NOT deliver the content and you MUST NOT create it.

- **Every run produces an output**: one run MUST leave an observable result — a record, a number, a conclusion the user can say out loud, or a before-and-after comparison. An action that only asks the user to notice, recall or feel relaxed without producing any result is empty content.
- **State the completion criteria**: the minimum observable behaviour, the completion criteria and the progression criteria MUST all be explicit, so the user can say what they finished rather than a vague "it felt different".
- **Puki-prepared content carries knowledge density**: the generation instruction MUST require each run to contain one repeatable number, conversion or mechanism, and MUST state the safety boundaries, forbid invented sources, and switch topics when something cannot be stated reliably.
- **Built to last**: an action MUST be sustainable and varied (rotating topics, comparing numbers, staged progression), not a one-off task; frequency, duration, repetitions and movement specifications come from the user's material or from reliable material actually opened.
- **Concrete safety boundaries**: for health and exercise content give general information, stopping conditions and when to see a professional, never individualised prescriptions; do not sell fear, and do not promise cures or outcomes.

### Factual Grounding Ledger

Every factual assertion (numbers, conversions, mechanisms, institutional conclusions, dates, quotations, professional relationships) MUST be tied to a source that was **actually opened**, not to model impression.

- Record for each assertion: the source URL, the quoted passage and the boundary of what it supports, mapped to the specific content of the action; deliver the ledger together with the content.
- Search snippets, reprints, second-hand retellings and model parameter memory can never be the sole basis; search only locates a source, which you MUST then actually open.
- When no reliable source can be found there are only three fallbacks: delete the assertion, reduce it to a non-factual statement, or ask the user for material. Do not paper over it with untraceable phrasing such as "studies show".
- Time-sensitive content (prices, markets, policy, model versions, tool lists, rankings) is excluded by default; when it must be included, base it on a first-hand page you actually opened and state the date you checked it.
- Self-check before delivery: every action run has an output and completion criteria; the content has a repeatable anchor; every factual assertion has a source in the ledger; and no unverifiable assertion has been kept.

## Follow-Along Image Authoring Package

Use images only when they can explain posture, direction, steps, equipment position or a comparison; do not add purely decorative images. Author with two files:

Images may only be downloaded from a web page in their original form, or generated from a real scene. The whole complete generated image MUST be produced directly by the image generation tool, and local layout is forbidden by default: Pillow, Canvas, SVG, HTML/CSS, screenshot collages, post-production text overlay, perspective compositing or code drawing MUST NOT be used to place movements, text, numbers, arrows, equipment or backgrounds onto the image. Only compression, format conversion, metadata stripping and alpha-channel handling that do not change the visible content are allowed. When a typo, a wrong number, a wrong posture, a safety problem or inauthenticity appears, regenerate the whole image; the only exception is when the user explicitly requests local layout or compositing, and it MUST be recorded.

When image generation fails repeatedly or makes no progress for a long time, stop retrying (never more than 3 attempts for the same image), report progress to the user and offer options: switch the source mode, adjust the scene description, or retry later.

- `action.authoring.json`: keeps the final API structure, with image blocks temporarily using `asset://<assetId>`.
- `action-images.json`: uses `pracmo-action-images@v1`, recording sources, facts, exact text/numbers, movement relations, block positions, license and review.

```json
{
  "blockType": "image",
  "mediaUrl": "asset://wall-pushup-start",
  "caption": "Wall push-up starting position"
}
```

First compress into a separate review directory:

```bash
pracmocli --env global images compress \
  --manifest output/<slug>/action-images.json \
  -o output/<slug>/reviewed/action-images.json \
  output/<slug>/action.authoring.json
```

Compression clears the old `review`. You MUST open the actual files in `reviewed/assets/` and check them again, and write the actual SHA-256 into `review.reviewedSha256`.

## Movement and Safety Hard Gate

Compare each image against the source, the caption, the text blocks, the level goals and the progression criteria:

1. Check the image text, labels, symbols, numbers, units, repetitions and duration word by word.
2. Check body/equipment positions, joint angles, support points, direction of motion, sequencing and range of motion.
3. The image MUST be consistent with the caption, the level description, the target training volume and the progression standard.
4. Check warm-up, breathing, stopping conditions, contraindications and risk warnings; a high-risk movement MUST NOT be presented as unconditionally applicable.
5. Check whether cropping, mirroring, arrows or highlighting is misleading, and whether it is still clear when scaled down on a phone.
6. Sources and licenses are complete; the claims, values and relations in a factual image are all traceable.

OCR and vision models can only assist; they cannot replace the item-by-item comparison. Any uncertainty, conflicting source, ambiguous posture or safety problem MUST first be corrected and reviewed again. 🛑 If any single item does not pass, you MUST NOT create.

```bash
pracmocli --env global images validate \
  --stage reviewed \
  --type action \
  --manifest output/<slug>/reviewed/action-images.json \
  output/<slug>/action.authoring.json
```

## Image Upload and Finalization

After the reviewed validation passes, run:

```bash
pracmocli --env global images finalize \
  --manifest output/<slug>/reviewed/action-images.json \
  --type action \
  -o output/<slug>/action.json \
  output/<slug>/action.authoring.json

pracmocli --env global images validate --stage finalized --type action output/<slug>/action.json
```

Finalization uses `clientRequestId + assetId + reviewedSha256` to build a deterministic `practiceAssets` key, re-downloads the uploaded content and compares the hash, and then replaces `asset://` with an HTTPS `mediaUrl`. The CLI has all of this built in, with no Python/Pillow/oss2 dependencies; you MUST NOT bypass the finalization command.

Actions with no image block skip compression, review and finalization: write `output/<slug>/action.json` directly (without going through `action.authoring.json`), and create once the same command validates it:

```bash
pracmocli --env global images validate --stage finalized --type action output/<slug>/action.json
```

After a creation failure or timeout, reuse the same `action.json`; do not finalize again, change the URL or change the request ID. `action-images.finalized.json` is a resumable ledger and MUST NOT be sent to the action API.

## Creation

🛑 Before creating, confirm every item: the target track comes from the active list just read in this session, all applicable gates have passed, and the user has authorized the actual creation — if any of these does not hold, stop immediately and do not create.

When the user asks for actual creation, the target track is unambiguous, and all applicable gates pass:

```bash
pracmocli --env global actions add <trackId> output/<slug>/action.json
```

This calls `POST /open/v1/learning-tracks/:trackId/actions`. `trackId` MUST come from an active track that was just read with the current API Key. Calling the public action submission endpoint is strictly forbidden.

This endpoint creates the action **paused** by default: no check-in occurrences are generated, no reminders are delivered, and it does not count against the active-action quota. An idempotent retry with the same `clientRequestId` returns the same paused action; do not create another one.

## Idempotency and Feedback

- Retrying the same content keeps the same `clientRequestId` and final JSON; reusing the same ID with different content conflicts.
- 🛑 When the user only asks for a draft, save/display the draft and stop; do not upload and do not call the creation endpoint.
- After success, report the track, `trackId`, action title, `actionId`, mode and image count, and note that the action starts **paused**; the content belongs to the user and may later be promoted to public.
- **Mandatory post-creation reminder**: tell the user the action was created in the "<track name>" track but starts paused, and that they need to open the Pracmo app ("Track detail → Action"), open this action and tap **Enable** before check-ins and reminders start. Only continue further operations after the user confirms they enabled it or asks you to recreate it.
- Stop when the track does not exist, has ended, or does not belong to the current user; do not automatically submit to another track.

## Red Lines (Never Do)

- Creating a track, or calling any track-creation/import endpoint.
- Using model parameter memory, search snippets or a re-post that was not actually opened as factual evidence.
- Local layout/compositing of generated images (except when the user explicitly requests it, and it MUST be recorded).
- Filling in the `review` field falsely to pass validation, or skipping the compress → review → validate flow.
- Assembling URLs by hand and bypassing `images finalize`; changing the `clientRequestId` or modifying the JSON on a retry.
- Creating while a gate has not passed or the user has not authorized it.

## Exit Codes and Recovery Actions

Write operations are **not retried automatically** by default. Before submitting, you may use `--dry-run` to perform only local structural validation without sending a request.

| Code | Meaning | Recovery action |
|----|------|----------|
| 0 | Success | Parse the stdout JSON |
| 1 | Argument/usage error | Check `pracmocli help` and then fix the command; do not change the JSON content |
| 2 | Not logged in / credentials expired | Guide the user to `pracmocli --env global auth login` (or get a Key at `https://www.pracmo.app/app/api-key`) |
| 3 | Business error (backend 4xx non-conflict) | Handle according to the stderr error message; when the track is unauthorized or has ended, re-read the list and have the user confirm again |
| 4 | Network/timeout | **Retry with the same `clientRequestId` and exactly the same JSON**; you MUST NOT generate a new ID |
| 5 | Conflict (409 idempotency conflict) | Content unchanged → check the earlier result; content substantially modified → generate a new `clientRequestId` |
| 6 | Local gate not passed (validation failure) | After fixing the image/action description, **re-run the full validation**; **MUST NOT create** |

> The action image pipeline **MUST carry `--type action`**. Omitting it makes the exercise validator check the action JSON,
> which shows up as `request top-level keys must be exactly schemaVersion, clientRequestId, exercise`.
> Also confirm that `stage` and `type` in the validation output match your expectations — a gate letting through the wrong stage causes irreversible consequences.

For a command cheat sheet see `references/cli-commands.md`.
