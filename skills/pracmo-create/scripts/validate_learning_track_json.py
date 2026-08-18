#!/usr/bin/env python3
"""Validate pracmo-learning-track@v1 authoring or finalized JSON."""

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

MAX_IMAGE_BYTES = 512 * 1024
QUESTION_TYPES = {"single_choice", "multiple_choice", "true_false", "short_answer"}
CONTENT_MODES = {"self_directed", "puki_generated", "follow_along"}
RELATIONS = {"advance", "assess", "reinforce"}


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def text(value, path, maximum=4000):
    require(isinstance(value, str) and value.strip(), f"{path} is required")
    require(len(value.strip()) <= maximum, f"{path} exceeds {maximum} characters")
    return value.strip()


def safe_local_path(raw, path, base_dir, check_assets):
    value = text(raw, path, 240)
    posix = PurePosixPath(value.replace("\\", "/"))
    require(not posix.is_absolute() and ".." not in posix.parts, f"{path} must be a safe relative path")
    require(not value.startswith(("file:", "data:")), f"{path} must be a safe relative path")
    if check_assets:
        local = base_dir.joinpath(*posix.parts)
        require(local.is_file(), f"{path} does not exist")
        require(0 < local.stat().st_size <= MAX_IMAGE_BYTES, f"{path} must be 512 KiB or smaller")


def validate_state_link(link, path, states):
    if link is None:
        return
    require(isinstance(link, dict), f"{path} must be an object")
    state_key = text(link.get("stateKey"), f"{path}.stateKey", 64)
    require(state_key in states, f"{path}.stateKey does not exist")
    require(link.get("relationRole") in RELATIONS, f"{path}.relationRole is invalid")
    criterion_ids = link.get("criterionIds")
    require(isinstance(criterion_ids, list) and criterion_ids, f"{path}.criterionIds is required")
    for criterion_id in criterion_ids:
        require(criterion_id in states[state_key], f"{path}.criterionId {criterion_id!r} does not exist")


def validate_action(item, path, states):
    require(isinstance(item, dict), f"{path} must be an object")
    text(item.get("actionKey"), f"{path}.actionKey", 64)
    text(item.get("title"), f"{path}.title", 255)
    require(item.get("scheduleType") in {"daily", "weekdays", "weekly_quota", "once"}, f"{path}.scheduleType is invalid")
    text(item.get("timezone"), f"{path}.timezone", 64)
    start_date = str(item.get("startDate", ""))
    require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_date)), f"{path}.startDate must use YYYY-MM-DD")
    try:
        dt.date.fromisoformat(start_date)
        if item.get("endDate"):
            require(dt.date.fromisoformat(str(item["endDate"])) >= dt.date.fromisoformat(start_date), f"{path}.endDate must not be before startDate")
    except ValueError as exc:
        raise ContractError(f"{path} contains an invalid ISO date") from exc
    require(bool(re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(item.get("deadlineLocalTime", "")))), f"{path}.deadlineLocalTime must use HH:mm")
    require(item.get("gracePolicy") in {"none", "two_hours", "next_day_noon"}, f"{path}.gracePolicy is invalid")
    completion = item.get("completionMode")
    require(completion in {"one_tap", "text", "rich_media"}, f"{path}.completionMode is invalid")
    mode = item.get("contentMode")
    require(mode in CONTENT_MODES, f"{path}.contentMode is invalid")
    schedule_raw = item.get("scheduleConfigJson", "")
    require(isinstance(schedule_raw, str), f"{path}.scheduleConfigJson must be a JSON string")
    if schedule_raw.strip():
        try:
            schedule_config = json.loads(schedule_raw)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{path}.scheduleConfigJson is invalid JSON") from exc
        require(isinstance(schedule_config, dict), f"{path}.scheduleConfigJson must encode an object")
    else:
        schedule_config = {}
    if item["scheduleType"] == "weekdays":
        weekdays = schedule_config.get("weekdays")
        require(isinstance(weekdays, list) and weekdays, f"{path}.scheduleConfigJson.weekdays is required")
        require(all(isinstance(day, int) and 1 <= day <= 7 for day in weekdays) and len(set(weekdays)) == len(weekdays), f"{path}.scheduleConfigJson.weekdays is invalid")
    elif item["scheduleType"] == "weekly_quota":
        target = schedule_config.get("targetCount")
        require(isinstance(target, int) and 1 <= target <= 7, f"{path}.scheduleConfigJson.targetCount must be 1-7")
    reminder_raw = item.get("reminderConfigJson", "")
    require(isinstance(reminder_raw, str), f"{path}.reminderConfigJson must be a JSON string")
    if reminder_raw.strip():
        try:
            reminder = json.loads(reminder_raw)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{path}.reminderConfigJson is invalid JSON") from exc
        require(isinstance(reminder, dict), f"{path}.reminderConfigJson must encode an object")
        times = reminder.get("times", [])
        offset = reminder.get("defaultBeforeDeadlineMinutes", 0)
        require(isinstance(times, list) and len(times) <= 5, f"{path}.reminderConfigJson.times must contain at most 5 items")
        require(all(isinstance(value, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value) for value in times), f"{path}.reminderConfigJson contains an invalid time")
        require(len(set(times)) == len(times), f"{path}.reminderConfigJson contains duplicate times")
        require(isinstance(offset, int) and 0 <= offset <= 1440, f"{path}.reminderConfigJson default offset is invalid")
        require(bool(times) or offset > 0, f"{path}.reminderConfigJson cannot be an empty reminder")
    generated, plan = item.get("generatedContentConfig"), item.get("followPlan")
    if mode == "self_directed":
        require(generated is None and plan is None, f"{path} self_directed cannot contain generated config or follow plan")
    elif mode == "puki_generated":
        require(completion == "one_tap" and isinstance(generated, dict) and plan is None, f"{path} puki_generated configuration is invalid")
        require(generated.get("type") in {"reading", "quick_qa"}, f"{path}.generatedContentConfig.type is invalid")
        text(generated.get("instruction"), f"{path}.generatedContentConfig.instruction", 1000)
    else:
        require(completion == "one_tap" and generated is None and isinstance(plan, dict), f"{path} follow_along configuration is invalid")
        levels = plan.get("levels")
        require(isinstance(levels, list) and 1 <= len(levels) <= 20, f"{path}.followPlan.levels must contain 1-20 items")
    validate_state_link(item.get("stateLink"), f"{path}.stateLink", states)


def canonical_payload(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate(payload, *, base_dir, mode="auto", check_assets=False):
    require(isinstance(payload, dict), "root must be an object")
    require(payload.get("schemaVersion") == "pracmo-learning-track@v1", "schemaVersion must be pracmo-learning-track@v1")
    request_id = text(payload.get("clientRequestId"), "clientRequestId", 128)
    require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}", request_id)), "clientRequestId has invalid characters or length")
    track = payload.get("track")
    require(isinstance(track, dict), "track must be an object")
    text(track.get("title"), "track.title", 255)
    text(track.get("goalStatement"), "track.goalStatement")
    path = payload.get("path")
    require(isinstance(path, dict), "path must be an object")
    state_items = path.get("states")
    require(isinstance(state_items, list) and 2 <= len(state_items) <= 8, "path.states must contain 2-8 items")
    states = {}
    for index, state in enumerate(state_items):
        state_path = f"path.states[{index}]"
        require(isinstance(state, dict), f"{state_path} must be an object")
        key = text(state.get("stateKey"), f"{state_path}.stateKey", 64)
        require(key not in states, f"{state_path}.stateKey is duplicated")
        text(state.get("title"), f"{state_path}.title", 255)
        text(state.get("description"), f"{state_path}.description")
        criteria = state.get("criteria")
        require(isinstance(criteria, list) and 1 <= len(criteria) <= 5, f"{state_path}.criteria must contain 1-5 items")
        states[key] = set()
        for criterion_index, criterion in enumerate(criteria):
            criterion_path = f"{state_path}.criteria[{criterion_index}]"
            require(isinstance(criterion, dict), f"{criterion_path} must be an object")
            criterion_id = text(criterion.get("criterionId"), f"{criterion_path}.criterionId", 64)
            require(criterion_id not in states[key], f"{criterion_path}.criterionId is duplicated")
            states[key].add(criterion_id)
            text(criterion.get("description"), f"{criterion_path}.description", 1000)
    require(path.get("currentStateKey") == state_items[0]["stateKey"], "currentStateKey must reference the first state")
    require(path.get("targetStateKey") == state_items[-1]["stateKey"], "targetStateKey must reference the final state")

    concepts = payload.get("concepts", [])
    require(isinstance(concepts, list), "concepts must be an array")
    concept_keys = set()
    for index, concept in enumerate(concepts):
        require(isinstance(concept, dict), f"concepts[{index}] must be an object")
        key = text(concept.get("conceptKey"), f"concepts[{index}].conceptKey", 64)
        require(key not in concept_keys, f"concepts[{index}].conceptKey is duplicated")
        concept_keys.add(key)
        text(concept.get("name"), f"concepts[{index}].name", 255)

    exercises = payload.get("exercises")
    require(isinstance(exercises, list) and len(exercises) <= 10, "exercises must contain at most 10 items")
    exercise_keys, total_questions = set(), 0
    for index, exercise in enumerate(exercises):
        exercise_path = f"exercises[{index}]"
        require(isinstance(exercise, dict), f"{exercise_path} must be an object")
        key = text(exercise.get("exerciseKey"), f"{exercise_path}.exerciseKey", 64)
        require(key not in exercise_keys, f"{exercise_path}.exerciseKey is duplicated")
        exercise_keys.add(key)
        text(exercise.get("title"), f"{exercise_path}.title", 255)
        questions = exercise.get("questions")
        require(isinstance(questions, list) and 1 <= len(questions) <= 100, f"{exercise_path}.questions must contain 1-100 items")
        total_questions += len(questions)
        for question_index, question in enumerate(questions):
            question_path = f"{exercise_path}.questions[{question_index}]"
            require(isinstance(question, dict), f"{question_path} must be an object")
            require(question.get("questionType") in QUESTION_TYPES, f"{question_path}.questionType is invalid")
            text(question.get("questionContent"), f"{question_path}.questionContent", 10000)
            text(question.get("testableClaim"), f"{question_path}.testableClaim", 1000)
            require(question.get("conceptKey") in concept_keys, f"{question_path}.conceptKey does not exist")
            if question["questionType"] != "short_answer":
                options = question.get("options")
                require(isinstance(options, list) and len(options) >= 2, f"{question_path}.options must contain at least 2 items")
                correct = sum(1 for option in options if isinstance(option, dict) and option.get("isCorrect") is True)
                require(correct >= 1, f"{question_path} needs a correct option")
                if question["questionType"] in {"single_choice", "true_false"}:
                    require(correct == 1, f"{question_path} requires exactly one correct option")
        validate_state_link(exercise.get("stateLink"), f"{exercise_path}.stateLink", states)
    require(total_questions <= 300, "total question count exceeds 300")

    actions = payload.get("actions")
    require(isinstance(actions, list) and len(actions) <= 10, "actions must contain at most 10 items")
    action_keys = set()
    for index, item in enumerate(actions):
        validate_action(item, f"actions[{index}]", states)
        require(item["actionKey"] not in action_keys, f"actions[{index}].actionKey is duplicated")
        action_keys.add(item["actionKey"])

    assets = payload.get("assets", [])
    require(isinstance(assets, list) and len(assets) <= 50, "assets must contain at most 50 items")
    detected = set()
    assets_by_id = {}
    finalized_count = 0
    for index, asset in enumerate(assets):
        asset_path = f"assets[{index}]"
        require(isinstance(asset, dict), f"{asset_path} must be an object")
        asset_id = text(asset.get("assetId"), f"{asset_path}.assetId", 64)
        require(asset_id not in detected, f"{asset_path}.assetId is duplicated")
        detected.add(asset_id)
        assets_by_id[asset_id] = asset
        has_local = "localPath" in asset
        has_remote = all(asset.get(field) not in (None, "") for field in ("objectKey", "url", "sha256", "contentType", "sizeBytes"))
        require(has_local != has_remote, f"{asset_path} must use exactly one of authoring or finalized form")
        if has_local:
            safe_local_path(asset["localPath"], f"{asset_path}.localPath", base_dir, check_assets)
        else:
            finalized_count += 1
            object_key = text(asset.get("objectKey"), f"{asset_path}.objectKey", 512)
            require("://" not in object_key and ".." not in PurePosixPath(object_key).parts, f"{asset_path}.objectKey is invalid")
            expected_segment = f"/learning-track-assets/{request_id}/"
            require(expected_segment in "/" + object_key, f"{asset_path}.objectKey is outside this learning track package")
            require(str(asset["url"]).startswith("https://"), f"{asset_path}.url must be HTTPS")
            require(0 < int(asset["sizeBytes"]) <= MAX_IMAGE_BYTES, f"{asset_path}.sizeBytes must be <= 512 KiB")
            require(asset["contentType"] in {"image/png", "image/jpeg", "image/webp"}, f"{asset_path}.contentType is invalid")
            require(bool(re.fullmatch(r"[0-9a-fA-F]{64}", str(asset.get("sha256", "")))), f"{asset_path}.sha256 is invalid")
    if mode == "authoring":
        require(finalized_count == 0, "authoring payload cannot contain finalized assets")
    if mode == "finalized":
        require(finalized_count == len(assets), "finalized payload cannot contain localPath")
    cover = track.get("coverImage")
    if cover is not None:
        require(isinstance(cover, dict) and set(cover) == {"assetId"}, "track.coverImage must contain only assetId")
        require(cover["assetId"] in detected, "track.coverImage.assetId does not exist")
        require(assets_by_id[cover["assetId"]].get("role") == "cover", "track.coverImage must reference a cover asset")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--authoring", action="store_true")
    group.add_argument("--finalized", action="store_true")
    parser.add_argument("--check-assets", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    mode = "authoring" if args.authoring else "finalized" if args.finalized else "auto"
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        validate(payload, base_dir=args.input.parent, mode=mode, check_assets=args.check_assets)
    except (OSError, json.JSONDecodeError, ContractError, ValueError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 2
    digest = hashlib.sha256(canonical_payload(payload)).hexdigest()
    result = {"valid": True, "payloadHash": digest, "schemaVersion": payload["schemaVersion"]}
    print(json.dumps(result, ensure_ascii=False) if args.json else f"valid {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
