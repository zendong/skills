#!/usr/bin/env python3
"""Submit a finalized package and recover uncertain transport results by lookup."""

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_BASE = "https://apis.zendong.com.cn/open/v1"


def load_validator():
    spec = importlib.util.spec_from_file_location("validator", SCRIPT_DIR / "validate_learning_track_json.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_ledger(path, item):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")


def request_json(method, url, api_key, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    request = urllib.request.Request(url, data=data, method=method, headers={"X-API-Key": api_key, "Accept": "application/json"})
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode())
    if isinstance(body, dict) and body.get("success") is False:
        raise RuntimeError(f"{body.get('code', 'API_ERROR')}: {body.get('message', 'request failed')}")
    return body.get("data", body) if isinstance(body, dict) else body


def submit(payload, api_key, base, ledger, timeout, requester=request_json):
    validator = load_validator()
    digest = hashlib.sha256(validator.canonical_payload(payload)).hexdigest()
    request_id = payload["clientRequestId"]
    append_ledger(ledger, {"clientRequestId": request_id, "payloadHash": digest, "status": "pending", "at": dt.datetime.now(dt.timezone.utc).isoformat()})
    try:
        result = requester("POST", base + "/learning-tracks/import", api_key, payload, timeout)
    except (urllib.error.HTTPError, RuntimeError):
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        append_ledger(ledger, {"clientRequestId": request_id, "payloadHash": digest, "status": "uncertain", "reason": str(exc), "at": dt.datetime.now(dt.timezone.utc).isoformat()})
        status = requester("GET", base + "/learning-tracks/imports/" + urllib.parse.quote(request_id, safe=""), api_key, None, timeout)
        if status.get("status") != "success" or not status.get("result"):
            raise RuntimeError(f"import lookup returned {status.get('status', 'unknown')}: {status.get('safeSummary', '')}")
        result = status["result"]
    append_ledger(ledger, {"clientRequestId": request_id, "payloadHash": digest, "status": "succeeded", "response": result, "at": dt.datetime.now(dt.timezone.utc).isoformat()})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    api_key = os.environ.get("PRACMO_APIKEY", "").strip()
    if not api_key:
        print("PRACMO_APIKEY is required; set it locally and do not paste it into chat", file=sys.stderr)
        return 2
    base = os.environ.get("PRACMO_OPEN_API_BASE", DEFAULT_BASE).rstrip("/")
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        load_validator().validate(payload, base_dir=args.input.parent, mode="finalized")
        result = submit(payload, api_key, base, args.ledger, args.timeout)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, urllib.error.HTTPError) as exc:
        print(f"learning track import failed: {exc}", file=sys.stderr)
        return 2
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
