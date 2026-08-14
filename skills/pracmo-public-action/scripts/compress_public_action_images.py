#!/usr/bin/env python3
"""Create an upload-ready Public Action JSON whose local images are <= 512 KiB."""

import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - environment-dependent failure path
    Image = None
    ImageOps = None


SCRIPT_DIR = Path(__file__).resolve().parent
MAX_PUBLIC_IMAGE_BYTES = 512 * 1024
PASSTHROUGH_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def load_validator():
    path = SCRIPT_DIR / "validate_public_action_json.py"
    spec = importlib.util.spec_from_file_location("pracmo_public_action_validator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def safe_relative_dir(raw: str) -> PurePosixPath:
    value = PurePosixPath(raw.replace("\\", "/"))
    if value.is_absolute() or ".." in value.parts or not value.parts:
        raise ValueError("--assets-dir must be a safe relative directory")
    return value


def safe_name(asset_id: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", asset_id).strip(".-")
    return value or "image"


def flatten_to_rgb(image):
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def write_jpeg_under_limit(source: Path, destination: Path) -> None:
    if Image is None:
        raise RuntimeError("Pillow is required: python3 -m pip install Pillow")
    with Image.open(source) as opened:
        image = flatten_to_rgb(opened)
    quality_steps = (88, 82, 76, 70, 64, 58, 52, 46, 40)
    while min(image.size) >= 320:
        for quality in quality_steps:
            image.save(destination, "JPEG", quality=quality, optimize=True, progressive=True)
            if destination.stat().st_size <= MAX_PUBLIC_IMAGE_BYTES:
                return
        next_size = (max(1, int(image.width * 0.85)), max(1, int(image.height * 0.85)))
        image = image.resize(next_size, Image.Resampling.LANCZOS)
    raise RuntimeError(f"cannot compress {source} to 512 KiB without excessive resolution loss")


def optimize_file(source: Path, destination_dir: Path, asset_id: str) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f"image does not exist: {source}")
    if source.stat().st_size <= 0:
        raise ValueError(f"image is empty: {source}")
    suffix = source.suffix.lower()
    if source.stat().st_size <= MAX_PUBLIC_IMAGE_BYTES and suffix in PASSTHROUGH_SUFFIXES:
        destination = destination_dir / f"{safe_name(asset_id)}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        return destination
    destination = destination_dir / f"{safe_name(asset_id)}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_jpeg_under_limit(source, destination)
    return destination


def compress(payload: dict, source_json: Path, output_json: Path, assets_dir_raw: str) -> dict:
    validator = load_validator()
    validator.validate(payload, base_dir=source_json.parent, check_assets=False)
    assets_dir = safe_relative_dir(assets_dir_raw)
    destination_dir = output_json.parent.joinpath(*assets_dir.parts)
    rewritten = json.loads(json.dumps(payload, ensure_ascii=False))
    optimized_by_source: dict[str, str] = {}

    for asset in rewritten["assets"]:
        local_path = asset.get("localPath")
        if not local_path:
            continue
        if local_path not in optimized_by_source:
            source_relative = PurePosixPath(local_path.replace("\\", "/"))
            source = source_json.parent.joinpath(*source_relative.parts)
            destination = optimize_file(source, destination_dir, asset["assetId"])
            optimized_by_source[local_path] = destination.relative_to(output_json.parent).as_posix()
        asset["localPath"] = optimized_by_source[local_path]

    cover = rewritten["catalog"]["coverImage"]
    if "localPath" in cover:
        original = cover["localPath"]
        if original not in optimized_by_source:
            raise ValueError("catalog.coverImage.localPath must reference the cover asset source")
        cover["localPath"] = optimized_by_source[original]

    validator.validate(rewritten, base_dir=output_json.parent, check_assets=True)
    return rewritten


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--assets-dir", default="assets")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        rewritten = compress(payload, args.input, args.output, args.assets_dir)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(json.dumps(rewritten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(args.output)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"image compression failed: {exc}", file=sys.stderr)
        return 2
    sizes = [
        (args.output.parent / asset["localPath"]).stat().st_size
        for asset in rewritten["assets"]
        if "localPath" in asset
    ]
    print(json.dumps({"output": str(args.output), "images": len(sizes), "maxSizeBytes": max(sizes, default=0)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
