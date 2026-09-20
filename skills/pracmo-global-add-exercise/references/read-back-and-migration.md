# Read-Back Auditing and Collection Migration

> **Boundary**: this file only covers re-submission **within the same region** (such as pre↔prod inside the global deployment, or switching accounts). The China and global deployments do not share accounts, content or image assets — there is no cross-region migration, and content from one region must not be moved to another region.

A successful create ≠ the end of the job. After creation you MUST **read back and verify** ownership, question count, answers and explanations; and when re-submitting an existing exercise collection within the same region, handle IDs, images and forward compatibility.

## 1. Direct Open API access (the general way when the CLI has no read-back command)

- Header: `X-API-Key: <key>`. **The backend trusts `X-API-Key`, not `Authorization: Bearer`** (Bearer returns `missing API key` even when the Key is correct).
- Endpoints:
  - `GET /open/v1/flow/exercise/:exerciseId` → metadata: `questionCount`, `accessMode` (the current save state, not public), etc.
  - `GET /open/v1/flow/questions?exerciseId=<id>&limit=100` → the question list.

```bash
curl -s -H "X-API-Key: $PRACMO_API_KEY" \
  "https://apis.pracmo.app/open/v1/flow/questions?exerciseId=<exerciseId>&limit=100"
```

## 2. Read-back explanation semantics (important — do not report a missing explanation)

The read endpoint does **not** return `options[].explanation`; instead it **dynamically composes** the stored per-option explanations into the question's `question.explanation`:

- Objective questions (single/multiple choice, true/false): each item is `- **A** √/× <that option's explanation>`, joined by blank lines;
- Short answer: `question.explanation = options[0].explanation` (the explanation of the reference-answer option).

The correct audit method: use the local submission package to generate `expected_display_explanation(question)` by the same rule, and compare it **question by question** against the `question.explanation` from the read endpoint; also check the question type, stem, option `content`, `isCorrect`, `bloomLevel` and image URLs. Do **not** conclude that explanations are missing just because the read endpoint's options have no `explanation`.

## 3. Audit Skeleton (Python)

```python
import json, os, urllib.request, urllib.parse

BASE = "https://apis.pracmo.app/open/v1"

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

# Read back with the exerciseId from the creation response; compare against the local package question by question
for local, resp in zip(local_questions, api("flow/questions", {"exerciseId": exid, "limit": 100})):
    assert resp["questionType"] == local["questionType"]
    assert resp["questionContent"] == local["questionContent"]
    assert resp.get("explanation", "") == expected_display_explanation(local)
    assert [o["content"] for o in resp["options"]] == [o["content"] for o in local["options"]]
    assert [o["isCorrect"] for o in resp["options"]] == [o["isCorrect"] for o in local["options"]]
```

## 4. Re-submitting an existing exercise collection within the same region (environment/account switch)

- **An environment/account switch MUST use a new `clientRequestId`**: the same ID hits idempotency (409 or reuses the old result); only "retrying the same request after a timeout in the same environment" may keep the original ID.
- `collectionId` may only come from a response just read/just created in the **target environment** (an exercise collection ID from the previous environment is unauthorized for the current account and will be rejected).
- **Images MUST be finalized again to the target account with `images finalize`**: the old URLs point to the old account's `material/<oldAccountId>/practice-assets/`, which is uncontrollable across accounts (the old account may clean them up, or they may be unauthorized) and MUST NOT be written directly into the new request.
- Migrating an old manifest to the current contract: each asset MUST carry `sourceType` (`primary`/`official`/`standard`/`peer_reviewed`/`reputable_secondary`); a missing field is rejected by `images validate --stage reviewed`.
- When the content is unchanged, reuse the reviewed files: before uploading, compare SHA-256 against the old online OSS object to confirm the bytes are identical, append a re-check record to `assets[].review.notes` and update `reviewedAt`; do not change review conclusions out of thin air.

## 5. Public content detail ≠ the complete source

- The public detail endpoint (such as `/public/public-exercise-collections/:id`) provides only a **preview**: `options` are strings, with no answers and no explanations. **Do not infer answers from public detail pages**.
- When the full content is needed (correct answers, per-option explanations, images), use the source submission package (the local finalized JSON) or the admin review endpoint.
- Public snapshots cannot be reversed: reworking a historical public exercise collection must re-submit from the source package, not recover from the public detail.