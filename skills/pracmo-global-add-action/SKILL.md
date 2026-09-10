---
name: pracmo-global-add-action
display_name: Pracmo Action Authoring
description: "Create private actions in the user's existing Pracmo track, including self-directed completion, Puki-prepared content and layered follow-along plans with text/image blocks. Use when the user says create an action, daily task, light reading, quick Q&A, follow-along plan, movement demonstration image or staged training. You MUST read and select an existing track owned by the API Key's user; you MUST NOT create a track or a public action. Follow-along images MUST go through reliable-source grounding, movement and safety review, private upload and HTTPS finalization."
description_en: "Create private actions in an existing track: self-directed, Puki-prepared layered content, or step-by-step follow-along with text/image blocks, including image grounding, review and upload."
category: productivity
version: 0.1.7
author: Pracmo (evertrain)
user-invocable: true
---

# Pracmo Add Action

Create private actions in a track that the user selects from what already exists. This skill does not create tracks, does not call the public action submission or review endpoints, and does not generate public templates.

Before starting, read `references/action-json-contract.md` in full. When follow-along images, factual movement specifications, repetitions/duration or health-safety content are involved, also read `references/follow-image-grounding-and-review.md` in full.

## Mandatory Prerequisite: Read and Select a Track

Call `GET /open/v1/learning-tracks?state=active&pageSize=100` (with `pracmocli --env global tracks list`); installing `pracmocli`: `npm install -g @pracmo/pracmo-cli` (no Python/Pillow/oss2 dependencies). Confirm login first: `pracmocli --env global auth status`, or supply the Key through the environment variable `PRACMO_API_KEY`. When not logged in, tell the user to run `pracmocli --env global auth login` (or get a Key at `https://www.pracmo.app/app/api-key`); do not let the user send the Key into the chat.

```bash
pracmocli --env global tracks list "track keyword"
```

When there is exactly one unambiguous match, use it, and state the track name before creating. When there are several reasonable matches, list the titles and the `trackId` values and ask the user to choose; do not guess. When there is no active track, stop and prompt exactly as follows:

```text
No existing track is available. Please create a track in the Pracmo mobile app first, then tell me once it is created, and I will be able to read it and continue adding actions.
```

You MUST NOT create a track. When the user asks to create a new track, likewise only point to creating it in the mobile app.

## Designing an Action

- `self_directed`: the user completes it by themselves; the completion mode may be `one_tap`, `text` or `rich_media`.
- `puki_generated`: Puki prepares light reading or quick Q&A; the completion mode is `one_tap`, and a complete `generatedContentConfig` is provided.
- `follow_along`: layered follow-along; the completion mode is `one_tap`, with 1–20 repeatable levels, text/image blocks and optional checkpoints.

Make the title, the minimum observable behaviour, the frequency, the timezone, the dates, the deadline, the completion criteria, the progression criteria and the safety boundaries explicit. Do not generate accounts, track ownership, check-in records, guardian relationships, review status or public category fields.

Factual movement specifications, health and safety, repetitions, duration and professional relationships MUST come from the user's material or from reliable material that was actually opened. Prefer official guidelines, formal standards, professional organizations, original papers and first-hand explanations; you MUST NOT rely on model parameter memory. Search snippets can only locate material, and cannot serve as the sole evidence. When you cannot confirm something, delete that assertion, reduce it to a non-factual statement, or ask the user for material.

## Follow-Along Image Authoring Package

Use images only when they can explain posture, direction, steps, equipment position or a comparison; do not add purely decorative images. Author with two files:

Images may only be downloaded from a web page in their original form, or generated from a real scene. The whole complete generated image MUST be produced directly by the image generation tool, and local layout is forbidden by default: Pillow, Canvas, SVG, HTML/CSS, screenshot collages, post-production text overlay, perspective compositing or code drawing MUST NOT be used to place movements, text, numbers, arrows, equipment or backgrounds onto the image. Only compression, format conversion, metadata stripping and alpha-channel handling that do not change the visible content are allowed. When a typo, a wrong number, a wrong posture, a safety problem or inauthenticity appears, regenerate the whole image; the only exception is when the user explicitly requests local layout or compositing, and it MUST be recorded.

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

OCR and vision models can only assist; they cannot replace the item-by-item comparison. Any uncertainty, conflicting source, ambiguous posture or safety problem MUST first be corrected and reviewed again. If any single item does not pass, you MUST NOT create.

```bash
pracmocli --env global images validate \
  --stage reviewed \
  --type action \
  --manifest output/<slug>/reviewed/action-images.json \
  output/<slug>/action.authoring.json
```

## Private Upload and Finalization

After the reviewed validation passes, run:

```bash
pracmocli --env global images finalize \
  --manifest output/<slug>/reviewed/action-images.json \
  --type action \
  -o output/<slug>/action.json \
  output/<slug>/action.authoring.json

pracmocli --env global images validate --stage finalized --type action output/<slug>/action.json
```

Finalization uses `clientRequestId + assetId + reviewedSha256` to build a deterministic private `practiceAssets` key, re-downloads the uploaded content and compares the hash, and then replaces `asset://` with an HTTPS `mediaUrl`. The CLI has all of this built in, with no Python/Pillow/oss2 dependencies; you MUST NOT bypass the finalization command.

After a creation failure or timeout, reuse the same `action.json`; do not finalize again, change the URL or change the request ID. `action-images.finalized.json` is a resumable ledger and MUST NOT be sent to the action API.

## Creation

When the user asks for actual creation, the target track is unambiguous, and all applicable gates pass:

```bash
pracmocli --env global actions add <trackId> output/<slug>/action.json
```

This calls `POST /open/v1/learning-tracks/:trackId/actions`. `trackId` MUST come from an active track that was just read with the current API Key. Calling the public action submission endpoint is strictly forbidden.

## Idempotency and Feedback

- Retrying the same content keeps the same `clientRequestId` and final JSON; reusing the same ID with different content conflicts.
- When the user only asks for a draft, save/display the draft and stop; do not upload and do not call the creation endpoint.
- After success, report the track, `trackId`, action title, `actionId`, mode and image count, and make clear that this is a private action.
- Stop when the track does not exist, has ended, or does not belong to the current user; do not automatically submit to another track.

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
