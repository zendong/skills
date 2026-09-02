#!/usr/bin/env python3
"""Validate a grounded exercise authoring package and its finalized API request."""

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

try:
    from PIL import Image
except ImportError:
    Image = None

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$")
ASSET_TOKEN_RE = re.compile(r"asset://([A-Za-z0-9][A-Za-z0-9._-]{0,63})")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)")
MAX_IMAGE_BYTES = 512 * 1024
REVIEW_FLAGS = (
    "sourceVerified",
    "pixelInspected",
    "textVerified",
    "logicVerified",
    "numbersVerified",
    "questionAnswerVerified",
    "mobileReadabilityVerified",
    "answerLeakageChecked",
    "authenticityVerified",
    "scenePlausibilityVerified",
    "deviceNeutralityVerified",
    "privacyVerified",
)
SOURCE_TYPES = {"primary", "official", "standard", "peer_reviewed", "reputable_secondary"}
SOURCE_MODES = {"web_downloaded", "real_scene_generated"}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class ContractError(ValueError):
    pass


def fail(message):
    raise ContractError(message)


def require_nonempty(value, path):
    if not isinstance(value, str) or not value.strip():
        fail(f"{path} must be a non-empty string")


def is_https(value):
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def safe_local_path(base_dir, value, path):
    require_nonempty(value, path)
    normalized = PurePosixPath(value.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        fail(f"{path} must stay inside the package directory")
    local = base_dir.joinpath(*normalized.parts)
    try:
        local.resolve().relative_to(base_dir.resolve())
    except ValueError:
        fail(f"{path} must stay inside the package directory")
    return local


def verify_image_file(local, path):
    if Image is None:
        fail("Pillow is required for reviewed image validation: python3 -m pip install Pillow")
    try:
        with Image.open(local) as opened:
            opened.verify()
            if opened.format not in {"PNG", "JPEG", "WEBP"}:
                fail(f"{path} must be PNG, JPEG, or WebP")
    except (OSError, SyntaxError) as exc:
        fail(f"{path} is not a valid image: {exc}")


def iter_image_fields(request):
    questions = request.get("exercise", {}).get("questions", [])
    for index, question in enumerate(questions):
        if isinstance(question, dict):
            yield index, "questionContent", question.get("questionContent", "")
            for option_index, option in enumerate(question.get("options", []) or []):
                if isinstance(option, dict):
                    yield index, f"options[{option_index}].content", option.get("content", "")


def validate_request_shape(request, require_collection=False):
    if not isinstance(request, dict):
        fail("request must be an object")
    allowed = {"schemaVersion", "clientRequestId", "exercise"}
    if set(request) != allowed:
        fail(f"request top-level keys must be exactly {sorted(allowed)}")
    if request.get("schemaVersion") != "pracmo-track-exercise@v1":
        fail("unsupported request schemaVersion")
    request_id = request.get("clientRequestId", "")
    if not isinstance(request_id, str) or not REQUEST_ID_RE.fullmatch(request_id):
        fail("clientRequestId format is invalid")
    exercise = request.get("exercise")
    if not isinstance(exercise, dict):
        fail("exercise must be an object")
    require_nonempty(exercise.get("title"), "exercise.title")
    collection_id = exercise.get("collectionId")
    if collection_id is None:
        if require_collection:
            fail("exercise.collectionId is required for finalized requests")
    else:
        require_nonempty(collection_id, "exercise.collectionId")
        if collection_id != collection_id.strip() or len(collection_id) > 64:
            fail("exercise.collectionId must be 1 to 64 characters without surrounding whitespace")
    questions = exercise.get("questions")
    if not isinstance(questions, list) or not 10 <= len(questions) <= 100:
        fail("exercise.questions must contain 10 to 100 questions")
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            fail(f"exercise.questions[{index}] must be an object")
        for field in ("questionType", "questionContent", "testableClaim"):
            require_nonempty(question.get(field), f"exercise.questions[{index}].{field}")
        if "explanation" in question:
            fail(f"exercise.questions[{index}].explanation is not allowed; use options[].explanation")
        question_type = question.get("questionType")
        if question_type not in {"single_choice", "multiple_choice", "true_false", "short_answer"}:
            fail(f"exercise.questions[{index}].questionType is unsupported")
        concept = question.get("concept")
        if not isinstance(concept, dict) or not any(
            isinstance(concept.get(field), str) and concept[field].strip()
            for field in ("name", "conceptId")
        ):
            fail(f"exercise.questions[{index}].concept requires name or conceptId")
        if question.get("bloomLevel") not in {1, 2, 3, 4}:
            fail(f"exercise.questions[{index}].bloomLevel must be 1 to 4")
        options = question.get("options", [])
        if not isinstance(options, list):
            fail(f"exercise.questions[{index}].options must be an array")
        if question_type == "short_answer":
            if len(options) != 1:
                fail(f"exercise.questions[{index}] short_answer requires exactly one reference answer option")
        elif len(options) < 2:
            fail(f"exercise.questions[{index}].options must contain at least two options")
        correct_count = 0
        for option_index, option in enumerate(options):
            if not isinstance(option, dict):
                fail(f"exercise.questions[{index}].options[{option_index}] must be an object")
            require_nonempty(option.get("content"), f"exercise.questions[{index}].options[{option_index}].content")
            require_nonempty(option.get("explanation"), f"exercise.questions[{index}].options[{option_index}].explanation")
            if option.get("isCorrect") is True:
                correct_count += 1
            elif option.get("isCorrect") is not False:
                fail(f"exercise.questions[{index}].options[{option_index}].isCorrect must be boolean")
        if question_type != "short_answer":
            explanations = [option["explanation"].strip() for option in options]
            if len(set(explanations)) != len(explanations):
                fail(f"exercise.questions[{index}] option explanations must be distinct and option-specific")
        if question_type == "short_answer":
            if correct_count != 1:
                fail(f"exercise.questions[{index}] short_answer reference answer option must be correct")
        else:
            expected = "exactly one" if question_type in {"single_choice", "true_false"} else "at least two"
            if (question_type in {"single_choice", "true_false"} and correct_count != 1) or (
                question_type == "multiple_choice" and correct_count < 2
            ):
                fail(f"exercise.questions[{index}] requires {expected} correct option")


def collect_asset_uses(request):
    uses = {}
    for question_index, field, content in iter_image_fields(request):
        if not isinstance(content, str):
            continue
        for asset_id in ASSET_TOKEN_RE.findall(content):
            uses.setdefault(asset_id, set()).add((question_index, field))
    return uses


def validate_package(request, manifest, base_dir, stage="reviewed"):
    validate_request_shape(request)
    if stage not in {"draft", "reviewed"}:
        fail("stage must be draft or reviewed")
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != "pracmo-exercise-images@v1":
        fail("image manifest schemaVersion must be pracmo-exercise-images@v1")
    if manifest.get("clientRequestId") != request["clientRequestId"]:
        fail("manifest clientRequestId must match request")

    resources = manifest.get("resources", [])
    assets = manifest.get("assets", [])
    if not isinstance(resources, list) or not isinstance(assets, list):
        fail("manifest resources and assets must be arrays")
    resource_ids = set()
    for index, resource in enumerate(resources):
        if not isinstance(resource, dict):
            fail(f"resources[{index}] must be an object")
        resource_id = resource.get("resourceId")
        require_nonempty(resource_id, f"resources[{index}].resourceId")
        if resource_id in resource_ids:
            fail(f"duplicate resourceId: {resource_id}")
        resource_ids.add(resource_id)
        for field in ("title", "publisher", "retrievedAt"):
            require_nonempty(resource.get(field), f"resources[{index}].{field}")
        if resource.get("sourceType") not in SOURCE_TYPES:
            fail(f"resources[{index}].sourceType is not trusted")
        if not is_https(str(resource.get("url", ""))):
            fail(f"resources[{index}].url must be HTTPS")

    actual_uses = collect_asset_uses(request)
    asset_ids = set()
    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if not isinstance(asset, dict):
            fail(f"{prefix} must be an object")
        asset_id = asset.get("assetId")
        require_nonempty(asset_id, f"{prefix}.assetId")
        if not ASSET_TOKEN_RE.fullmatch(f"asset://{asset_id}"):
            fail(f"{prefix}.assetId format is invalid")
        if asset_id in asset_ids:
            fail(f"duplicate assetId: {asset_id}")
        asset_ids.add(asset_id)
        require_nonempty(asset.get("altText"), f"{prefix}.altText")
        require_nonempty(asset.get("provenance"), f"{prefix}.provenance")
        require_nonempty(asset.get("license"), f"{prefix}.license")
        source_mode = asset.get("sourceMode")
        if source_mode not in SOURCE_MODES:
            fail(f"{prefix}.sourceMode must be web_downloaded or real_scene_generated")
        source_details = asset.get("sourceDetails")
        if not isinstance(source_details, dict):
            fail(f"{prefix}.sourceDetails must be an object")
        source_refs = source_details.get("resourceIds")
        if not isinstance(source_refs, list) or not source_refs:
            fail(f"{prefix}.sourceDetails.resourceIds must cite at least one resource")
        unknown_source_refs = set(source_refs) - resource_ids
        if unknown_source_refs:
            fail(f"{prefix}.sourceDetails cites unknown resources: {sorted(unknown_source_refs)}")
        if source_mode == "web_downloaded":
            if not is_https(str(source_details.get("originalUrl", ""))):
                fail(f"{prefix}.sourceDetails.originalUrl must be HTTPS")
            if not SHA256_RE.fullmatch(str(source_details.get("downloadSha256", ""))):
                fail(f"{prefix}.sourceDetails.downloadSha256 must be lowercase SHA-256")
        else:
            require_nonempty(source_details.get("generationMethod"), f"{prefix}.sourceDetails.generationMethod")
            if source_details.get("wholeImageGenerated") is not True:
                fail(f"{prefix}.sourceDetails.wholeImageGenerated must be true")
            if source_details.get("localLayoutApplied") is not False:
                fail(f"{prefix}.sourceDetails.localLayoutApplied must be false")
        if asset.get("factuality") not in {"factual", "non_factual"}:
            fail(f"{prefix}.factuality must be factual or non_factual")
        local = safe_local_path(Path(base_dir), asset.get("localPath"), f"{prefix}.localPath")
        if stage == "reviewed":
            if not local.is_file() or local.stat().st_size <= 0:
                fail(f"{prefix}.localPath does not exist or is empty")
            if local.stat().st_size > MAX_IMAGE_BYTES:
                fail(f"{prefix}.localPath exceeds 512 KiB; compress before review")
            verify_image_file(local, f"{prefix}.localPath")

        claims = asset.get("claims", [])
        if not isinstance(claims, list):
            fail(f"{prefix}.claims must be an array")
        if asset.get("factuality") == "factual" and not claims:
            fail(f"{prefix} is factual and must declare sourced claims")
        for claim_index, claim in enumerate(claims):
            claim_path = f"{prefix}.claims[{claim_index}]"
            if not isinstance(claim, dict):
                fail(f"{claim_path} must be an object")
            require_nonempty(claim.get("claimId"), f"{claim_path}.claimId")
            require_nonempty(claim.get("text"), f"{claim_path}.text")
            refs = claim.get("resourceIds")
            if not isinstance(refs, list) or not refs:
                fail(f"{claim_path}.resourceIds must cite at least one resource")
            unknown = set(refs) - resource_ids
            if unknown:
                fail(f"{claim_path} cites unknown resources: {sorted(unknown)}")

        for field in ("expectedVisibleText", "expectedRelations", "expectedValues", "usedBy"):
            if not isinstance(asset.get(field), list):
                fail(f"{prefix}.{field} must be an array")
        if not isinstance(asset.get("containsNumbers"), bool):
            fail(f"{prefix}.containsNumbers must be boolean")
        if asset["containsNumbers"] and not asset["expectedValues"]:
            fail(f"{prefix}.expectedValues is required when the image contains numbers")
        for value_index, expected_value in enumerate(asset["expectedValues"]):
            value_path = f"{prefix}.expectedValues[{value_index}]"
            if not isinstance(expected_value, dict):
                fail(f"{value_path} must be an object")
            require_nonempty(expected_value.get("label"), f"{value_path}.label")
            require_nonempty(expected_value.get("displayValue"), f"{value_path}.displayValue")
            refs = expected_value.get("resourceIds")
            if not isinstance(refs, list) or not refs:
                fail(f"{value_path}.resourceIds must cite at least one resource")
            unknown = set(refs) - resource_ids
            if unknown:
                fail(f"{value_path} cites unknown resources: {sorted(unknown)}")
        declared_uses = set()
        for use_index, use in enumerate(asset["usedBy"]):
            if not isinstance(use, dict) or not isinstance(use.get("questionIndex"), int):
                fail(f"{prefix}.usedBy[{use_index}] is invalid")
            require_nonempty(use.get("field"), f"{prefix}.usedBy[{use_index}].field")
            declared_uses.add((use["questionIndex"], use["field"]))
        if declared_uses != actual_uses.get(asset_id, set()):
            fail(f"{prefix}.usedBy does not match asset:// references")

        if stage == "reviewed":
            review = asset.get("review")
            if not isinstance(review, dict):
                fail(f"{prefix}.review is required")
            failed = [flag for flag in REVIEW_FLAGS if review.get(flag) is not True]
            if failed:
                fail(f"{prefix}.review failed or omitted: {', '.join(failed)}")
            require_nonempty(review.get("reviewedAt"), f"{prefix}.review.reviewedAt")
            require_nonempty(review.get("notes"), f"{prefix}.review.notes")

    undeclared = set(actual_uses) - asset_ids
    if undeclared:
        fail(f"request references undeclared assets: {sorted(undeclared)}")
    unused = asset_ids - set(actual_uses)
    if unused:
        fail(f"manifest contains unused assets: {sorted(unused)}")


def validate_final_request(request):
    validate_request_shape(request, require_collection=True)
    encoded = json.dumps(request, ensure_ascii=False)
    if "asset://" in encoded or "file://" in encoded or "data:image/" in encoded:
        fail("final request contains a local or embedded image reference")
    for question_index, field, content in iter_image_fields(request):
        if not isinstance(content, str):
            continue
        for url in MARKDOWN_IMAGE_RE.findall(content):
            if not is_https(url):
                fail(f"question {question_index} {field} image URL must be HTTPS")


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
                fail("--manifest is required for draft and reviewed stages")
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            validate_package(request, manifest, args.manifest.parent, stage=args.stage)
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"exercise package validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"valid": True, "stage": args.stage}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
