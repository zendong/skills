#!/usr/bin/env python3
"""Upload local Public Action assets and write a finalized submission JSON."""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_UPLOADER = SCRIPT_DIR / "pracmo_oss_upload.py"


def load_validator():
    path = SCRIPT_DIR / "validate_public_action_json.py"
    spec = importlib.util.spec_from_file_location("pracmo_public_action_validator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def upload(uploader: Path, category: str, local_path: Path) -> dict:
    result = subprocess.run(
        [str(uploader), "--category", category, str(local_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"asset uploader exited {result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("asset uploader returned invalid JSON") from exc


def finalize(payload: dict, source_path: Path, uploader: Path) -> dict:
    validator = load_validator()
    validator.validate(payload, base_dir=source_path.parent, check_assets=True)
    finalized = json.loads(json.dumps(payload, ensure_ascii=False))
    uploaded_by_id: dict[str, dict] = {}
    for asset in finalized["assets"]:
        if "localPath" not in asset:
            uploaded_by_id[asset["assetId"]] = asset
            continue
        relative = asset.pop("localPath")
        local_path = source_path.parent / relative
        category = "public-action-cover" if asset["role"] == "cover" else "public-action-content"
        uploaded = upload(uploader, category, local_path)
        asset.update(uploaded)
        asset["sha256"] = hashlib.sha256(local_path.read_bytes()).hexdigest()
        uploaded_by_id[asset["assetId"]] = asset

    cover = next(asset for asset in finalized["assets"] if asset["role"] == "cover")
    finalized["catalog"]["coverImage"] = {
        "objectKey": cover["objectKey"],
        "url": cover["url"],
        "alt": finalized["catalog"]["coverImage"]["alt"],
    }
    follow_plan = finalized["template"].get("followPlan") or {}
    for level in follow_plan.get("levels", []):
        for block in level["contentBlocks"]:
            if block.get("blockType") == "image":
                asset = uploaded_by_id.get(block.get("assetId", ""))
                if asset is None:
                    raise RuntimeError(f"image block assetId {block.get('assetId')} was not uploaded")
                block["mediaUrl"] = asset["url"]
    validator.validate(finalized, base_dir=source_path.parent, finalized=True)
    return finalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--uploader", type=Path, default=DEFAULT_UPLOADER)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        finalized = finalize(payload, args.input, args.uploader)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(finalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"asset finalization failed: {exc}", file=sys.stderr)
        return 2
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
