#!/usr/bin/env python3
"""Upload one reviewed private-exercise image using Pracmo OSS STS."""

import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

DEFAULT_BASE = "https://apis.zendong.com.cn/open/v1"
MAX_IMAGE_BYTES = 512 * 1024
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$")


def api_get(base, path, api_key):
    request = urllib.request.Request(base.rstrip("/") + "/" + path.lstrip("/"))
    request.add_header("X-API-Key", api_key)
    request.add_header("Accept", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    if isinstance(body, dict) and body.get("success") is False:
        raise RuntimeError(f"{body.get('code', 'API_ERROR')}: {body.get('message', 'request failed')}")
    return body.get("data", body)


def safe_name(path):
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", path.name).strip("-.")
    return name or "image.bin"


def build_object_key(prefix, request_id, path, stamp=None, nonce=None):
    if not REQUEST_ID_PATTERN.fullmatch(request_id):
        raise ValueError("clientRequestId format is invalid")
    stamp = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    nonce = nonce or uuid.uuid4().hex[:10]
    return f"{prefix}{request_id}/{stamp}-{nonce}-{safe_name(path)}"


def upload(path, request_id, api_key, base):
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_IMAGE_BYTES:
        raise ValueError("image must exist and be 512 KiB or smaller")
    content_type = mimetypes.guess_type(path.name)[0] or ""
    if content_type == "image/jpg":
        content_type = "image/jpeg"
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError(f"unsupported image type: {content_type or path.suffix}")

    config = api_get(base, "oss/config", api_key)
    sts = api_get(base, "oss/stsToken", api_key)
    bucket_name = str(config.get("bucketName", "")).strip()
    endpoint = str(config.get("ossEndpoint", "")).strip()
    account_prefix = str(config.get("objectKeyPrefix", "")).strip()
    prefix = str((config.get("objectKeyPrefixes") or {}).get("practiceAssets", "")).strip()
    if not bucket_name or not endpoint or not account_prefix or not prefix:
        raise RuntimeError("OSS config is missing bucket, endpoint, or practiceAssets prefix")
    if not prefix.startswith(account_prefix):
        raise RuntimeError("practiceAssets prefix is outside the account OSS prefix")

    access_key_id = sts.get("AccessKeyId") or sts.get("accessKeyId")
    access_key_secret = sts.get("AccessKeySecret") or sts.get("accessKeySecret")
    security_token = sts.get("SecurityToken") or sts.get("securityToken")
    if not access_key_id or not access_key_secret or not security_token:
        raise RuntimeError("STS token is incomplete")
    try:
        import oss2
    except ImportError as exc:
        raise RuntimeError("Python package oss2 is required: python3 -m pip install oss2") from exc

    object_key = build_object_key(prefix, request_id, path)
    auth = oss2.StsAuth(access_key_id, access_key_secret, security_token)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    bucket.put_object_from_file(object_key, str(path), headers={"Content-Type": content_type})
    host = re.sub(r"^https?://", "", endpoint).rstrip("/")
    return {
        "objectKey": object_key,
        "url": f"https://{bucket_name}.{host}/{quote(object_key, safe='/')}",
        "contentType": content_type,
        "sizeBytes": path.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    api_key = os.environ.get("PRACMO_APIKEY", "").strip()
    if not api_key:
        print("pracmo-oss-upload: PRACMO_APIKEY is required", file=sys.stderr)
        return 2
    try:
        result = upload(args.file, args.request_id, api_key, os.environ.get("PRACMO_OPEN_API_BASE", DEFAULT_BASE))
    except Exception as exc:
        print(f"pracmo-oss-upload: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
