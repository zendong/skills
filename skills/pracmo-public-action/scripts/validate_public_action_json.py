#!/usr/bin/env python3
"""Validate a pracmo-public-action@v2 authoring or finalized payload."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ALLOWED_TOP_LEVEL = {"schemaVersion", "clientRequestId", "catalog", "template", "assets"}
ALLOWED_TEMPLATE = {
    "title", "description", "iconCode", "colorCode", "scheduleType", "scheduleConfigJson",
    "timezone", "deadlineLocalTime", "gracePolicy", "completionMode", "contentMode",
    "generatedContentConfig", "followPlan",
}
ALLOWED_SCHEDULES = {"daily", "weekdays", "weekly_quota", "once"}
ALLOWED_GRACE = {"none", "two_hours", "next_day_noon"}
ALLOWED_COMPLETION = {"one_tap", "text", "rich_media"}
ALLOWED_AFTER = {"continue_last_level", "end_action"}
ALLOWED_CONTENT_MODES = {"self_directed", "puki_generated", "follow_along"}
ALLOWED_GENERATED_TYPES = {"reading", "quick_qa"}
ALLOWED_QUESTION_TYPES = {"auto", "single_choice", "multiple_choice", "true_false", "short_answer", "mixed"}
MAX_PUBLIC_IMAGE_BYTES = 512 * 1024


class ContractError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def reject_unknown(value: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = set(value) - allowed
    require(not unknown, f"unknown {path} fields: {', '.join(sorted(unknown))}")


def text_field(value: Any, path: str, *, maximum: int, allow_empty: bool = False) -> str:
    require(isinstance(value, str), f"{path} must be a string")
    value = value.strip()
    require(allow_empty or bool(value), f"{path} is required")
    require(len(value) <= maximum, f"{path} exceeds {maximum} characters")
    return value


def validate_local_path(value: Any, path: str, base_dir: Path, check_assets: bool) -> None:
    raw = text_field(value, path, maximum=240)
    posix = PurePosixPath(raw.replace("\\", "/"))
    require(not posix.is_absolute() and ".." not in posix.parts, f"{path} must be a safe relative path")
    require(not raw.startswith(("file:", "data:")), f"{path} must be a safe relative path")
    if check_assets:
        local_file = base_dir / Path(*posix.parts)
        require(local_file.is_file(), f"{path} does not exist")
        require(
            0 < local_file.stat().st_size <= MAX_PUBLIC_IMAGE_BYTES,
            f"{path} must be 512 KiB or smaller before OSS upload",
        )


def canonical_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate(payload: Any, *, base_dir: Path, check_assets: bool = False, finalized: bool = False) -> dict[str, Any]:
    require(isinstance(payload, dict), "root must be an object")
    unknown = set(payload) - ALLOWED_TOP_LEVEL
    require(not unknown, f"unknown root fields: {', '.join(sorted(unknown))}")
    require(payload.get("schemaVersion") == "pracmo-public-action@v2", "schemaVersion must be pracmo-public-action@v2")
    client_request_id = text_field(payload.get("clientRequestId"), "clientRequestId", maximum=128)
    require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}", client_request_id)), "clientRequestId has invalid characters or length")

    catalog = payload.get("catalog")
    require(isinstance(catalog, dict), "catalog must be an object")
    reject_unknown(catalog, {"category", "tags", "coverImage"}, "catalog")
    text_field(catalog.get("category"), "catalog.category", maximum=64)
    tags = catalog.get("tags")
    require(isinstance(tags, list) and len(tags) <= 8, "catalog.tags must contain at most 8 items")
    for index, tag in enumerate(tags):
        text_field(tag, f"catalog.tags[{index}]", maximum=32)

    assets = payload.get("assets")
    require(isinstance(assets, list) and 1 <= len(assets) <= 41, "assets must contain 1 to 41 items")
    asset_ids: set[str] = set()
    covers = 0
    for index, asset in enumerate(assets):
        path = f"assets[{index}]"
        require(isinstance(asset, dict), f"{path} must be an object")
        reject_unknown(asset, {"assetId", "role", "localPath", "objectKey", "url", "alt", "sha256", "contentType", "sizeBytes", "width", "height"}, path)
        asset_id = text_field(asset.get("assetId"), f"{path}.assetId", maximum=64)
        require(asset_id not in asset_ids, f"{path}.assetId is duplicated")
        asset_ids.add(asset_id)
        role = asset.get("role")
        require(role in {"cover", "content"}, f"{path}.role must be cover or content")
        covers += int(role == "cover")
        text_field(asset.get("alt"), f"{path}.alt", maximum=120)
        has_local = "localPath" in asset
        has_remote = bool(asset.get("objectKey")) and bool(asset.get("url"))
        require(has_local != has_remote, f"{path} must use either localPath or finalized objectKey/url")
        if has_local:
            require(not finalized, f"{path}.localPath is not allowed in finalized payload")
            validate_local_path(asset["localPath"], f"{path}.localPath", base_dir, check_assets)
        else:
            require(str(asset["url"]).startswith("https://"), f"{path}.url must use https")
            require(bool(re.fullmatch(r"[a-f0-9]{64}", str(asset.get("sha256", "")))), f"{path}.sha256 is invalid")
            require(asset.get("contentType") in {"image/png", "image/jpeg", "image/webp"}, f"{path}.contentType is invalid")
            require(
                isinstance(asset.get("sizeBytes"), int) and 0 < asset["sizeBytes"] <= MAX_PUBLIC_IMAGE_BYTES,
                f"{path}.sizeBytes must be 512 KiB or smaller",
            )
    require(covers == 1, "assets must contain exactly one cover")

    cover = catalog.get("coverImage")
    require(isinstance(cover, dict), "catalog.coverImage must be an object")
    reject_unknown(cover, {"localPath", "objectKey", "url", "alt"}, "catalog.coverImage")
    text_field(cover.get("alt"), "catalog.coverImage.alt", maximum=120)
    if "localPath" in cover:
        require(not finalized, "catalog.coverImage.localPath is not allowed in finalized payload")
        validate_local_path(cover["localPath"], "catalog.coverImage.localPath", base_dir, check_assets)
    else:
        require(str(cover.get("url", "")).startswith("https://") and bool(cover.get("objectKey")), "catalog.coverImage must use localPath or finalized objectKey/url")

    template = payload.get("template")
    require(isinstance(template, dict), "template must be an object")
    reject_unknown(template, ALLOWED_TEMPLATE, "template")
    required_template = {"title", "description", "iconCode", "colorCode", "scheduleType", "scheduleConfigJson", "timezone", "deadlineLocalTime", "gracePolicy", "completionMode", "contentMode"}
    missing_template = required_template - set(template)
    require(not missing_template, f"missing template fields: {', '.join(sorted(missing_template))}")
    text_field(template.get("title"), "template.title", maximum=80)
    text_field(template.get("description", ""), "template.description", maximum=500, allow_empty=True)
    text_field(template.get("iconCode"), "template.iconCode", maximum=32)
    text_field(template.get("colorCode"), "template.colorCode", maximum=32)
    require(template.get("scheduleType") in ALLOWED_SCHEDULES, "template.scheduleType is invalid")
    schedule_config = text_field(template.get("scheduleConfigJson"), "template.scheduleConfigJson", maximum=1024)
    try:
        parsed_config = json.loads(schedule_config)
    except json.JSONDecodeError as exc:
        raise ContractError("template.scheduleConfigJson must contain valid JSON") from exc
    require(isinstance(parsed_config, dict), "template.scheduleConfigJson must encode an object")
    text_field(template.get("timezone"), "template.timezone", maximum=64)
    require(bool(re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(template.get("deadlineLocalTime", "")))), "template.deadlineLocalTime must use HH:mm")
    require(template.get("gracePolicy") in ALLOWED_GRACE, "template.gracePolicy is invalid")
    completion_mode = template.get("completionMode")
    require(completion_mode in ALLOWED_COMPLETION, "template.completionMode is invalid")
    content_mode = template.get("contentMode")
    require(content_mode in ALLOWED_CONTENT_MODES, "template.contentMode is invalid")
    generated = template.get("generatedContentConfig")
    plan = template.get("followPlan")
    follow_after = template.get("followAfterCompletionPolicy")

    if content_mode == "self_directed":
        require(generated is None, "template.generatedContentConfig is not allowed for self_directed")
        require(plan is None, "template.followPlan is not allowed for self_directed")
        require(follow_after is None, "template.followAfterCompletionPolicy is not allowed for self_directed")
        return payload

    if content_mode == "puki_generated":
        require(completion_mode == "one_tap", "puki_generated actions require one_tap completionMode")
        require(plan is None, "template.followPlan is not allowed for puki_generated")
        require(follow_after is None, "template.followAfterCompletionPolicy is not allowed for puki_generated")
        require(isinstance(generated, dict), "template.generatedContentConfig must be an object")
        reject_unknown(generated, {"schemaVersion", "type", "instruction", "quickQa"}, "generatedContentConfig")
        require(generated.get("schemaVersion") == 1, "template.generatedContentConfig.schemaVersion must be 1")
        generated_type = generated.get("type")
        require(generated_type in ALLOWED_GENERATED_TYPES, "template.generatedContentConfig.type is invalid")
        text_field(generated.get("instruction"), "template.generatedContentConfig.instruction", maximum=1000)
        quick_qa = generated.get("quickQa")
        if generated_type == "reading":
            require(quick_qa is None, "template.generatedContentConfig.quickQa is not allowed for reading")
        else:
            require(isinstance(quick_qa, dict), "template.generatedContentConfig.quickQa must be an object")
            reject_unknown(quick_qa, {"questionType"}, "quickQa")
            require(quick_qa.get("questionType") in ALLOWED_QUESTION_TYPES, "template.generatedContentConfig.quickQa.questionType is invalid")
        return payload

    require(completion_mode == "one_tap", "follow_along actions require one_tap completionMode")
    require(generated is None, "template.generatedContentConfig is not allowed for follow_along")
    require(isinstance(plan, dict), "template.followPlan must be an object")
    reject_unknown(plan, {"afterCompletionPolicy", "levels", "checkpoints"}, "followPlan")
    require(plan.get("afterCompletionPolicy") in ALLOWED_AFTER, "template.followPlan.afterCompletionPolicy is invalid")
    levels = plan.get("levels")
    require(isinstance(levels, list) and 1 <= len(levels) <= 20, "template.followPlan.levels must contain 1 to 20 levels")
    used_content_assets: set[str] = set()
    for level_index, level in enumerate(levels):
        path = f"template.followPlan.levels[{level_index}]"
        require(isinstance(level, dict), f"{path} must be an object")
        reject_unknown(level, {"title", "description", "targetSessions", "promotionCriterion", "estMinutes", "contentBlocks"}, path)
        text_field(level.get("title"), f"{path}.title", maximum=80)
        blocks = level.get("contentBlocks")
        require(isinstance(blocks, list) and 1 <= len(blocks) <= 20, f"{path}.contentBlocks must contain 1 to 20 blocks")
        for block_index, block in enumerate(blocks):
            block_path = f"{path}.contentBlocks[{block_index}]"
            require(isinstance(block, dict), f"{block_path} must be an object")
            reject_unknown(block, {"blockType", "textContent", "assetId", "mediaUrl", "caption", "durationSeconds"}, block_path)
            if block.get("blockType") == "text":
                text_field(block.get("textContent"), f"{block_path}.textContent", maximum=10000)
            elif block.get("blockType") == "image":
                asset_id = text_field(block.get("assetId"), f"{block_path}.assetId", maximum=64)
                require(asset_id in asset_ids, f"{block_path}.assetId does not exist in assets")
                used_content_assets.add(asset_id)
                if finalized:
                    require(str(block.get("mediaUrl", "")).startswith("https://"), f"{block_path}.mediaUrl is required in finalized payload")
            else:
                raise ContractError(f"{block_path}.blockType must be text or image")

    checkpoints = plan.get("checkpoints", [])
    require(isinstance(checkpoints, list) and len(checkpoints) <= 40, "template.followPlan.checkpoints must be an array")
    for index, checkpoint in enumerate(checkpoints):
        path = f"template.followPlan.checkpoints[{index}]"
        require(isinstance(checkpoint, dict), f"{path} must be an object")
        reject_unknown(checkpoint, {"levelIndex", "title", "description", "isKey"}, path)
        level_index = checkpoint.get("levelIndex")
        require(isinstance(level_index, int) and 0 <= level_index < len(levels), f"{path}.levelIndex must refer to an existing level")
        text_field(checkpoint.get("title"), f"{path}.title", maximum=80)
        require(isinstance(checkpoint.get("isKey"), bool), f"{path}.isKey must be boolean")

    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--check-assets", action="store_true")
    parser.add_argument("--finalized", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        validate(payload, base_dir=args.input.parent, check_assets=args.check_assets, finalized=args.finalized)
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 2
    digest = hashlib.sha256(canonical_payload(payload)).hexdigest()
    result = {"valid": True, "payloadHash": digest, "schemaVersion": payload["schemaVersion"]}
    print(json.dumps(result, ensure_ascii=False) if args.json else f"valid {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
