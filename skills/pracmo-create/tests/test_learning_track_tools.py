import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load("validator", "scripts/validate_learning_track_json.py")
renderer = load("renderer", "scripts/learning_track_json_to_markdown.py")
uploader = load("uploader", "scripts/pracmo_oss_upload.py")


class LearningTrackToolsTest(unittest.TestCase):
    def skeleton(self):
        return json.loads((ROOT / "references/examples/skeleton.json").read_text(encoding="utf-8"))

    def test_skeleton_authoring_is_valid(self):
        payload = self.skeleton()
        validator.validate(payload, base_dir=ROOT, mode="authoring")
        self.assertEqual(payload["path"]["currentStateKey"], "current")

    def test_broken_state_reference_is_rejected(self):
        payload = self.skeleton()
        payload["actions"] = [{
            "actionKey": "walk", "title": "散步", "scheduleType": "daily",
            "timezone": "Asia/Shanghai", "startDate": "2026-08-15", "deadlineLocalTime": "20:00",
            "gracePolicy": "none", "completionMode": "one_tap", "contentMode": "self_directed",
            "stateLink": {"stateKey": "missing", "relationRole": "advance", "criterionIds": ["x"]},
        }]
        with self.assertRaises(validator.ContractError):
            validator.validate(payload, base_dir=ROOT, mode="authoring")

    def test_finalized_rejects_local_path(self):
        payload = self.skeleton()
        payload["assets"] = [{"assetId": "cover", "role": "cover", "localPath": "source-assets/cover.jpg", "alt": "cover"}]
        with self.assertRaises(validator.ContractError):
            validator.validate(payload, base_dir=ROOT, mode="finalized")

    def test_empty_reminder_object_is_rejected_before_import(self):
        payload = self.skeleton()
        payload["actions"] = [{
            "actionKey": "walk", "title": "散步", "scheduleType": "daily",
            "scheduleConfigJson": "{}", "timezone": "Asia/Shanghai",
            "startDate": "2026-08-15", "deadlineLocalTime": "20:00",
            "gracePolicy": "none", "completionMode": "one_tap",
            "reminderConfigJson": "{}", "contentMode": "self_directed",
        }]
        with self.assertRaises(validator.ContractError):
            validator.validate(payload, base_dir=ROOT, mode="authoring")

    def test_finalized_cover_must_reference_a_verified_asset(self):
        payload = self.skeleton()
        payload["track"]["coverImage"] = {"url": "https://example.test/cover.png"}
        with self.assertRaises(validator.ContractError):
            validator.validate(payload, base_dir=ROOT, mode="finalized")

    def test_markdown_contains_goal_path_and_empty_activity_hints(self):
        output = renderer.render(self.skeleton())
        self.assertIn("## 核心目标", output)
        self.assertIn("## 目标路径", output)
        self.assertIn("可继续规划的甲程骨架", output)

    def test_payload_hash_is_stable_across_key_order(self):
        payload = self.skeleton()
        reordered = json.loads(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        self.assertEqual(validator.canonical_payload(payload), validator.canonical_payload(reordered))

    def test_oss_object_key_is_isolated_by_request_id(self):
        key = uploader.build_object_key(
            "material/1001/learning-track-assets/", "walking-habit-20260814-v1", Path("封面 图.jpg"),
            stamp="20260814T120000Z", nonce="abc123",
        )
        self.assertEqual(
            key,
            "material/1001/learning-track-assets/walking-habit-20260814-v1/20260814T120000Z-abc123-jpg",
        )


if __name__ == "__main__":
    unittest.main()
