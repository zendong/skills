from pathlib import Path
import base64
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
        self.assertIn("name: pracmo-add-exercise", text)
        self.assertIn("GET /open/v1/learning-tracks", text)
        self.assertIn("POST /open/v1/learning-tracks/:trackId/exercises", text)
        self.assertIn("请先到璞奇手机端创建甲程", text)
        self.assertIn("不得创建甲程", text)
        self.assertNotIn("/learning-tracks/import", text)
        self.assertNotIn("/learning-tracks/with-exercise", text)

    def test_api_script_has_no_track_creation_route(self):
        text = (ROOT / "scripts" / "pracmo-open-api.sh").read_text(encoding="utf-8")
        self.assertIn('learning-tracks/${track_id}/exercises', text)
        self.assertNotIn("with-exercise", text)
        self.assertNotIn("learning-tracks/import", text)

    def test_skill_has_grounded_image_review_gate(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("不得依赖模型参数记忆", text)
        self.assertIn("references/image-grounding-and-review.md", text)
        self.assertIn("validate_exercise_package.py", text)
        self.assertIn("finalize_exercise_images.py", text)
        self.assertIn("任何一项未通过都不得创建", text)


class ExerciseImageToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module("exercise_validator", "scripts/validate_exercise_package.py")
        cls.finalizer = load_module("exercise_finalizer", "scripts/finalize_exercise_images.py")

    def package(self, directory):
        image = directory / "diagram.png"
        image.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        ))
        image_question = {
            "questionType": "single_choice",
            "questionContent": "观察图示：![KV 缓存流程](asset://kv-cache)",
            "concept": {"name": "KV cache"},
            "testableClaim": "缓存可复用先前 token 的键和值",
            "bloomLevel": 2,
            "options": [
                {"content": "复用先前 token 的键和值", "isCorrect": True},
                {"content": "删除全部历史状态", "isCorrect": False},
            ],
            "explanation": "图中箭头表示已计算键和值被后续步骤复用。",
        }
        text_question = {
            "questionType": "true_false",
            "questionContent": "KV cache 可以复用先前 token 已计算的键和值。",
            "concept": {"name": "KV cache"},
            "testableClaim": "缓存可复用先前 token 的键和值",
            "bloomLevel": 1,
            "options": [
                {"content": "正确", "isCorrect": True},
                {"content": "错误", "isCorrect": False},
            ],
            "explanation": "该陈述符合引用材料。",
        }
        request = {
            "schemaVersion": "pracmo-track-exercise@v1",
            "clientRequestId": "exercise-20260823-images-v1",
            "exercise": {
                "title": "缓存练习",
                "questions": [image_question] + [dict(text_question) for _ in range(9)],
            },
        }
        manifest = {
            "schemaVersion": "pracmo-exercise-images@v1",
            "clientRequestId": request["clientRequestId"],
            "resources": [{
                "resourceId": "r1",
                "title": "Authoritative paper",
                "url": "https://example.org/paper",
                "publisher": "Example Research Lab",
                "sourceType": "primary",
                "retrievedAt": "2026-08-23T10:00:00+08:00",
            }],
            "assets": [{
                "assetId": "kv-cache",
                "localPath": "diagram.png",
                "altText": "KV 缓存流程",
                "factuality": "factual",
                "provenance": "generated_from_sources",
                "license": "original",
                "claims": [{
                    "claimId": "claim-1",
                    "text": "缓存可复用先前 token 的键和值",
                    "resourceIds": ["r1"],
                }],
                "expectedVisibleText": ["KV Cache", "K", "V"],
                "expectedRelations": ["先前 token 的 K/V 指向后续解码步骤"],
                "containsNumbers": False,
                "expectedValues": [],
                "usedBy": [{"questionIndex": 0, "field": "questionContent"}],
                "review": {
                    "sourceVerified": True,
                    "pixelInspected": True,
                    "textVerified": True,
                    "logicVerified": True,
                    "numbersVerified": True,
                    "questionAnswerVerified": True,
                    "mobileReadabilityVerified": True,
                    "answerLeakageChecked": True,
                    "reviewedAt": "2026-08-23T11:00:00+08:00",
                    "notes": "逐字、逐箭头并独立作答复核。",
                },
            }],
        }
        return request, manifest

    def test_reviewed_package_accepts_grounded_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest = self.package(directory)
            self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_factual_image_without_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest = self.package(directory)
            manifest["assets"][0]["claims"][0]["resourceIds"] = []
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_failed_review_blocks_finalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest = self.package(directory)
            manifest["assets"][0]["review"]["logicVerified"] = False
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_uploaded_urls_replace_placeholders_and_leave_clean_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest = self.package(directory)
            final_request = self.finalizer.replace_assets(
                request,
                manifest,
                {"kv-cache": {"url": "https://cdn.example.org/kv-cache.png"}},
            )
            encoded = json.dumps(final_request, ensure_ascii=False)
            self.assertIn("https://cdn.example.org/kv-cache.png", encoded)
            self.assertNotIn("asset://", encoded)
            self.assertEqual(set(final_request), {"schemaVersion", "clientRequestId", "exercise"})


if __name__ == "__main__":
    unittest.main()
