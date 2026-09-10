# Follow-Along Image Grounding and Strict Review

This specification applies to the image blocks of `followPlan.levels[].contentBlocks[]`. The value of an image is to demonstrate an observable movement accurately, not to decorate.

## Source Priority

1. Original material provided by the user and actually read.
2. Official health/sports guidelines, formal standards, original papers, or first-hand explanations of the movement system.
3. Material from professional organizations, universities, hospitals or public institutions.
4. Reliable secondary material that can link back to first-hand evidence.

Search snippets, unattributed reprints, social-media content and model parameter memory cannot serve as the sole evidence. Health, safety or injury-related content counts as high-risk fact; when sources are insufficient or conflict with each other, stop and do not invent a generic conclusion.

## Manifest Contract

The top level uses `pracmo-action-images@v1`, with a `clientRequestId` consistent with the action, and contains `resources` and `assets`. Each resource records a unique `resourceId`, `title`, `publisher`, HTTPS `url`, `sourceType`, `retrievedAt`, and either `version` or `publishedAt`. `sourceType` allows only `primary`, `official`, `standard`, `peer_reviewed`, `reputable_secondary`.

Each asset:

```json
{
  "assetId": "wall-pushup-start",
  "localPath": "assets/wall-pushup-start.png",
  "altText": "Wall push-up starting position",
  "factuality": "factual",
  "provenance": "generated_from_sources",
  "sourceMode": "real_scene_generated",
  "sourceDetails": {
    "generationMethod": "Generate the whole complete image directly with the image generation tool",
    "resourceIds": ["r1"],
    "wholeImageGenerated": true,
    "localLayoutApplied": false
  },
  "license": "original",
  "claims": [{"claimId": "claim-1", "text": "the fact the image expresses in full", "resourceIds": ["r1"]}],
  "expectedVisibleText": [],
  "containsNumbers": false,
  "expectedValues": [],
  "expectedRelations": [{"subject": "torso", "relation": "maintains", "object": "a stable straight line", "notes": "starting position"}],
  "usedBy": [{"levelIndex": 0, "blockIndex": 1}],
  "review": {}
}
```

When the image contains numbers needed to perform the movement, set `containsNumbers` to true and register `label`, the exact `displayValue`, an optional `unit` and `resourceIds` in `expectedValues` for every value; spot-checking numbers is forbidden. A local path MUST be a relative path inside the manifest directory; absolute paths, `..` and symlinks pointing outside the directory are forbidden.

## Production Boundaries

- `web_downloaded` registers the original HTTPS URL, the download SHA-256, the resource ID and the license; `real_scene_generated` registers the generation method, the resource IDs, `wholeImageGenerated: true` and `localLayoutApplied: false`.
- Local layout is forbidden by default for generated images: Pillow, Canvas, SVG, HTML/CSS, screenshot collages, post-production text overlay, perspective compositing or code drawing MUST NOT be used to change the visible content, and a generated base image MUST NOT be combined a second time with movements, labels, arrows, equipment or backgrounds.
- Only compression, format conversion, metadata stripping and alpha-channel handling that do not change the visible content are allowed. Unless the user explicitly requests local layout/compositing, any typo, wrong number, wrong posture, wrong equipment position, safety problem or lack of authenticity requires regenerating the whole image.

## Review

You MUST open the final compressed file that is about to be uploaded, magnify it, and compare item by item: text and numbers; body, joint, support-point and equipment positions; arrows, mirroring, movement direction and steps; consistency with the caption, the level goal, the training volume and the progression criteria; warm-up, breathing, stopping conditions and risks; phone readability and compression artifacts.

When it passes, write:

```json
{
  "sourceVerified": true,
  "pixelInspected": true,
  "textVerified": true,
  "numbersVerified": true,
  "motionLogicVerified": true,
  "planConsistencyVerified": true,
  "safetyVerified": true,
  "mobileReadabilityVerified": true,
  "misleadingCueChecked": true,
  "reviewedSha256": "64-character lowercase SHA-256 of the compressed file",
  "reviewedAt": "ISO-8601",
  "notes": "record specifically the results of checking posture, relations, safety conditions and plan consistency"
}
```

You MUST NOT fill in true dishonestly in order to pass the script. After the image changes, the SHA will no longer match, and it MUST be reviewed again.
