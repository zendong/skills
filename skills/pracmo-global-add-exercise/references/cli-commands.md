# pracmocli Command Reference

All business commands print JSON to stdout (`exit 0` on success); error messages go to stderr, and the exit codes are listed in the table below.

> **Argument order**: write flags **before** positional arguments (`pracmocli images validate --stage reviewed <file>`).
> The CLI accepts both orders, but this form is the least error-prone and makes word-for-word comparison with the examples easy.

## Commands

| Command | Purpose | Required |
|------|------|------|
| `pracmocli auth login` | Issue a binding code and print the authorization URL (no leading/trailing whitespace, no quotes, within 10 seconds) | none |
| `pracmocli auth status` | Login state check (no side effects, idempotent); the output contains `"logged in"` when logged in | none |
| `pracmocli auth logout` | Revoke the binding and clear local credentials (idempotent, returns 0 even when not logged in) | none |
| `pracmocli tracks list [keyword]` | List active tracks (`state=active&pageSize=100`) | none |
| `pracmocli collections list <trackId>` | List exercise collections | trackId |
| `pracmocli collections create <trackId> <file>` | Create an exercise collection (JSON: `name`/`clientRequestId`/optional `description`) | trackId + file |
| `pracmocli exercises add <trackId> <file>` | Create a finished exercise → `POST /open/v1/learning-tracks/:id/exercises` | trackId + file |
| `pracmocli exercises image-replace <trackId> <exerciseId> <questionId> <file>` | Replace a question image in place (`PATCH …/image-url`) | 3 IDs + file |
| `pracmocli actions add <trackId> <file>` | Create an action → `POST /open/v1/learning-tracks/:id/actions` | trackId + file |
| `pracmocli validate exercise\|action\|collection\|replace-image <file>` | Pre-submit structural validation (`--manifest`/`--stage` below) | file |
| `pracmocli images compress --manifest <m> [-o out] <authoring.json>` | Compress images to ≤512 KiB and clear `review` pending re-review | manifest + authoring |
| `pracmocli images validate --stage reviewed\|finalized [--manifest <m>] [--type exercise\|action] <file>` | Hard gate validation | file (the reviewed stage also requires a manifest) |
| `pracmocli images finalize --manifest <m> -o <out> [--final-manifest <f>] [--type exercise\|action] <authoring.json>` | Direct OSS upload + hash read-back + `asset://` replacement with HTTPS | manifest + out + authoring |
| `pracmocli doctor` | Environment self-check (variables/credentials/**connectivity**, read-only) | none |
| `pracmocli version` | Print the version | none |

**Common flag for write commands**: `--dry-run` — performs only local JSON structural validation and sends no request at all.

**Semantics of the validation stages** (always confirm that `stage` in the output matches your expectation):

| Stage | Purpose | Requires `collectionId` |
|------|------|------------------------|
| `reviewed` | After image review, before upload | No |
| `finalized` | The final request (with `asset://` already replaced) | **Yes** |

## Exit codes

> This table is kept in sync with the "Exit Codes and Recovery Actions" section in SKILL.md.

| Code | Meaning | Handling |
|----|------|----------|
| 0 | Success | Parse the stdout JSON |
| 1 | Argument/usage error | Check `pracmocli help` |
| 2 | Not logged in / credentials expired | Guide the user to `pracmocli auth login` |
| 3 | Business error (backend 4xx non-conflict) | Recover according to the stderr error message |
| 4 | Network/timeout | Retry with the **same `clientRequestId` and the same JSON** |
| 5 | Conflict (409 idempotency conflict) | Content unchanged → check the earlier result; content changed → use a new ID |
| 6 | Local gate not passed (validation failure) | After fixing the image/question stem, re-validate; **MUST NOT create** |

## Global flags

| Flag | Description |
|------|------|
| `--base <url>` | Backend Open API address (highest priority) |
| `--env <name>` | Preset `prod` / `pre` / `global` / `local` |

Priority: command-line flags > environment variables > preset > built-in default.

## Environment variables

| Variable | Default | Description |
|------|------|------|
| `PRACMO_OPEN_API_BASE` | `https://apis.pracmo.app/open/v1` | Backend address |
| `PRACMO_ENV` | `prod` | Preset: `prod` (China production) / `pre` (China pre-release) / `global` (global production) / `local` |
| `PRACMO_API_KEY` | empty | API Key (takes priority over the credentials file) |
| `PRACMO_CREDENTIALS_DIR` | `~/.pracmo` | Credentials directory (0600, valid across restarts, isolated per environment as `credentials.<env>.json`) |
| `PRACMO_HTTP_TIMEOUT_SECONDS` | 120 | HTTP timeout; write commands such as `exercises add` can exceed 30s in practice |
| `PRACMO_LOG_LEVEL` | `info` | Log level `debug`/`info`/`warn`/`error` |
| `PRACMO_OSS_ENDPOINT` / `PRACMO_OSS_BUCKET` | taken from backend STS | Integration overrides only (such as a local minio) |

> The CLI's built-in default for `PRACMO_ENV` is `prod` (China production). Every command in
> this skill passes `--env global` explicitly, so a different `PRACMO_ENV` on your machine
> cannot send requests to the wrong region.

## Write-command timeout recovery

If `exercises add` returns exit code 4 (client timeout), **the backend may already have created it**. Retry with the **same `clientRequestId` + exactly the same JSON**: an idempotency hit returns the same `exerciseId` (measured in practice); only changing the ID creates duplicate exercises. If it keeps timing out, increase `PRACMO_HTTP_TIMEOUT_SECONDS`.

## Common response shape

```json
{ "success": true, "data": { "trackId": "track_xxx", "title": "Linear Algebra" }, "code": "SUCCESS", "message": "success" }
```

> Note: the backend also returns HTTP 200 for **business errors**, expressing failure through `success:false` + `code`
> (for example, an unknown or expired binding code returns `NOT_FOUND`). The CLI already classifies correctly by `success` and `code`,
> so simply read the exit code — do not look only at the HTTP status.

## Troubleshooting and Experience

> Use the **latest** CLI (known issues in older versions are all fixed): `npm install -g @pracmo/pracmo-cli@latest --registry=https://registry.npmjs.org`; upgrade first before troubleshooting.

| Symptom | Cause | Handling |
|---|---|---|
| `invalid API key` after switching environments | API Keys are **not interchangeable** across prod/pre/global | First run `pracmocli --env global doctor` to check `baseUrl`; use the Key for the target environment |
| `exercises add` client timeout (exit code 4) | Server-side question creation and concept association can take 1–5 minutes, so the default 120s is not enough | `PRACMO_HTTP_TIMEOUT_SECONDS=300`; on timeout retry with the **same clientRequestId and the same JSON** — `reusedExisting: true` in the response means the idempotency hit and nothing was duplicated |
| Read-back shows options without `explanation` | The read endpoint **dynamically composes** the per-option explanations into a question-level `question.explanation`, which is by design | Compare question by question using the composition rules in `references/read-back-and-migration.md`; do not report a missing explanation |
| An old manifest is rejected by `images validate --stage reviewed` after migrating to the current contract | The asset is missing `sourceType` (primary/official/standard/peer_reviewed/reputable_secondary) | Add it and validate again |
| The public detail endpoint has no answers or explanations | The public preview provides only the options strings | Use the source submission package or the admin review side; do not infer answers from public detail pages |

> Read-back auditing, re-submitting after an environment or account change within the same region, and the relationship between public content and the source package are covered in `references/read-back-and-migration.md`.
