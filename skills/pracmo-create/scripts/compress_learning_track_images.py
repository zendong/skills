#!/usr/bin/env python3
"""Copy/convert all local package images into assets/, each <= 512 KiB."""

import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = ImageOps = None

SCRIPT_DIR = Path(__file__).resolve().parent
MAX_BYTES = 512 * 1024
PASSTHROUGH = {".png", ".jpg", ".jpeg", ".webp"}


def load_validator():
    spec = importlib.util.spec_from_file_location("validator", SCRIPT_DIR / "validate_learning_track_json.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-") or "image"


def flatten(image):
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def compress_one(source, destination_dir, asset_id):
    if not source.is_file() or source.stat().st_size <= 0:
        raise ValueError(f"invalid image: {source}")
    suffix = source.suffix.lower()
    if source.stat().st_size <= MAX_BYTES and suffix in PASSTHROUGH:
        destination = destination_dir / f"{safe_name(asset_id)}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        return destination
    if Image is None:
        raise RuntimeError("Pillow is required: python3 -m pip install Pillow")
    with Image.open(source) as opened:
        image = flatten(opened)
    destination = destination_dir / f"{safe_name(asset_id)}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    while min(image.size) >= 320:
        for quality in (88, 82, 76, 70, 64, 58, 52, 46, 40):
            image.save(destination, "JPEG", quality=quality, optimize=True, progressive=True)
            if destination.stat().st_size <= MAX_BYTES:
                return destination
        image = image.resize((max(1, int(image.width * .85)), max(1, int(image.height * .85))), Image.Resampling.LANCZOS)
    raise RuntimeError(f"cannot compress {source} under 512 KiB")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        validator = load_validator()
        validator.validate(payload, base_dir=args.input.parent, mode="authoring")
        rewritten = json.loads(json.dumps(payload, ensure_ascii=False))
        destination_dir = args.output.parent / "assets"
        for asset in rewritten.get("assets", []):
            raw = PurePosixPath(asset["localPath"].replace("\\", "/"))
            source = args.input.parent.joinpath(*raw.parts)
            destination = compress_one(source, destination_dir, asset["assetId"])
            asset["localPath"] = destination.relative_to(args.output.parent).as_posix()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rewritten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validator.validate(rewritten, base_dir=args.output.parent, mode="authoring", check_assets=True)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"image compression failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(args.output), "imageCount": len(rewritten.get("assets", []))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
