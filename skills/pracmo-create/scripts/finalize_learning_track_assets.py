#!/usr/bin/env python3
"""Upload local images and write a separate finalized package JSON."""

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

try:
    from PIL import Image
except ImportError:
    Image = None

SCRIPT_DIR = Path(__file__).resolve().parent
UPLOADER = SCRIPT_DIR / "pracmo_oss_upload.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validator", SCRIPT_DIR / "validate_learning_track_json.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upload(local, request_id, content_type):
    command = [sys.executable, str(UPLOADER), "--request-id", request_id, str(local)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def image_size(path):
    if Image is None:
        return 0, 0
    with Image.open(path) as opened:
        return opened.size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("PRACMO_APIKEY", "").strip():
        print("PRACMO_APIKEY is required; set it locally and do not paste it into chat", file=sys.stderr)
        return 2
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        validator = load_validator()
        validator.validate(payload, base_dir=args.input.parent, mode="authoring", check_assets=True)
        finalized = json.loads(json.dumps(payload, ensure_ascii=False))
        for asset in finalized.get("assets", []):
            relative = PurePosixPath(asset.pop("localPath").replace("\\", "/"))
            local = args.input.parent.joinpath(*relative.parts)
            suffix = local.suffix.lower()
            content_type = "image/png" if suffix == ".png" else "image/webp" if suffix == ".webp" else "image/jpeg"
            remote = upload(local, payload["clientRequestId"], content_type)
            width, height = image_size(local)
            asset.update(remote)
            asset["sha256"] = hashlib.sha256(local.read_bytes()).hexdigest()
            if width and height:
                asset["width"], asset["height"] = width, height
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(finalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validator.validate(finalized, base_dir=args.output.parent, mode="finalized")
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"asset finalization failed: {exc}", file=sys.stderr)
        return 2
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
