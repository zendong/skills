# Private Track Action JSON Contract

The top level allows only `schemaVersion`, `clientRequestId` and `action`. The version is fixed at `pracmo-track-action@v1`.

`clientRequestId` is 8–64 characters long and uses only letters, digits, dots, underscores and hyphens, with a first character that is a letter or a digit. Retrying the same content keeps it unchanged.

Fields required for every action: `title`, `scheduleType`, `timezone`, `startDate`, `deadlineLocalTime`, `completionMode`. `scheduleType` is `daily / weekdays / weekly_quota / once`; dates are `YYYY-MM-DD`, and the local deadline time is `HH:mm`.

Content modes: `self_directed` carries no generated content configuration and no follow-along plan; `puki_generated` carries `generatedContentConfig`; `follow_along` carries `followPlan`. The exact combination MUST satisfy the Server Action validation.

`followPlan.levels` contains 1–20 levels, and each level contains 1–20 `contentBlocks`. A text block uses a non-empty `textContent`; an image block uses `blockType=image`, a non-empty `caption` and `mediaUrl`. During authoring `mediaUrl` is `asset://<assetId>`; the final request MUST be an absolute HTTPS URL with a host.

Internal image source and review information is kept in a separate `pracmo-action-images@v1` manifest and is not sent to the Server. The final action JSON forbids `assetId`, manifest, `asset://`, `file://`, data URLs or local paths.

It MUST NOT carry accountId, trackId, sourceType, sourceRefId, publicActionId, catalog, review/publication status, runtime state, check-in or guardian data. The Server binds the owner and the active track from the URL and the API Key, and fixes the source as `open_api`.
