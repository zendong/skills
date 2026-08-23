from pathlib import Path
import base64
import hashlib
import importlib.util
import json
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillContractTest(unittest.TestCase):
    def test_skill_requires_existing_track_and_private_endpoint(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: pracmo-add-action", text)
        self.assertIn("GET /open/v1/learning-tracks", text)
        self.assertIn("POST /open/v1/learning-tracks/:trackId/actions", text)
        self.assertIn("请先到璞奇手机端创建甲程", text)
        self.assertIn("不得创建甲程", text)
        self.assertNotIn("/public-actions", text)

    def test_api_script_has_no_public_submission_route(self):
        text = (ROOT / "scripts" / "pracmo-open-api.sh").read_text(encoding="utf-8")
        self.assertIn('learning-tracks/${track_id}/actions', text)
        self.assertNotIn("public-actions", text)

    def test_skill_has_follow_image_safety_gate(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("不得依赖模型参数记忆", text)
        self.assertIn("references/follow-image-grounding-and-review.md", text)
        self.assertIn("validate_action_package.py", text)
        self.assertIn("finalize_action_images.py", text)
        self.assertIn("任何一项未通过都不得创建", text)


class ActionImageToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module("action_validator", "scripts/validate_action_package.py")
        cls.finalizer = load_module("action_finalizer", "scripts/finalize_action_images.py")
        cls.uploader = load_module("action_uploader", "scripts/pracmo_oss_upload.py")

    def package(self, directory):
        image = directory / "wall-pushup.png"
        image.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        ))
        reviewed_sha = hashlib.sha256(image.read_bytes()).hexdigest()
        request = {
            "schemaVersion": "pracmo-track-action@v1",
            "clientRequestId": "action-20260823-images-v1",
            "action": {
                "title": "俯卧撑入门",
                "description": "循序练习俯卧撑",
                "scheduleType": "daily",
                "timezone": "Asia/Shanghai",
                "startDate": "2026-08-23",
                "deadlineLocalTime": "20:00",
                "completionMode": "one_tap",
                "contentMode": "follow_along",
                "followPlan": {
                    "afterCompletionPolicy": "continue_last_level",
                    "levels": [{
                        "title": "墙壁俯卧撑",
                        "targetSessions": 3,
                        "promotionCriterion": "动作稳定完成 3 组",
                        "estMinutes": 8,
                        "contentBlocks": [
                            {"blockType": "text", "textContent": "保持身体成一直线。"},
                            {
                                "blockType": "image",
                                "mediaUrl": "asset://wall-pushup",
                                "caption": "墙壁俯卧撑起始姿势",
                            },
                        ],
                    }],
                    "checkpoints": [],
                },
            },
        }
        manifest = {
            "schemaVersion": "pracmo-action-images@v1",
            "clientRequestId": request["clientRequestId"],
            "resources": [{
                "resourceId": "r1",
                "title": "Official exercise guidance",
                "publisher": "Example Health Authority",
                "url": "https://example.org/exercise-guidance",
                "sourceType": "official",
                "retrievedAt": "2026-08-23T10:00:00+08:00",
                "version": "2026-08",
            }],
            "assets": [{
                "assetId": "wall-pushup",
                "localPath": "wall-pushup.png",
                "altText": "墙壁俯卧撑起始姿势",
                "factuality": "factual",
                "provenance": "generated_from_sources",
                "license": "original",
                "claims": [{
                    "claimId": "claim-1",
                    "text": "墙壁俯卧撑起始时双手支撑墙面并保持躯干稳定",
                    "resourceIds": ["r1"],
                }],
                "expectedVisibleText": [],
                "containsNumbers": False,
                "expectedValues": [],
                "expectedRelations": [{
                    "subject": "躯干",
                    "relation": "保持",
                    "object": "稳定直线",
                    "notes": "起始姿势",
                }],
                "usedBy": [{"levelIndex": 0, "blockIndex": 1}],
                "review": {
                    "sourceVerified": True,
                    "pixelInspected": True,
                    "textVerified": True,
                    "numbersVerified": True,
                    "motionLogicVerified": True,
                    "planConsistencyVerified": True,
                    "safetyVerified": True,
                    "mobileReadabilityVerified": True,
                    "misleadingCueChecked": True,
                    "reviewedSha256": reviewed_sha,
                    "reviewedAt": "2026-08-23T11:00:00+08:00",
                    "notes": "核对支撑点、躯干直线、caption 与练阶要求。",
                },
            }],
        }
        return request, manifest, image

    def test_reviewed_package_accepts_grounded_follow_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest, _ = self.package(directory)
            self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_changed_file_after_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest, image = self.package(directory)
            image.write_bytes(image.read_bytes() + b"changed")
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_unknown_source_and_failed_safety_review_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest, _ = self.package(directory)
            manifest["assets"][0]["claims"][0]["resourceIds"] = ["missing"]
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")
            manifest["assets"][0]["claims"][0]["resourceIds"] = ["r1"]
            manifest["assets"][0]["review"]["safetyVerified"] = False
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_local_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest, _ = self.package(directory)
            manifest["assets"][0]["localPath"] = "../secret.png"
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_symlink_outside_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            directory = Path(tmp)
            outside = Path(outside_tmp) / "outside.png"
            outside.write_bytes(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ))
            request, manifest, _ = self.package(directory)
            link = directory / "outside-link.png"
            link.symlink_to(outside)
            manifest["assets"][0]["localPath"] = link.name
            manifest["assets"][0]["review"]["reviewedSha256"] = hashlib.sha256(outside.read_bytes()).hexdigest()
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_finalized_request_rejects_malformed_https(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, _, _ = self.package(directory)
            request["action"]["followPlan"]["levels"][0]["contentBlocks"][1]["mediaUrl"] = "https:/missing-host.png"
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_final_request(request)

    def test_finalizer_replaces_placeholder_without_leaking_manifest_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest, _ = self.package(directory)
            final_request = self.finalizer.replace_assets(
                request,
                manifest,
                {"wall-pushup": {"url": "https://cdn.example.org/wall-pushup.png"}},
            )
            encoded = json.dumps(final_request, ensure_ascii=False)
            self.assertIn("https://cdn.example.org/wall-pushup.png", encoded)
            self.assertNotIn("asset://", encoded)
            self.assertNotIn('"assetId"', encoded)
            self.assertNotIn('"resources"', encoded)
            self.assertEqual(set(final_request), {"schemaVersion", "clientRequestId", "action"})

    def test_deterministic_object_key_uses_reviewed_hash(self):
        key = self.uploader.build_object_key(
            "material/1001/practice-assets/",
            "action-20260823-images-v1",
            "wall-pushup",
            "a" * 64,
            Path("姿势 图.png"),
        )
        self.assertEqual(
            key,
            "material/1001/practice-assets/action-20260823-images-v1/wall-pushup-" + "a" * 16 + ".png",
        )


if __name__ == "__main__":
    unittest.main()
