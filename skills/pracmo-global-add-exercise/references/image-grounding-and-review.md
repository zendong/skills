# Grounding, Production and Strict Review of Exercise Images

This specification applies to question-stem images, option images, charts, flowcharts, maps, timelines, structural diagrams, and illustrations containing factual text. The goal is not "looks plausible" but making every decidable fact in the image traceable back to a reliable source that was actually read.

## 1. Ground first, draw later

Look for material in the following order:

1. Original material specified by the user and readable by you.
2. Official documentation, raw government or institutional data, formal standards, original papers, and first-hand explanations from the author or the project.
3. Teaching material from trustworthy institutions such as universities, museums and professional organizations.
4. Reliable secondary sources that have editorial review and can link back to the original evidence.

Search snippets, aggregator pages, unattributed reprints, social-media posts and model parameter memory MUST NOT be treated as the only evidence. When a fact is time-sensitive, record the source's publication date or version together with `retrievedAt`; for high-risk or disputed claims, prefer first-hand sources and cross-check — otherwise do not use the question.

You may retrieve existing images, or redraw them based on the evidence. Redrawing is usually better for copyright and clarity, but "drawing it yourself" does not mean sources may be omitted. Protected images MUST NOT be copied without permission; record the license, the public-domain status, or a note that it is an original redrawing.

## 2. Manifest Contract

Image manifest top level:

```json
{
  "schemaVersion": "pracmo-exercise-images@v1",
  "clientRequestId": "identical to the exercise request",
  "resources": [],
  "assets": []
}
```

Every `resources[]` contains at least:

- `resourceId`: an ID unique within this package.
- `title`, `publisher`, `url`, `retrievedAt`.
- `sourceType`: one of `primary`, `official`, `standard`, `peer_reviewed`, `reputable_secondary`.

Every `assets[]` contains at least:

```json
{
  "assetId": "kv-cache-flow",
  "localPath": "assets/kv-cache-flow.png",
  "altText": "KV cache reuse flow",
  "factuality": "factual",
  "provenance": "generated_from_sources",
  "sourceMode": "real_scene_generated",
  "sourceDetails": {
    "generationMethod": "Generate the whole complete image directly with the image generation tool",
    "resourceIds": ["resource-1"],
    "wholeImageGenerated": true,
    "localLayoutApplied": false
  },
  "license": "original",
  "claims": [
    {
      "claimId": "claim-1",
      "text": "the specific fact the image expresses",
      "resourceIds": ["resource-1"]
    }
  ],
  "expectedVisibleText": ["text that must appear verbatim"],
  "expectedRelations": ["the arrow from A points to B"],
  "containsNumbers": true,
  "expectedValues": [
    {
      "label": "label or metric in the image",
      "displayValue": "17.2%",
      "unit": "%",
      "resourceIds": ["resource-1"]
    }
  ],
  "usedBy": [{"questionIndex": 0, "field": "questionContent"}],
  "review": {}
}
```

When `factuality` is `factual`, `claims` is mandatory, and every claim references at least one registered resource. Purely geometric decoration, or an operational diagram that expresses no external fact, may use `non_factual`, but its text, logic and question answers MUST still be reviewed.

`containsNumbers` MUST be declared explicitly. When it is `true`, every number in the image that is used to understand or answer the question should be registered in `expectedValues`, preserving the exact display form such as the decimal point and percent sign in `displayValue` and citing a source; when there are many numbers you may register them by data series and explain the item-by-item comparison method in `notes` — spot-checking only is forbidden.

`usedBy.field` uses `questionContent` or `options[n].content`, and MUST match the actual location where `asset://` appears exactly.

### Source Mode Contract

- `web_downloaded`: `sourceDetails` MUST contain `resourceIds`, an HTTPS `originalUrl` consistent with the registered resource, and the `downloadSha256` of the original downloaded file; `license` MUST state the basis on which it may be used.
- `real_scene_generated`: `sourceDetails` MUST contain `generationMethod`, the `resourceIds` that support the scene and the facts, `wholeImageGenerated: true` and `localLayoutApplied: false`. The whole complete image MUST come directly from the image generation tool.
- No other source modes are allowed. When the real source or the real scene cannot be proven, delete the image reference and switch to a text-only question.

## 3. Production Requirements

- Local layout is forbidden by default. Pillow, Canvas, SVG, HTML/CSS, screenshot collages, post-production text overlay, perspective compositing or code drawing MUST NOT be used to change the visible content; you MUST NOT generate a base image first and then overlay text, numbers, UI, arrows, people or backgrounds onto it.
- Only compression, format conversion, metadata stripping and alpha-channel handling that do not change the visible content are allowed. The only exception is when the user explicitly requests local layout/compositing, and it MUST be recorded in `generationMethod`, the review notes and the delivery description.
- When a generated image has typos, pseudo-characters, wrong numbers, logical errors, wrong posture, brand/model leakage or insufficient authenticity, regenerate the whole image; patching it with local touch-ups or post-production layout is forbidden.
- Prefer original high-resolution material, or redraw from the evidence; blurry images that have been re-saved repeatedly are forbidden.
- An image contains only the information needed to answer; do not expose the answer directly through highlighting, file names, corner markers or in-image text.
- Design font sizes, line weights, whitespace and contrast for a phone screen; colour MUST NOT be the only means of distinguishing answers.
- After compression a single file MUST NOT exceed 512 KiB, and only PNG, JPEG and WebP are allowed.
- After replacement, compression, cropping or redrawing, all previous reviews are void: you MUST review the final file that is about to be uploaded.

## 4. Strict Comparison Checklist

You MUST actually open the file to be uploaded, magnify it, and compare it item by item against the manifest, the source pages and the exercise question:

- Text: check titles, labels, footnotes, proper nouns, capitalisation, spelling, symbols and language word by word.
- Values: check values, units, dimensions, ratios, percent signs, dates, precision, axis ticks and legends item by item.
- Structure: check nodes, arrows, order, direction, hierarchy, set relations, spatial correspondence and colour mapping.
- Facts: every `claim` can be directly supported by the source corresponding to its `resourceIds`; do not draw speculation as fact.
- Question: answer independently using only the image and the question stem, recompute the result, then compare item by item against the options, the correct answer and each option's explanation.
- Teaching: difficulty matches the Bloom level, the distractors have diagnostic value, and the image adds no extra ambiguity or answer leakage.
- Presentation: still clear when viewed at phone width, no obvious compression artifacts, and the key distinctions remain understandable under colour-vision deficiency or in grayscale.

OCR can be used to find missing characters, but it cannot prove that the text is correct; automated image similarity can only prove that files are near-identical, and cannot prove that facts, logic or answers are correct.

When the review passes, write:

```json
{
  "sourceVerified": true,
  "pixelInspected": true,
  "textVerified": true,
  "logicVerified": true,
  "numbersVerified": true,
  "questionAnswerVerified": true,
  "mobileReadabilityVerified": true,
  "answerLeakageChecked": true,
  "authenticityVerified": true,
  "scenePlausibilityVerified": true,
  "deviceNeutralityVerified": true,
  "privacyVerified": true,
  "reviewedAt": "ISO-8601 timestamp",
  "notes": "record specifically which text, numbers and relations were checked, and the result of answering independently"
}
```

You MUST NOT fill in `true` dishonestly in order to pass the script. If any item cannot be confirmed, it MUST remain in a failing state: fix or delete the image, and do not continue with upload and creation.

The authenticity and privacy review MUST additionally confirm: the image is not a low-fidelity card or placeholder UI; the layout, perspective and operation in a real scene are plausible; the phone carries no vendor- or model-specific characteristics; and the image contains no real names, phone numbers, accounts, order numbers, addresses, routable links, QR codes, bank cards or recognizable brands. If the image expresses objective knowledge, all text, numbers and states MUST be traced back to the resources and checked item by item.
