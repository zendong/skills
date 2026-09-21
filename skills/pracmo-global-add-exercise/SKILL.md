---
name: pracmo-global-add-exercise
display_name: Pracmo Exercise Authoring
description: "Create a set of exercises in the user's existing Pracmo track and a specified exercise collection; it also supports creating an exercise collection, and creating, retrieving, validating and uploading factually reliable images, charts and diagrams for question stems or options. Use when the user says practice this, turn this content into exercises, write questions for a track or exercise collection, add more exercises, or make questions from an image. You MUST first read the existing tracks owned by the API Key's user; you MUST NOT create a track. When no existing track is available, tell the user to create one in the Pracmo mobile app first."
description_en: "Turn a conversation, material or goal into a set of exercises and add it to the user's existing track and a specified exercise collection; supports creating, retrieving, validating and uploading factually reliable images for question stems and options."
category: productivity
version: 0.1.8
author: Pracmo (evertrain)
user-invocable: true
---

# Pracmo Add Exercise

Turn a conversation, material or goal into a complete set of questions and add them to a track and exercise collection that the user selects from what already exists. Created content belongs to the user and may later be promoted to public through the public-content flow. This skill may create an exercise collection inside the selected track, but it does not create tracks.

Before starting you MUST read in full:

- `references/exercise-json-contract.md`
- When images, charts, factual numbers or external material are involved, also read `references/image-grounding-and-review.md` in full.

## Mandatory Prerequisite: Confirm the Track + Exercise Collection

Before writing questions, confirm login: run `pracmocli --env global auth status`, or supply the Key through the environment variable `PRACMO_API_KEY`. When not logged in, tell the user to run `pracmocli --env global auth login` (or get a Key at `https://www.pracmo.app/app/api-key`); do not let the user send the Key into the chat. Installing `pracmocli`: `npm install -g @pracmo/pracmo-cli` (no Python/Pillow/oss2 dependencies).

Troubleshooting prerequisite:
- API Keys are **not interchangeable** across environments (prod/pre/global): on `invalid API key`, first run `pracmocli --env global doctor` to check `baseUrl`.

Call `GET /open/v1/learning-tracks?state=active&pageSize=100`; when the user gave a name, also pass `keyword`. You may also use:

```bash
pracmocli --env global tracks list "track keyword"
```

Track selection rules:

1. When there is exactly one unambiguous match, use it, and tell the user the track name before creating.
2. When there are several reasonable matches, list the titles and the `trackId` values and let the user choose; do not guess.
3. When there is no active track, or the search result is empty and no other reasonable candidate exists, stop and prompt exactly as follows:

```text
No existing track is available. Please create a track in the Pracmo mobile app first, then tell me once it is created, and I will be able to read it and continue adding exercises.
```

You MUST NOT create a track, and you MUST NOT call any import, `with-exercise` or track-creation endpoint. When the user explicitly asks to "create a new track", use the same mobile-app prompt above.

After selecting a track you MUST call `GET /open/v1/learning-tracks/:trackId/exercise-collections`, or use:

```bash
pracmocli --env global collections list <trackId>
```

Exercise collection selection rules:

1. Identify the system default collection only from `isDefault` in the response; do not guess from display names such as "Uncategorized".
2. If the list contains only the system default collection, you may select it automatically; before creating, you MUST still tell the user the track and collection names together.
3. 🔴 STOP: as long as any named exercise collection exists, you MUST list the candidates and let the user choose explicitly; do not infer one yourself from the exercise topic, and do not continue creating until the user confirms. The default collection is still an option.
4. Disambiguate exercise collections with the same name by description and `collectionId`; in the end use only the real ID returned by the API, and do not construct an ID from a name.
5. 🛑 When the list is still loading, failed to load, is empty, or the choice is ambiguous, stop; you MUST NOT silently fall back to the default collection by omitting `collectionId`.

The user may also choose to create a new exercise collection inside the confirmed track. First confirm one complete destination, for example:

```text
Track + exercise collection: General AI Use, Beginner to Advanced / AI Collaboration Challenge (to be created)
```

This single confirmation authorizes selecting the track, selecting or creating the exercise collection, and then submitting the reviewed exercises; creating an exercise collection does not need a separate second confirmation. If the user only asks for a draft, a design or a preview, you MUST NOT call any write endpoint; a new exercise collection is likewise created only when the user authorizes actual creation.

A create-collection request contains a name, an optional description and a stable `clientRequestId`:

```json
{
  "name": "AI Collaboration Challenge",
  "description": "Progressive practice from asking questions to making decisions",
  "clientRequestId": "collection-20260827-ai-collab-v1"
}
```

For actual creation, call `POST /open/v1/learning-tracks/:trackId/exercise-collections`, or use:

```bash
pracmocli --env global validate collection output/<slug>/collection.json   # validate before submitting
pracmocli --env global collections create <trackId> output/<slug>/collection.json
```

Use the `collectionId` in the creation response as the destination for the following exercises. On a network timeout or an unknown result, retry with the same `clientRequestId` and exactly the same JSON; after the user changes the name or description this is a new intent, and you MUST generate a new ID.

## Material Grounding and Question Writing

- Generate 3–100 complete, answerable questions; the default is 10–15 unless the user specifies otherwise.
- Single choice, multiple choice, true/false and short answer are supported; each question includes a Bloom level from 1–4, a concept and a testable claim, and each option includes an answer marker and an explanation specific to that option.
- Read the material the user provides first. When the factual content is insufficient, actively search and actually open high-quality sources; prefer first-hand material, official documentation, standards, raw data and peer-reviewed papers.
- You MUST NOT rely on model parameter memory to assert facts, numbers, quotations, time-sensitive status or professional relationships. Search snippets may only be used to locate a source, and cannot serve as the sole evidence.
- The question stem, the answer, the per-option explanations and the facts in images MUST all be traceable to material actually read; when no reliable basis can be found, delete that claim, change it into a question without factual assertions, or ask the user for material.
- The question stem and the per-option explanations MUST be self-contained for App users, and MUST NOT depend on the Agent context or local paths.
- 🛑 When the user only asks to "take a look first", output or save a draft and stop; do not call any write endpoint.

## Knowledge Density and Content Grounding (Hard Requirements)

A set of questions MUST leave the user with **specific knowledge**, not a drill in "how to think". Every rule in this section carries the same weight as the image gate: if any one is not satisfied, you MUST NOT deliver the content and you MUST NOT create it.

- **One nameable knowledge through-line**: organise each exercise pack around one real through-line that can be named (for example, "one gram of sodium is roughly two and a half grams of salt"). Before finishing, ask yourself: can the user say in one sentence what they learned? If not, this is empty content.
- **Do not pass metacognitive drills off as knowledge**: making a whole pack out of method questions such as "the difference between observation and judgement", "how to write a record", "questioning technique" or "think before you answer" is the most typical empty exercise. Method may carry knowledge; it MUST NOT replace it.
- **Six-question division of labour**: a question set SHOULD cover, in order, a first guess (a judgement most people get wrong), the mechanism (why it works this way), a number or conversion (something the user can compute), a common misconception (what is wrong with the popular claim), transfer to a new scenario, and a takeaway line the user can repeat and teach. Do not pad the count with paraphrases of one point.
- **Distractors MUST be real misconceptions**: wrong options MUST come from what many people genuinely believe, and MUST let a user who chose wrong understand what they got wrong. Strawmen that can be ruled out at a glance (for example, writing "replace every piece of furniture immediately" as a wrong option) are forbidden, as are exaggerated, absurd or irrelevant options used as filler.
- **A repeatable anchor**: every pack MUST give at least one number, conversion, mechanism or named concept in the stem or the explanations. Besides saying what is right or wrong, each explanation MUST add one conclusion worth remembering.
- **No novelty-seeking or fear-selling**: do not manufacture appeal with exaggeration, absolutes or scare tactics; for health, financial and legal topics give general information and ways to judge, and never individualised advice or promises.
- **Content starts on its own**: the scenario, necessary background, dialogue and numbers are all generated by the AI and placed inside the exercise; the user is not required to find material first.

### Factual Grounding Ledger

Every factual assertion (numbers, conversions, mechanisms, institutional conclusions, dates, quotations, professional relationships) MUST be tied to a source that was **actually opened**, not to model impression.

- Record for each assertion: the source URL, the quoted passage and the boundary of what it supports, mapped to the specific question; deliver the ledger together with the content.
- Search snippets, reprints, second-hand retellings and model parameter memory can never be the sole basis; search only locates a source, which you MUST then actually open.
- When no reliable source can be found there are only three fallbacks: delete the assertion, rewrite it as a question without factual assertions, or ask the user for material. Do not paper over it with untraceable phrasing such as "studies show".
- Time-sensitive content (prices, markets, policy, model versions, tool lists, rankings) is excluded by default; when it must be included, base it on a first-hand page you actually opened and state the date you checked it.
- Self-check before delivery: each pack has one nameable through-line; the six questions are not paraphrases of one another; every wrong option is a real misconception; there is at least one repeatable anchor; every factual assertion has a source in the ledger; and no unverifiable assertion has been kept.

## Per-Option Explanation Hard Contract

Explanations are written only in `options[].explanation`; the question object MUST NOT contain explanation fields. Every option MUST have a non-empty explanation, including wrong options; the explanation MUST state directly why this option holds or does not hold, and MUST NOT merely restate the option, write an explanation only for the correct option, or copy one generic passage into every option.

- Single choice, true/false: exactly one option has `isCorrect` set to `true`; explain the basis for each option being correct or incorrect.
- Multiple choice: at least two options have `isCorrect` set to `true`; explain separately for each option why it should or should not be selected.
- Short answer: there is exactly one reference-answer option in `options`, `content` is an answer that can be graded deterministically, `isCorrect` is fixed at `true`, and `explanation` gives the grading points, the conditions under which it holds and common omissions.

```json
{
  "questionType": "single_choice",
  "questionContent": "Which approach is more appropriate?",
  "options": [
    {
      "content": "Verify the key information first, then act",
      "isCorrect": true,
      "explanation": "This option verifies the facts first, which lowers the risk of acting on a false premise."
    },
    {
      "content": "Act immediately on the first impression",
      "isCorrect": false,
      "explanation": "This option skips fact verification, and a first impression is not enough to support the current decision."
    }
  ]
}
```

Base request format:

```json
{
  "schemaVersion": "pracmo-track-exercise@v1",
  "clientRequestId": "exercise-20260823-stable-id",
  "exercise": {
    "title": "Exercise title",
    "collectionId": "collection_xxx",
    "userRequest": "Exercise goal",
    "difficultyLevel": 2,
    "questions": []
  }
}
```

The create API does not accept `accessMode` or `createShare`; do not include them in requests. Content may later be promoted to public through the public-content flow.

## Image Authoring Package

An image is not decoration. Add one only when it carries observation, comparison, spatial relations, a process, data reading or an identification task; purely decorative images should be omitted.

An image MUST also have credible real-world grounding, and only two source modes are allowed:

- `web_downloaded`: downloaded from a web page that was actually opened, registering the original URL, resource ID, license and the SHA-256 of the downloaded file.
- `real_scene_generated`: generated according to a real scene, registering the generation method and the basis for the scene. The whole complete image MUST be produced directly by the image generation tool.

Local layout is forbidden by default for generated images: you MUST NOT use Pillow, Canvas, SVG, HTML/CSS, screenshot collages, post-production text overlay, perspective compositing or any other code to arrange text, numbers, UI, people, backgrounds or graphics onto a generated image. Only compression, format conversion, metadata stripping and alpha-channel handling that do not change the visible content are allowed. When the text, numbers, relations, posture or authenticity in the image does not pass, regenerate the whole image; the only exception is when the user explicitly requests local layout or compositing, which MUST be recorded in the manifest and the delivery description.

Using flat cards, placeholder boxes or low-fidelity wireframes to pass as a real scene is forbidden. Phone screens should use a neutral phone UI, with no vendor logo, model, notch, Dynamic Island, camera cutout, physical buttons or recognizable third-party App brands. When you cannot be real, clear and verifiable at the same time, prefer leaving the image out.

Before the final upload, author with two files:

- `exercise.authoring.json`: keeps the final API structure, using `asset://<assetId>` as a temporary placeholder in the question-stem or option Markdown.
- `exercise-images.json`: per `pracmo-exercise-images@v1`, records sources, item-by-item facts, expected visible text, logical relations, usage locations, license and strict review results.

Example:

```markdown
Observe the diagram: ![attention cache flow](asset://kv-cache-flow)
```

First put the original images into `source-assets/`, then compress them into a separate review directory:

```bash
pracmocli --env global images compress \
  --manifest output/<slug>/exercise-images.json \
  -o output/<slug>/reviewed/exercise-images.json \
  output/<slug>/exercise.authoring.json
```

Compression deletes the old `review` (after compression you MUST review again against the actual file). The CLI has all of this built in, with no Python/Pillow/oss2 dependencies.

> In the commands, all flags are written **before** the positional arguments. The CLI also accepts the other order, but this form is the least error-prone — copy it as is.

## Image Correctness Hard Gate

Inspect every actual image in `reviewed/assets/` pixel by pixel, comparing it item by item against the evidence list and the sources. OCR, programmatic checks and vision models can only assist; they cannot replace a complete human-style re-check. At a minimum, confirm:

1. All headings, labels, body text, symbols, spelling and language are accurate, with no garbled characters and no truncation.
2. All numbers, units, ratios, axes, legends, dates, decimal points and signs match the source.
3. Arrow directions, causation, order, containment relations, spatial positions, colour mapping and process-branch logic are correct.
4. The image, question stem, options, correct answer and per-option explanations are consistent with one another; cover the answer and answer independently once, and the correct answer is unique or matches the definition of the question type.
5. The image does not leak the answer directly, the distractors remain reasonable, the text is readable when scaled down on a phone, and the key content does not depend on colours that are hard to distinguish.
6. The source, license and factual claims of a retrieved or redrawn image are complete; a factual image MUST cite resource IDs item by item.
7. The layout, lighting, perspective, device operation and interface density of the scene are realistic, not a schematic card disguised as a screenshot.
8. The phone interface stays device-neutral; names, phone numbers, accounts, order numbers, addresses, links, QR codes, bank cards and recognizable brands are all absent, or are explicitly registered and non-routable fictitious values.
9. When an image reflects objective knowledge, check numbers, text, states and logic item by item; anything that cannot be confirmed from a source MUST be deleted, or the image withdrawn.

Write every actual result into `review` in the manifest. Whenever there is any uncertainty, anything unreadable, conflicting sources or logical ambiguity, fix the image and re-check from the beginning. 🛑 If any single item does not pass, you MUST NOT create.

After re-checking, run the hard validation:

```bash
pracmocli --env global images validate \
  --stage reviewed \
  --manifest output/<slug>/reviewed/exercise-images.json \
  output/<slug>/exercise.authoring.json
```

## Upload and Finalization

Upload only after the reviewed validation passes. The command below goes through the CLI to upload directly to OSS under the account `practiceAssets` prefix, re-download and verify the hash of the uploaded content, and then replace every `asset://` with an HTTPS URL; the internal evidence list does not enter the API request. You MUST NOT bypass the finalization command and assemble URLs by hand:

```bash
pracmocli --env global images finalize \
  --manifest output/<slug>/reviewed/exercise-images.json \
  -o output/<slug>/exercise.json \
  output/<slug>/exercise.authoring.json

pracmocli --env global images validate --stage finalized output/<slug>/exercise.json
```

The final JSON MUST NOT contain local paths, `asset://`, `file://`, base64 images or unsafe URLs. Images are allowed only as HTTPS Markdown URLs.

## Creation

🛑 Before creating, confirm every item: the target track and exercise collection come from a response just read or just created in this session, all applicable gates have passed, and the user has authorized the actual creation — if any of these does not hold, stop immediately and do not create.

When the user asks for actual creation, the target track and exercise collection are both unambiguous, and all applicable gates pass:

```bash
pracmocli --env global exercises add <trackId> output/<slug>/exercise.json
```

This calls `POST /open/v1/learning-tracks/:trackId/exercises`. Both `trackId` and `exercise.collectionId` may only come from an API response that was just read or just created; they MUST NOT be invented or copied from someone else's shared content. When there are no images you should still validate the final request with `--stage finalized`.

The success response MUST contain the actual `collection` summary. Check that its `collectionId` matches the target; if the exercise collection has been deleted, disabled, is unauthorized, or does not belong to that track since the confirmation, re-read the list and have the user confirm again — do not automatically switch to the default collection or another collection with the same name.

## Replace an Existing Question Image In Place

When you are only replacing the image of an existing question, you MUST NOT re-create the exercise or overwrite the questions with a full-sync endpoint. Save a pre-update snapshot first, then prepare the following for each image:

```json
{
  "schemaVersion": "pracmo-question-image-replace@v1",
  "clientRequestId": "replace-image-stable-id",
  "expectedOldUrl": "https://.../material/<accountId>/practice-assets/old.png",
  "newUrl": "https://.../material/<accountId>/practice-assets/new.png"
}
```

Use `pracmocli --env global exercises image-replace <trackId> <exerciseId> <questionId> <json-file>` (before submitting you may first run `pracmocli --env global validate replace-image <json-file>`). The server allows only the same trusted OSS host and the current account's `practiceAssets` prefix, and uses the old URL appearing exactly once as an optimistic lock; it modifies only the specified question's image URL and increments the exercise version, without rebuilding questions or options. Retrying the same request keeps the same ID and JSON; a rollback uses a new stable ID to replace in reverse.

For multiple images, maintain a ledger item by item and read back. You MUST confirm that exerciseId, questionId, optionId, question type, the non-image text of the question stem, options, correct answer, per-option explanations, order, plan and concept associations are all unchanged. The old images MUST be retained, to stay compatible with the frozen projection of in-progress plays.

## Idempotency and Feedback

- Retrying the same content MUST keep the same `clientRequestId` and JSON.
- Reusing the same ID with different content returns a conflict; after the content is substantially modified, generate a new ID.
- After a timeout, first retry with the same request; do not change the ID and manufacture duplicate exercises.
- After success, report the track title, `trackId`, exercise collection name, `collectionId`, exercise title, `exerciseId`, question count and image count, and note that the content belongs to the user and may later be promoted to public.
- Stop when the track does not exist, has ended, or does not belong to the API Key user; do not automatically switch to another track.

## Red Lines (Never Do)

- Creating a track, or calling any track-creation/`import`/`with-exercise` endpoint.
- Using model parameter memory, search snippets or a re-post that was not actually opened as factual evidence.
- Local layout/compositing of generated images (except when the user explicitly requests it, and it MUST be recorded).
- Filling in `review` falsely to pass validation, or skipping the compress → re-check → validate flow.
- Assembling URLs by hand and bypassing `images finalize`; silently falling back to the default collection by omitting `collectionId`.
- Inferring answers from public detail pages; creating while a gate has not passed.

## Exit Codes and Recovery Actions

Write operations are **not retried automatically** by default. Before submitting, you may use `--dry-run` to perform only local structural validation without sending a request.

| Code | Meaning | Recovery action |
|----|------|----------|
| 0 | Success | Parse the stdout JSON |
| 1 | Argument/usage error | Check `pracmocli help` and then fix the command; do not change the JSON content |
| 2 | Not logged in / credentials expired | Guide the user to `pracmocli --env global auth login` (or get a Key at `https://www.pracmo.app/app/api-key`); do not let the user send the Key into the chat |
| 3 | Business error (backend 4xx non-conflict) | Handle according to the stderr error message; when the track/collection is unauthorized or deleted, re-read the list and have the user confirm again |
| 4 | Network/timeout | **Retry with the same `clientRequestId` and exactly the same JSON**; you MUST NOT generate a new ID |
| 5 | Conflict (409 idempotency conflict) | Content unchanged → check the earlier result; content substantially modified → generate a new `clientRequestId` |
| 6 | Local gate not passed (validation failure) | After fixing the image/question stem, **re-run the full validation**; **MUST NOT create** |

> The output of `images validate` carries a `stage` field. **🛑 If `stage` does not match the stage you want, the arguments were not accepted correctly** — letting a request containing `asset://` through causes irreversible consequences, so you MUST stop and check the command.

## Version Requirement

Use the **latest** CLI (known issues in older versions are all fixed; treat the latest version as authoritative):

```bash
npm install -g @pracmo/pracmo-cli@latest --registry=https://registry.npmjs.org
```

For the command and exit-code cheat sheet see `references/cli-commands.md`; for read-back auditing, re-submitting after an environment or account change within the same region, and the relationship between public content and the source package, see `references/read-back-and-migration.md`.
