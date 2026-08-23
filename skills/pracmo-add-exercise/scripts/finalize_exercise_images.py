#!/usr/bin/env python3
"""Upload reviewed exercise images and replace asset:// placeholders with HTTPS URLs."""

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path, PurePosixPath

SCRIPT_DIR = Path(__file__).resolve().parent


def load_local_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_local_module("pracmo_exercise_validator", "validate_exercise_package.py")


def replace_assets(request, manifest, uploads):
    finalized = json.loads(json.dumps(request, ensure_ascii=False))
    known = {asset["assetId"] for asset in manifest.get("assets", [])}
    if set(uploads) != known:
        raise validator.ContractError("uploaded asset IDs must exactly match the manifest")
    for question in finalized.get("exercise", {}).get("questions", []):
        fields = [(question, "questionContent")]
        fields.extend((option, "content") for option in (question.get("options", []) or []) if isinstance(option, dict))
        for owner, field in fields:
            value = owner.get(field)
            if not isinstance(value, str):
                continue
            for asset_id, remote in uploads.items():
                url = remote.get("url", "")
                if not validator.is_https(url):
                    raise validator.ContractError(f"uploaded URL for {asset_id} must be HTTPS")
                value = value.replace(f"asset://{asset_id}", url)
            owner[field] = value
    validator.validate_final_request(finalized)
    return finalized


def upload_asset(local_path, request_id):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "pracmo_oss_upload.py"), "--request-id", request_id, str(local_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def verify_uploaded_bytes(url, expected_sha256):
    request = urllib.request.Request(url, headers={"Accept": "image/*"})
    with urllib.request.urlopen(request, timeout=30) as response:
        uploaded = response.read(512 * 1024 + 1)
    if len(uploaded) > 512 * 1024:
        raise validator.ContractError("uploaded image exceeds 512 KiB")
    actual = hashlib.sha256(uploaded).hexdigest()
    if actual != expected_sha256:
        raise validator.ContractError("uploaded image bytes differ from the reviewed local file")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--final-manifest", type=Path)
    args = parser.parse_args()
    if not os.environ.get("PRACMO_APIKEY", "").strip():
        print("PRACMO_APIKEY is required; set it locally and never paste it into chat", file=sys.stderr)
        return 2
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        validator.validate_package(request, manifest, args.manifest.parent, stage="reviewed")
        uploads = {}
        finalized_manifest = json.loads(json.dumps(manifest, ensure_ascii=False))
        finalized_by_id = {asset["assetId"]: asset for asset in finalized_manifest.get("assets", [])}
        for asset in manifest.get("assets", []):
            raw = PurePosixPath(asset["localPath"].replace("\\", "/"))
            local = args.manifest.parent.joinpath(*raw.parts)
            remote = upload_asset(local, request["clientRequestId"])
            remote["sha256"] = hashlib.sha256(local.read_bytes()).hexdigest()
            verify_uploaded_bytes(remote["url"], remote["sha256"])
            remote["downloadVerified"] = True
            uploads[asset["assetId"]] = remote
            finalized_by_id[asset["assetId"]]["upload"] = remote
        final_request = replace_assets(request, manifest, uploads)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(final_request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        final_manifest_path = args.final_manifest or args.output.with_name("exercise-images.finalized.json")
        final_manifest_path.write_text(
            json.dumps(finalized_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError, validator.ContractError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        print(f"exercise image finalization failed: {detail}", file=sys.stderr)
        return 2
    print(json.dumps({"request": str(args.output), "manifest": str(final_manifest_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
