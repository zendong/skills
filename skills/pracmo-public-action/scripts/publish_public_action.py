#!/usr/bin/env python3
"""Validate, finalize, submit and recover a Public Action submission."""

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_BASE = "https://apis.zendong.com.cn/open/v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def append_ledger(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def request_json(method: str, url: str, api_key: str, payload: dict | None = None, timeout: int = 30) -> dict:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("X-API-Key", api_key)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    if isinstance(body, dict) and body.get("success") is False:
        raise RuntimeError(f"{body.get('code', 'API_ERROR')}: {body.get('message', 'request failed')}")
    return body.get("data", body) if isinstance(body, dict) else body


def submit_with_recovery(payload: dict, *, api_key: str, base: str, ledger: Path, timeout: int = 30, requester=request_json) -> dict:
    """Submit once and resolve an uncertain transport result via the idempotency lookup."""
    canonical = load_module("pracmo_public_action_validator_hash", SCRIPT_DIR / "validate_public_action_json.py").canonical_payload(payload)
    payload_hash = hashlib.sha256(canonical).hexdigest()
    client_request_id = payload["clientRequestId"]
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    append_ledger(ledger, {"clientRequestId": client_request_id, "payloadHash": payload_hash, "status": "pending", "at": now})
    try:
        result = requester("POST", base + "/public-actions", api_key, payload, timeout)
    except (urllib.error.HTTPError, RuntimeError):
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        append_ledger(ledger, {"clientRequestId": client_request_id, "payloadHash": payload_hash, "status": "uncertain", "reason": str(exc), "at": now})
        result = requester(
            "GET",
            base + "/public-actions/submissions/" + urllib.parse.quote(client_request_id, safe=""),
            api_key,
            None,
            timeout,
        )
    append_ledger(ledger, {"clientRequestId": client_request_id, "payloadHash": payload_hash, "status": "succeeded", "response": result, "at": dt.datetime.now(dt.timezone.utc).isoformat()})
    return result


def validate_category_with_server(
    payload: dict,
    *,
    api_key: str,
    base: str,
    timeout: int = 30,
    requester=request_json,
) -> None:
    """Fail before asset upload when the server does not recognize the category."""
    result = requester("GET", base + "/public-actions/categories", api_key, None, timeout)
    items = result.get("items", []) if isinstance(result, dict) else []
    allowed = {
        str(item.get("code", "")).strip()
        for item in items
        if isinstance(item, dict) and str(item.get("code", "")).strip()
    }
    category = str(payload.get("catalog", {}).get("category", "")).strip()
    if not allowed:
        raise RuntimeError("server returned no public action categories")
    if category not in allowed:
        raise ValueError(
            f"catalog.category {category!r} is not enabled by the server; "
            f"allowed: {', '.join(sorted(allowed))}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--ledger", type=Path, default=SKILL_DIR / "cache" / "submission-ledger.jsonl")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--finalized-output", type=Path)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    api_key = os.environ.get("PRACMO_APIKEY", "").strip()
    if not api_key:
        print("PRACMO_APIKEY is required; set it locally and do not paste it into chat", file=sys.stderr)
        return 2
    base = os.environ.get("PRACMO_OPEN_API_BASE", DEFAULT_BASE).rstrip("/")
    validator = load_module("pracmo_public_action_validator", SCRIPT_DIR / "validate_public_action_json.py")
    finalizer = load_module("pracmo_public_action_finalizer", SCRIPT_DIR / "finalize_public_action_assets.py")
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        validator.validate(payload, base_dir=args.input.parent, check_assets=True)
        validate_category_with_server(payload, api_key=api_key, base=base, timeout=args.timeout)
        if any("localPath" in asset for asset in payload["assets"]):
            payload = finalizer.finalize(payload, args.input, finalizer.DEFAULT_UPLOADER)
        validator.validate(payload, base_dir=args.input.parent, finalized=True)
        finalized_output = args.finalized_output
        if finalized_output is None:
            finalized_output = args.input.with_name("public-action.finalized.json")
        finalized_output.parent.mkdir(parents=True, exist_ok=True)
        finalized_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"public action preparation failed: {exc}", file=sys.stderr)
        return 2

    try:
        result = submit_with_recovery(payload, api_key=api_key, base=base, ledger=args.ledger, timeout=args.timeout)
    except (urllib.error.HTTPError, RuntimeError) as exc:
        canonical = validator.canonical_payload(payload)
        append_ledger(args.ledger, {"clientRequestId": payload["clientRequestId"], "payloadHash": hashlib.sha256(canonical).hexdigest(), "status": "failed", "reason": str(exc), "at": dt.datetime.now(dt.timezone.utc).isoformat()})
        print(f"submission failed: {exc}", file=sys.stderr)
        return 2
    except (urllib.error.URLError, TimeoutError, OSError) as recovery_exc:
        print(f"submission state is uncertain; lookup failed: {recovery_exc}", file=sys.stderr)
        return 3

    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
