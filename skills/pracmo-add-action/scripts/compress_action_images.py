#!/usr/bin/env python3
"""Normalize action images to package-local files no larger than 512 KiB."""

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = ImageOps = None

MAX_BYTES = 512 * 1024
PASSTHROUGH = {".png", ".jpg", ".jpeg", ".webp"}


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-") or "image"


def open_normalized(source):
    if Image is None:
        raise RuntimeError("Pillow is required: python3 -m pip install Pillow")
    with Image.open(source) as opened:
        opened.verify()
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.getchannel("A"))
            return background
        return image.convert("RGB")


def compress_one(source, destination_dir, asset_id):
    if not source.is_file() or source.stat().st_size <= 0:
        raise ValueError(f"invalid image: {source}")
    image = open_normalized(source)
    suffix = source.suffix.lower()
    destination_dir.mkdir(parents=True, exist_ok=True)
    if source.stat().st_size <= MAX_BYTES and suffix in PASSTHROUGH:
        destination = destination_dir / f"{safe_name(asset_id)}{suffix}"
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        return destination
    destination = destination_dir / f"{safe_name(asset_id)}.jpg"
    while min(image.size) >= 320:
        for quality in (88, 82, 76, 70, 64, 58, 52, 46, 40):
            image.save(destination, "JPEG", quality=quality, optimize=True, progressive=True)
            if destination.stat().st_size <= MAX_BYTES:
                return destination
        image = image.resize(
            (max(1, int(image.width * 0.85)), max(1, int(image.height * 0.85))),
            Image.Resampling.LANCZOS,
        )
    raise RuntimeError(f"cannot compress {source} under 512 KiB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = json.loads(json.dumps(manifest, ensure_ascii=False))
        destination_dir = args.output.parent / "assets"
        for index, asset in enumerate(result.get("assets", [])):
            raw = PurePosixPath(str(asset.get("localPath", "")).replace("\\", "/"))
            if raw.is_absolute() or ".." in raw.parts:
                raise ValueError(f"assets[{index}].localPath must stay inside the package")
            source = args.manifest.parent.joinpath(*raw.parts)
            destination = compress_one(source, destination_dir, asset.get("assetId", f"asset-{index}"))
            asset["localPath"] = destination.relative_to(args.output.parent).as_posix()
            asset["preparedSha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
            asset.pop("review", None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"action image compression failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(args.output), "imageCount": len(result.get("assets", []))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
