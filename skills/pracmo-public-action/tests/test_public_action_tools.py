import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
FIXTURE = SKILL_DIR / "tests" / "fixtures" / "valid-public-action.json"
FIXTURES = {
    "self_directed": SKILL_DIR / "tests" / "fixtures" / "valid-self-directed.json",
    "puki_reading": SKILL_DIR / "tests" / "fixtures" / "valid-puki-reading.json",
    "puki_quick_qa": SKILL_DIR / "tests" / "fixtures" / "valid-puki-quick-qa.json",
    "follow_along": FIXTURE,
}
VALIDATOR = SKILL_DIR / "scripts" / "validate_public_action_json.py"
EXPORTER = SKILL_DIR / "scripts" / "public_action_json_to_markdown.py"
FINALIZER = SKILL_DIR / "scripts" / "finalize_public_action_assets.py"
PUBLISHER = SKILL_DIR / "scripts" / "publish_public_action.py"
COMPRESSOR = SKILL_DIR / "scripts" / "compress_public_action_images.py"
MAX_PUBLIC_IMAGE_BYTES = 512 * 1024


class PublicActionToolsTest(unittest.TestCase):
    def test_skill_identity_is_pracmo_public_action(self):
        self.assertEqual(SKILL_DIR.name, "pracmo-public-action")

        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: pracmo-public-action", skill_text)
        self.assertIn("# Pracmo Public Action", skill_text)
        self.assertNotIn("name: pracmo-action", skill_text)

        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Pracmo Public Action"', metadata)
        self.assertIn("$pracmo-public-action", metadata)
        self.assertNotIn("$pracmo-action", metadata)

        evals = json.loads((SKILL_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(evals["skill_name"], "pracmo-public-action")

    def run_validator(self, path: Path, *, check_assets: bool = False, finalized: bool = False):
        command = [sys.executable, str(VALIDATOR), str(path), "--json"]
        if check_assets:
            command.append("--check-assets")
        if finalized:
            command.append("--finalized")
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_fixtures_cover_all_action_modes(self):
        for name, fixture in FIXTURES.items():
            with self.subTest(name=name):
                first = self.run_validator(fixture)
                second = self.run_validator(fixture)
                self.assertEqual(first.returncode, 0, first.stderr)
                self.assertEqual(second.returncode, 0, second.stderr)
                first_payload = json.loads(first.stdout)
                second_payload = json.loads(second.stdout)
                self.assertEqual(first_payload["schemaVersion"], "pracmo-public-action@v2")
                self.assertEqual(first_payload["payloadHash"], second_payload["payloadHash"])
                self.assertEqual(len(first_payload["payloadHash"]), 64)

    def test_rejects_type_specific_fields_from_another_mode(self):
        payload = json.loads(FIXTURES["self_directed"].read_text(encoding="utf-8"))
        payload["template"]["followPlan"] = json.loads(
            FIXTURES["follow_along"].read_text(encoding="utf-8")
        )["template"]["followPlan"]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = self.run_validator(path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("followPlan", result.stderr)

    def test_rejects_private_or_unknown_template_fields(self):
        payload = json.loads(FIXTURES["self_directed"].read_text(encoding="utf-8"))
        payload["template"]["stateLink"] = {"stateId": "private-state"}
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = self.run_validator(path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("stateLink", result.stderr)

    def test_rejects_generated_instruction_over_1000_characters(self):
        payload = json.loads(FIXTURES["puki_reading"].read_text(encoding="utf-8"))
        payload["template"]["generatedContentConfig"]["instruction"] = "深" * 1001
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = self.run_validator(path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("1000", result.stderr)

    def test_rejects_checkpoint_outside_levels(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["template"]["followPlan"]["checkpoints"][0]["levelIndex"] = 2
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = self.run_validator(path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("levelIndex", result.stderr)

    def test_rejects_absolute_local_asset_path(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["assets"][0]["localPath"] = "/tmp/cover.png"
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = self.run_validator(path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("relative", result.stderr)

    def test_rejects_local_public_image_larger_than_512_kib(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "cover.png").write_bytes(b"x" * (MAX_PUBLIC_IMAGE_BYTES + 1))
            path = root / "public-action.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = self.run_validator(path, check_assets=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("512 KiB", result.stderr)

    def test_rejects_finalized_public_image_larger_than_512_kib(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        asset = payload["assets"][0]
        asset.pop("localPath")
        asset.update({
            "objectKey": "material/1001/action-assets/staging/cover/x.png",
            "url": "https://oss.example.com/x.png",
            "sha256": "a" * 64,
            "contentType": "image/png",
            "sizeBytes": MAX_PUBLIC_IMAGE_BYTES + 1,
        })
        payload["catalog"]["coverImage"] = {
            "objectKey": asset["objectKey"],
            "url": asset["url"],
            "alt": "cover",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "finalized.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = self.run_validator(path, finalized=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("512 KiB", result.stderr)

    def test_compressor_updates_json_and_keeps_every_image_below_512_kib(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["assets"][0]["localPath"] = "source/cover.ppm"
        payload["catalog"]["coverImage"]["localPath"] = "source/cover.ppm"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            source_dir.mkdir()
            pixels = bytearray()
            for y in range(768):
                for x in range(1024):
                    pixels.extend(((x * 17 + y * 31) % 256, (x * 43 + y * 7) % 256, (x * 3 + y * 61) % 256))
            (source_dir / "cover.ppm").write_bytes(b"P6\n1024 768\n255\n" + pixels)
            source = root / "draft.json"
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            output = root / "public-action.json"
            result = subprocess.run(
                [sys.executable, str(COMPRESSOR), str(source), "-o", str(output), "--assets-dir", "assets"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            optimized = json.loads(output.read_text(encoding="utf-8"))
            relative = optimized["assets"][0]["localPath"]
            optimized_file = root / relative
            self.assertEqual(relative, optimized["catalog"]["coverImage"]["localPath"])
            self.assertEqual(optimized_file.suffix, ".jpg")
            self.assertLessEqual(optimized_file.stat().st_size, MAX_PUBLIC_IMAGE_BYTES)
            self.assertEqual(payload["assets"][0]["localPath"], "source/cover.ppm")
            validated = self.run_validator(output, check_assets=True)
            self.assertEqual(validated.returncode, 0, validated.stderr)

    def test_markdown_export_is_deterministic_and_has_no_local_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "first.md"
            second = Path(temp_dir) / "second.md"
            for output in (first, second):
                result = subprocess.run(
                    [sys.executable, str(EXPORTER), str(FIXTURE), "-o", str(output)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            first_text = first.read_text(encoding="utf-8")
            self.assertEqual(first_text, second.read_text(encoding="utf-8"))
            self.assertIn("# 晨间轻阅读", first_text)
            self.assertIn("形成轻阅读节奏", first_text)
            self.assertNotIn("cover.png", first_text)

    def test_asset_finalizer_uploads_and_removes_local_paths(self):
        payload = json.loads(FIXTURES["self_directed"].read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "cover.png").write_bytes(b"png bytes")
            source = root / "public-action.json"
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            uploader = root / "uploader.py"
            uploader.write_text(
                "#!/usr/bin/env python3\nimport json\nprint(json.dumps({'objectKey':'material/1001/action-assets/staging/cover/x.png','url':'https://oss.example.com/x.png','contentType':'image/png','sizeBytes':9}))\n",
                encoding="utf-8",
            )
            uploader.chmod(0o755)
            output = root / "finalized.json"
            result = subprocess.run(
                [sys.executable, str(FINALIZER), str(source), "-o", str(output), "--uploader", str(uploader)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            finalized = json.loads(output.read_text(encoding="utf-8"))
            self.assertNotIn("localPath", finalized["assets"][0])
            self.assertEqual(finalized["catalog"]["coverImage"]["url"], "https://oss.example.com/x.png")
            self.assertEqual(len(finalized["assets"][0]["sha256"]), 64)

    def test_finalizer_uses_bundled_uploader(self):
        spec = importlib.util.spec_from_file_location("finalizer", FINALIZER)
        finalizer = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(finalizer)
        self.assertEqual(finalizer.DEFAULT_UPLOADER.parent, SKILL_DIR / "scripts")
        self.assertTrue(finalizer.DEFAULT_UPLOADER.is_file())

    def test_publish_stops_before_network_without_api_key(self):
        env = dict(__import__("os").environ)
        env.pop("PRACMO_APIKEY", None)
        result = subprocess.run(
            [sys.executable, str(PUBLISHER), str(FIXTURE)],
            capture_output=True, text=True, check=False, env=env,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("PRACMO_APIKEY", result.stderr)

    def test_uncertain_submission_recovers_by_idempotency_lookup_and_records_ledger(self):
        spec = importlib.util.spec_from_file_location("publisher", PUBLISHER)
        publisher = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(publisher)
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        calls = []

        def requester(method, url, api_key, body=None, timeout=30):
            calls.append((method, url, api_key, body, timeout))
            if method == "POST":
                raise urllib.error.URLError("connection reset after send")
            return {"publicActionId": "public_1", "reviewStatus": "pending"}

        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = Path(temp_dir) / "ledger.jsonl"
            result = publisher.submit_with_recovery(
                payload,
                api_key="secret",
                base="https://api.example.test/open/v1",
                ledger=ledger,
                requester=requester,
            )
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(result["publicActionId"], "public_1")
        self.assertEqual([entry["status"] for entry in entries], ["pending", "uncertain", "succeeded"])
        self.assertEqual(calls[1][0], "GET")
        self.assertTrue(calls[1][1].endswith("/submissions/public-action-morning-read-20260808"))

    def test_category_preflight_accepts_server_category(self):
        spec = importlib.util.spec_from_file_location("publisher", PUBLISHER)
        publisher = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(publisher)
        payload = json.loads(FIXTURES["self_directed"].read_text(encoding="utf-8"))
        calls = []

        def requester(method, url, api_key, body=None, timeout=30):
            calls.append((method, url, body))
            return {"items": [{"code": "habit", "label": "习惯养成"}]}

        publisher.validate_category_with_server(
            payload,
            api_key="secret",
            base="https://api.example.test/open/v1",
            requester=requester,
        )
        self.assertEqual(calls, [("GET", "https://api.example.test/open/v1/public-actions/categories", None)])

    def test_category_preflight_rejects_unknown_category_before_asset_upload(self):
        spec = importlib.util.spec_from_file_location("publisher", PUBLISHER)
        publisher = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(publisher)
        payload = json.loads(FIXTURES["self_directed"].read_text(encoding="utf-8"))

        def requester(method, url, api_key, body=None, timeout=30):
            return {"items": [{"code": "reading", "label": "阅读"}]}

        with self.assertRaisesRegex(ValueError, "habit"):
            publisher.validate_category_with_server(
                payload,
                api_key="secret",
                base="https://api.example.test/open/v1",
                requester=requester,
            )

    def test_mode_specific_generated_contract_rules(self):
        cases = []
        reading = json.loads(FIXTURES["puki_reading"].read_text(encoding="utf-8"))
        reading["template"]["generatedContentConfig"]["quickQa"] = {"questionType": "auto"}
        cases.append((reading, "quickQa"))
        quick_qa = json.loads(FIXTURES["puki_quick_qa"].read_text(encoding="utf-8"))
        quick_qa["template"]["generatedContentConfig"].pop("quickQa")
        cases.append((quick_qa, "quickQa"))
        follow = json.loads(FIXTURES["follow_along"].read_text(encoding="utf-8"))
        follow["template"]["completionMode"] = "text"
        cases.append((follow, "one_tap"))

        for index, (payload, message) in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "invalid.json"
                path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                result = self.run_validator(path)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)


if __name__ == "__main__":
    unittest.main()
