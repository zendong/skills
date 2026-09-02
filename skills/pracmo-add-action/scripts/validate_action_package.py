#!/usr/bin/env python3
"""Validate grounded private-action image packages and finalized API requests."""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

try:
    from PIL import Image
except ImportError:
    Image = None

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$")
ASSET_URL_RE = re.compile(r"^asset://([A-Za-z0-9][A-Za-z0-9._-]{0,63})$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
MAX_IMAGE_BYTES = 512 * 1024
SOURCE_TYPES = {"primary", "official", "standard", "peer_reviewed", "reputable_secondary"}
SOURCE_MODES = {"web_downloaded", "real_scene_generated"}
REVIEW_FLAGS = (
    "sourceVerified",
    "pixelInspected",
    "textVerified",
    "numbersVerified",
    "motionLogicVerified",
    "planConsistencyVerified",
    "safetyVerified",
    "mobileReadabilityVerified",
    "misleadingCueChecked",
)


class ContractError(ValueError):
    pass


def fail(message):
    raise ContractError(message)


def require_text(value, path):
    if not isinstance(value, str) or not value.strip():
        fail(f"{path} must be a non-empty string")
    return value.strip()


def is_https(value):
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_date(value, path):
    require_text(value, path)
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        fail(f"{path} must use YYYY-MM-DD")


def validate_request_shape(request, stage="authoring"):
    if not isinstance(request, dict):
        fail("request must be an object")
    allowed = {"schemaVersion", "clientRequestId", "action"}
    if set(request) != allowed:
        fail(f"request top-level keys must be exactly {sorted(allowed)}")
    if request.get("schemaVersion") != "pracmo-track-action@v1":
        fail("unsupported schemaVersion")
    request_id = request.get("clientRequestId", "")
    if not isinstance(request_id, str) or not REQUEST_ID_RE.fullmatch(request_id):
        fail("clientRequestId format is invalid")
    action = request.get("action")
    if not isinstance(action, dict):
        fail("action must be an object")
    for field in ("title", "scheduleType", "timezone", "startDate", "deadlineLocalTime", "completionMode"):
        require_text(action.get(field), f"action.{field}")
    if action["scheduleType"] not in {"daily", "weekdays", "weekly_quota", "once"}:
        fail("action.scheduleType is invalid")
    validate_date(action["startDate"], "action.startDate")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", action["deadlineLocalTime"]):
        fail("action.deadlineLocalTime must use HH:mm")
    mode = str(action.get("contentMode", "self_directed")).strip()
    generated = action.get("generatedContentConfig")
    plan = action.get("followPlan")
    if mode == "self_directed":
        if generated is not None or plan is not None:
            fail("self_directed action cannot contain generatedContentConfig or followPlan")
    elif mode == "puki_generated":
        if not isinstance(generated, dict) or plan is not None:
            fail("puki_generated action requires generatedContentConfig and forbids followPlan")
    elif mode == "follow_along":
        if action["completionMode"] != "one_tap" or generated is not None or not isinstance(plan, dict):
            fail("follow_along action requires one_tap, followPlan, and no generatedContentConfig")
        validate_follow_plan(plan, stage)
    else:
        fail("action.contentMode is invalid")


def validate_follow_plan(plan, stage):
    if plan.get("afterCompletionPolicy", "continue_last_level") not in {"continue_last_level", "end_action"}:
        fail("followPlan.afterCompletionPolicy is invalid")
    levels = plan.get("levels")
    if not isinstance(levels, list) or not 1 <= len(levels) <= 20:
        fail("followPlan.levels must contain 1 to 20 levels")
    for level_index, level in enumerate(levels):
        path = f"followPlan.levels[{level_index}]"
        if not isinstance(level, dict):
            fail(f"{path} must be an object")
        require_text(level.get("title"), f"{path}.title")
        blocks = level.get("contentBlocks")
        if not isinstance(blocks, list) or not 1 <= len(blocks) <= 20:
            fail(f"{path}.contentBlocks must contain 1 to 20 blocks")
        for block_index, block in enumerate(blocks):
            block_path = f"{path}.contentBlocks[{block_index}]"
            if not isinstance(block, dict):
                fail(f"{block_path} must be an object")
            block_type = str(block.get("blockType", "text")).strip()
            if block_type == "text":
                require_text(block.get("textContent"), f"{block_path}.textContent")
            elif block_type == "image":
                media_url = require_text(block.get("mediaUrl"), f"{block_path}.mediaUrl")
                require_text(block.get("caption"), f"{block_path}.caption")
                if stage == "authoring" and not ASSET_URL_RE.fullmatch(media_url):
                    fail(f"{block_path}.mediaUrl must use asset://<assetId> while authoring")
                if stage == "finalized" and not is_https(media_url):
                    fail(f"{block_path}.mediaUrl must be an absolute HTTPS URL")
            else:
                fail(f"{block_path}.blockType must be text or image")
    checkpoints = plan.get("checkpoints", [])
    if not isinstance(checkpoints, list) or len(checkpoints) > 40:
        fail("followPlan.checkpoints is invalid")
    for index, checkpoint in enumerate(checkpoints):
        if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("levelIndex"), int):
            fail(f"followPlan.checkpoints[{index}] is invalid")
        if not 0 <= checkpoint["levelIndex"] < len(levels):
            fail(f"followPlan.checkpoints[{index}].levelIndex is invalid")
        require_text(checkpoint.get("title"), f"followPlan.checkpoints[{index}].title")


def collect_asset_uses(request):
    uses = {}
    plan = request.get("action", {}).get("followPlan") or {}
    for level_index, level in enumerate(plan.get("levels", [])):
        for block_index, block in enumerate(level.get("contentBlocks", [])):
            if not isinstance(block, dict) or str(block.get("blockType", "")).strip() != "image":
                continue
            match = ASSET_URL_RE.fullmatch(str(block.get("mediaUrl", "")).strip())
            if match:
                uses.setdefault(match.group(1), set()).add((level_index, block_index))
    return uses


def safe_local_path(base_dir, value, path):
    require_text(value, path)
    posix = PurePosixPath(value.replace("\\", "/"))
    if posix.is_absolute() or ".." in posix.parts:
        fail(f"{path} must be a package-relative path")
    local = base_dir.joinpath(*posix.parts)
    try:
        local.resolve(strict=True).relative_to(base_dir.resolve(strict=True))
    except (OSError, ValueError):
        fail(f"{path} must resolve to an existing file inside the package")
    return local


def verify_image(local, path):
    if not local.is_file() or not 0 < local.stat().st_size <= MAX_IMAGE_BYTES:
        fail(f"{path} must be a non-empty image no larger than 512 KiB")
    if Image is None:
        fail("Pillow is required: python3 -m pip install Pillow")
    try:
        with Image.open(local) as opened:
            opened.verify()
            if opened.format not in {"PNG", "JPEG", "WEBP"}:
                fail(f"{path} must be PNG, JPEG, or WebP")
    except (OSError, SyntaxError) as exc:
        fail(f"{path} is not a valid image: {exc}")


def validate_package(request, manifest, base_dir, stage="reviewed"):
    if stage not in {"draft", "reviewed"}:
        fail("stage must be draft or reviewed")
    validate_request_shape(request, stage="authoring")
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != "pracmo-action-images@v1":
        fail("manifest schemaVersion must be pracmo-action-images@v1")
    if manifest.get("clientRequestId") != request["clientRequestId"]:
        fail("manifest clientRequestId must match request")
    resources = manifest.get("resources")
    assets = manifest.get("assets")
    if not isinstance(resources, list) or not isinstance(assets, list):
        fail("manifest resources and assets must be arrays")

    resource_ids = set()
    for index, resource in enumerate(resources):
        path = f"resources[{index}]"
        if not isinstance(resource, dict):
            fail(f"{path} must be an object")
        resource_id = require_text(resource.get("resourceId"), f"{path}.resourceId")
        if resource_id in resource_ids:
            fail(f"duplicate resourceId: {resource_id}")
        resource_ids.add(resource_id)
        for field in ("title", "publisher", "retrievedAt"):
            require_text(resource.get(field), f"{path}.{field}")
        if not (resource.get("version") or resource.get("publishedAt")):
            fail(f"{path} requires version or publishedAt")
        if resource.get("sourceType") not in SOURCE_TYPES:
            fail(f"{path}.sourceType is not trusted")
        if not is_https(str(resource.get("url", ""))):
            fail(f"{path}.url must be HTTPS")

    actual_uses = collect_asset_uses(request)
    asset_ids = set()
    claim_ids = set()
    for index, asset in enumerate(assets):
        path = f"assets[{index}]"
        if not isinstance(asset, dict):
            fail(f"{path} must be an object")
        asset_id = require_text(asset.get("assetId"), f"{path}.assetId")
        if not ASSET_URL_RE.fullmatch(f"asset://{asset_id}") or asset_id in asset_ids:
            fail(f"{path}.assetId is invalid or duplicated")
        asset_ids.add(asset_id)
        for field in ("altText", "provenance", "license"):
            require_text(asset.get(field), f"{path}.{field}")
        source_mode = asset.get("sourceMode")
        if source_mode not in SOURCE_MODES:
            fail(f"{path}.sourceMode must be web_downloaded or real_scene_generated")
        source_details = asset.get("sourceDetails")
        if not isinstance(source_details, dict):
            fail(f"{path}.sourceDetails must be an object")
        source_refs = source_details.get("resourceIds")
        if not isinstance(source_refs, list) or not source_refs or set(source_refs) - resource_ids:
            fail(f"{path}.sourceDetails.resourceIds must cite known resources")
        if source_mode == "web_downloaded":
            if not is_https(str(source_details.get("originalUrl", ""))):
                fail(f"{path}.sourceDetails.originalUrl must be HTTPS")
            if not SHA256_RE.fullmatch(str(source_details.get("downloadSha256", ""))):
                fail(f"{path}.sourceDetails.downloadSha256 must be lowercase SHA-256")
        else:
            require_text(source_details.get("generationMethod"), f"{path}.sourceDetails.generationMethod")
            if source_details.get("wholeImageGenerated") is not True:
                fail(f"{path}.sourceDetails.wholeImageGenerated must be true")
            if source_details.get("localLayoutApplied") is not False:
                fail(f"{path}.sourceDetails.localLayoutApplied must be false")
        if asset.get("factuality") not in {"factual", "non_factual"}:
            fail(f"{path}.factuality must be factual or non_factual")
        local = safe_local_path(Path(base_dir), asset.get("localPath"), f"{path}.localPath")
        if stage == "reviewed":
            verify_image(local, f"{path}.localPath")

        claims = asset.get("claims")
        if not isinstance(claims, list) or (asset["factuality"] == "factual" and not claims):
            fail(f"{path}.claims must contain sourced claims for factual images")
        for claim_index, claim in enumerate(claims):
            claim_path = f"{path}.claims[{claim_index}]"
            if not isinstance(claim, dict):
                fail(f"{claim_path} must be an object")
            claim_id = require_text(claim.get("claimId"), f"{claim_path}.claimId")
            if claim_id in claim_ids:
                fail(f"duplicate claimId: {claim_id}")
            claim_ids.add(claim_id)
            require_text(claim.get("text"), f"{claim_path}.text")
            refs = claim.get("resourceIds")
            if not isinstance(refs, list) or not refs or set(refs) - resource_ids:
                fail(f"{claim_path}.resourceIds must cite known resources")

        for field in ("expectedVisibleText", "expectedValues", "expectedRelations", "usedBy"):
            if not isinstance(asset.get(field), list):
                fail(f"{path}.{field} must be an array")
        if not isinstance(asset.get("containsNumbers"), bool):
            fail(f"{path}.containsNumbers must be boolean")
        if asset["containsNumbers"] and not asset["expectedValues"]:
            fail(f"{path}.expectedValues is required when numbers are present")
        for value_index, value in enumerate(asset["expectedValues"]):
            value_path = f"{path}.expectedValues[{value_index}]"
            if not isinstance(value, dict):
                fail(f"{value_path} must be an object")
            require_text(value.get("label"), f"{value_path}.label")
            require_text(value.get("displayValue"), f"{value_path}.displayValue")
            refs = value.get("resourceIds")
            if not isinstance(refs, list) or not refs or set(refs) - resource_ids:
                fail(f"{value_path}.resourceIds must cite known resources")
        for relation_index, relation in enumerate(asset["expectedRelations"]):
            relation_path = f"{path}.expectedRelations[{relation_index}]"
            if not isinstance(relation, dict):
                fail(f"{relation_path} must be an object")
            for field in ("subject", "relation", "object"):
                require_text(relation.get(field), f"{relation_path}.{field}")
        declared_uses = set()
        for use_index, use in enumerate(asset["usedBy"]):
            if not isinstance(use, dict) or not isinstance(use.get("levelIndex"), int) or not isinstance(use.get("blockIndex"), int):
                fail(f"{path}.usedBy[{use_index}] is invalid")
            declared_uses.add((use["levelIndex"], use["blockIndex"]))
        if declared_uses != actual_uses.get(asset_id, set()):
            fail(f"{path}.usedBy does not match image block references")

        if stage == "reviewed":
            review = asset.get("review")
            if not isinstance(review, dict):
                fail(f"{path}.review is required")
            failed = [flag for flag in REVIEW_FLAGS if review.get(flag) is not True]
            if failed:
                fail(f"{path}.review failed or omitted: {', '.join(failed)}")
            require_text(review.get("reviewedAt"), f"{path}.review.reviewedAt")
            require_text(review.get("notes"), f"{path}.review.notes")
            reviewed_sha = str(review.get("reviewedSha256", ""))
            if not SHA256_RE.fullmatch(reviewed_sha):
                fail(f"{path}.review.reviewedSha256 is invalid")
            if hashlib.sha256(local.read_bytes()).hexdigest() != reviewed_sha:
                fail(f"{path}.localPath changed after review")

    if set(actual_uses) - asset_ids:
        fail("request references undeclared image assets")
    if asset_ids - set(actual_uses):
        fail("manifest contains unused image assets")


def validate_final_request(request):
    validate_request_shape(request, stage="finalized")
    encoded = json.dumps(request, ensure_ascii=False)
    for forbidden in ("asset://", "file://", "data:image/", '"assetId"', '"resources"', '"assets"'):
        if forbidden in encoded:
            fail(f"final request contains forbidden authoring data: {forbidden}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--stage", choices=("draft", "reviewed", "finalized"), default="reviewed")
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        if args.stage == "finalized":
            validate_final_request(request)
        else:
            if not args.manifest:
                fail("--manifest is required for draft/reviewed validation")
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            validate_package(request, manifest, args.manifest.parent, stage=args.stage)
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"action package validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"valid": True, "stage": args.stage}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
