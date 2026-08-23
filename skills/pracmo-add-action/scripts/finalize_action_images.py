#!/usr/bin/env python3
"""Upload reviewed action images and replace asset:// mediaUrl placeholders."""

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


validator = load_local_module("pracmo_action_validator", "validate_action_package.py")


def replace_assets(request, manifest, uploads):
    finalized = json.loads(json.dumps(request, ensure_ascii=False))
    known = {asset["assetId"] for asset in manifest.get("assets", [])}
    if set(uploads) != known:
        raise validator.ContractError("uploaded asset IDs must exactly match the manifest")
    plan = finalized.get("action", {}).get("followPlan") or {}
    for level in plan.get("levels", []):
        for block in level.get("contentBlocks", []):
            if not isinstance(block, dict) or str(block.get("blockType", "")).strip() != "image":
                continue
            match = validator.ASSET_URL_RE.fullmatch(str(block.get("mediaUrl", "")).strip())
            if not match:
                raise validator.ContractError("authoring image block must contain an asset:// placeholder")
            remote = uploads.get(match.group(1), {})
            url = remote.get("url", "")
            if not validator.is_https(url):
                raise validator.ContractError(f"uploaded URL for {match.group(1)} must be HTTPS")
            block["mediaUrl"] = url
    validator.validate_final_request(finalized)
    return finalized


def upload_asset(local, request_id, asset_id, reviewed_sha):
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "pracmo_oss_upload.py"),
            "--request-id", request_id,
            "--asset-id", asset_id,
            "--reviewed-sha256", reviewed_sha,
            str(local),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def verify_uploaded_bytes(url, expected_sha):
    request = urllib.request.Request(url, headers={"Accept": "image/*"})
    with urllib.request.urlopen(request, timeout=30) as response:
        uploaded = response.read(512 * 1024 + 1)
    if len(uploaded) > 512 * 1024 or hashlib.sha256(uploaded).hexdigest() != expected_sha:
        raise validator.ContractError("uploaded image differs from the reviewed local file")


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
        ledger_assets = {asset["assetId"]: asset for asset in finalized_manifest.get("assets", [])}
        for asset in manifest.get("assets", []):
            raw = PurePosixPath(asset["localPath"].replace("\\", "/"))
            local = args.manifest.parent.joinpath(*raw.parts)
            reviewed_sha = asset["review"]["reviewedSha256"]
            remote = upload_asset(local, request["clientRequestId"], asset["assetId"], reviewed_sha)
            verify_uploaded_bytes(remote["url"], reviewed_sha)
            remote["downloadVerified"] = True
            uploads[asset["assetId"]] = remote
            ledger_assets[asset["assetId"]]["upload"] = remote
        final_request = replace_assets(request, manifest, uploads)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(final_request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ledger_path = args.final_manifest or args.output.with_name("action-images.finalized.json")
        ledger_path.write_text(json.dumps(finalized_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, validator.ContractError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        print(f"action image finalization failed: {detail}", file=sys.stderr)
        return 2
    print(json.dumps({"request": str(args.output), "manifest": str(ledger_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
