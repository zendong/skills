# Track Exercise JSON Contract

The top level allows only `schemaVersion`, `clientRequestId` and `exercise`. The version is fixed at `pracmo-track-exercise@v1`.

`clientRequestId` is 8–64 characters long and uses only letters, digits, dots, underscores and hyphens, with a first character that is a letter or a digit. Retrying the same semantic content MUST NOT change it.

`exercise` requires `title` and `questions`; the final submission MUST also include `collectionId`. `collectionId` is a real exercise collection ID of 1–64 characters, and it MUST come from the exercise-collection response for the target track that was just queried or just created; you MUST NOT pass a display name, a guessed value, or an ID belonging to another track. Draft/review packages may temporarily omit this field, so that a new exercise collection is only created after confirmation; `--stage finalized` MUST reject a missing value.

Optional fields include `userRequest`, `difficultyLevel`, and source and material context fields. It MUST NOT contain track creation information, public state, or share requests.

Every question MUST have `questionType`, `questionContent`, `concept`, `testableClaim`, `bloomLevel` and `options`. The question object MUST NOT contain explanation fields; all explanations go into the non-empty `options[].explanation`, and each MUST state the reason why its own option holds or does not hold — one generic explanation MUST NOT be used to cover the whole question.

`concept` is an object containing a non-empty `name` or `conceptId`, not a string. Single-choice and true/false questions have exactly one correct option, multiple-choice questions have at least two correct options; for these question types every option MUST contain `content`, a boolean `isCorrect` and a non-empty `explanation`. A short-answer question MUST have exactly one reference-answer option: `content` is an answer that can be graded deterministically, `isCorrect` is `true`, and `explanation` gives the grading points, the conditions under which it holds, and common omissions. The total number of questions is 3–100.

The Server saves exercises with the API Key account as the owner; the create API does not accept public/share parameters — public promotion happens through the public-content flow.

## Destination Contract

- Query exercise collections: `GET /open/v1/learning-tracks/:trackId/exercise-collections`
- Create an exercise collection: `POST /open/v1/learning-tracks/:trackId/exercise-collections`
- Create a finished exercise: `POST /open/v1/learning-tracks/:trackId/exercises`

In the final exercise request, `exercise.collectionId` MUST match the confirmed destination. The Server keeps default-collection compatibility for older clients when the value is omitted, but this skill MUST NOT use that compatibility path. The `collection.collectionId` in the success response is the actual underlying ownership, and it MUST be read back and verified.

## Images

The Server currently carries images through Markdown and does not use extra image fields. Images may appear in:

- `questions[].questionContent`
- `questions[].options[].content`

During authoring, use `![alt text](asset://asset-id)` and record sources and review in a separate `pracmo-exercise-images@v1` manifest. The final request MUST replace the placeholder with `![alt text](https://...)`, and the top level may still contain only `schemaVersion`, `clientRequestId` and `exercise`.

The final request forbids `asset://`, `file://`, local absolute/relative paths, base64/data URLs and plain HTTP images. The internal manifest, source list and review records MUST NOT be inserted into the API request.
