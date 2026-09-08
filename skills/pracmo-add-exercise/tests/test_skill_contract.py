from pathlib import Path
import base64
import copy
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
        self.assertIn("请先到多练手机端创建甲程", text)
        self.assertIn("不得创建甲程", text)
        self.assertNotIn("/learning-tracks/import", text)
        self.assertNotIn("/learning-tracks/with-exercise", text)

    def test_api_script_has_no_track_creation_route(self):
        text = (ROOT / "scripts" / "pracmo-open-api.sh").read_text(encoding="utf-8")
        self.assertIn('learning-tracks/${track_id}/exercises', text)
        self.assertIn('image-url', text)
        self.assertIn('replace-image', text)
        self.assertNotIn("with-exercise", text)
        self.assertNotIn("learning-tracks/import", text)

    def test_skill_requires_collection_selection_or_creation_before_submit(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "exercise-json-contract.md").read_text(encoding="utf-8")
        combined = text + contract
        self.assertIn("GET /open/v1/learning-tracks/:trackId/exercise-collections", combined)
        self.assertIn("POST /open/v1/learning-tracks/:trackId/exercise-collections", combined)
        self.assertIn("甲程 + 练习册", combined)
        self.assertIn('"collectionId"', combined)

    def test_api_script_lists_and_creates_collections(self):
        text = (ROOT / "scripts" / "pracmo-open-api.sh").read_text(encoding="utf-8")
        self.assertIn("list-collections", text)
        self.assertIn("create-collection", text)
        self.assertIn('learning-tracks/${track_id}/exercise-collections', text)

    def test_skill_has_grounded_image_review_gate(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("不得依赖模型参数记忆", text)
        self.assertIn("references/image-grounding-and-review.md", text)
        self.assertIn("pracmocli images validate", text)
        self.assertIn("pracmocli images finalize", text)
        self.assertIn("pracmocli exercises add", text)
        self.assertIn("pracmocli exercises image-replace", text)
        self.assertIn("任何一项未通过都不得创建", text)

    def test_skill_requires_authentic_or_omitted_images(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("web_downloaded", text)
        self.assertIn("real_scene_generated", text)
        self.assertIn("中性手机界面", text)
        self.assertIn("宁可不使用图片", text)

    def test_skill_forbids_local_layout_and_requires_whole_image_generation(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        reference = (ROOT / "references" / "image-grounding-and-review.md").read_text(encoding="utf-8")
        combined = text + reference
        self.assertIn("整张完整成图", combined)
        self.assertIn("禁止本地排版", combined)
        self.assertIn("整图重新生成", combined)
        for forbidden_layout in ("Pillow", "Canvas", "SVG", "HTML/CSS", "后期贴字", "透视合成"):
            self.assertIn(forbidden_layout, combined)

    def test_skill_contract_places_all_explanations_on_options(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "exercise-json-contract.md").read_text(encoding="utf-8")
        combined = text + contract
        self.assertIn("options[].explanation", combined)
        self.assertIn("题目对象不得包含解析字段", combined)
        self.assertNotIn("questions[].explanation", combined)


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
                {
                    "content": "复用先前 token 的键和值",
                    "isCorrect": True,
                    "explanation": "图中箭头表示已计算的键和值被后续步骤复用。",
                },
                {
                    "content": "删除全部历史状态",
                    "isCorrect": False,
                    "explanation": "图中保留并复用历史键和值，并没有删除全部历史状态。",
                },
            ],
        }
        text_question = {
            "questionType": "true_false",
            "questionContent": "KV cache 可以复用先前 token 已计算的键和值。",
            "concept": {"name": "KV cache"},
            "testableClaim": "缓存可复用先前 token 的键和值",
            "bloomLevel": 1,
            "options": [
                {
                    "content": "正确",
                    "isCorrect": True,
                    "explanation": "该陈述与引用材料中 KV cache 的复用机制一致。",
                },
                {
                    "content": "错误",
                    "isCorrect": False,
                    "explanation": "该选项否定了材料明确描述的键和值复用机制。",
                },
            ],
        }
        request = {
            "schemaVersion": "pracmo-track-exercise@v1",
            "clientRequestId": "exercise-20260823-images-v1",
            "exercise": {
                "title": "缓存练习",
                "collectionId": "collection_selected",
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
                "sourceMode": "real_scene_generated",
                "sourceDetails": {
                    "generationMethod": "built-in image generation",
                    "resourceIds": ["r1"],
                    "wholeImageGenerated": True,
                    "localLayoutApplied": False,
                },
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
                    "authenticityVerified": True,
                    "scenePlausibilityVerified": True,
                    "deviceNeutralityVerified": True,
                    "privacyVerified": True,
                    "reviewedAt": "2026-08-23T11:00:00+08:00",
                    "notes": "逐字、逐箭头并独立作答复核。",
                },
            }],
        }
        return request, manifest

    def option_explanation_request(self, directory):
        request, manifest = self.package(directory)
        request = copy.deepcopy(request)
        for question in request["exercise"]["questions"]:
            question.pop("explanation", None)
            for option in question["options"]:
                option["explanation"] = (
                    "该选项符合题干中的事实与判断边界。"
                    if option["isCorrect"]
                    else "该选项与题干中的事实或判断边界不一致。"
                )
        return request, manifest

    def test_question_level_explanation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, _ = self.package(directory)
            request["exercise"]["questions"][0]["explanation"] = "旧的题目级统一解析。"
            with self.assertRaisesRegex(
                self.validator.ContractError,
                r"questions\[0\]\.explanation is not allowed",
            ):
                self.validator.validate_request_shape(request)

    def test_every_option_requires_its_own_explanation(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, _ = self.option_explanation_request(directory)
            request["exercise"]["questions"][0]["options"][0].pop("explanation")
            with self.assertRaisesRegex(
                self.validator.ContractError,
                r"questions\[0\]\.options\[0\]\.explanation must be a non-empty string",
            ):
                self.validator.validate_request_shape(request)

    def test_objective_options_cannot_share_one_generic_explanation(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, _ = self.option_explanation_request(directory)
            question = request["exercise"]["questions"][0]
            for option in question["options"]:
                option["explanation"] = "这是这道题的统一解析。"
            with self.assertRaisesRegex(
                self.validator.ContractError,
                r"option explanations must be distinct and option-specific",
            ):
                self.validator.validate_request_shape(request)

    def test_short_answer_uses_one_explained_reference_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, _ = self.option_explanation_request(directory)
            question = request["exercise"]["questions"][0]
            question["questionType"] = "short_answer"
            question["options"] = []
            with self.assertRaisesRegex(
                self.validator.ContractError,
                r"short_answer requires exactly one reference answer option",
            ):
                self.validator.validate_request_shape(request)

    def test_short_answer_accepts_one_explained_reference_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, _ = self.option_explanation_request(directory)
            question = request["exercise"]["questions"][0]
            question["questionType"] = "short_answer"
            question["options"] = [{
                "content": "说明复用历史键和值可以减少重复计算。",
                "isCorrect": True,
                "explanation": "评分时应同时提到复用对象和减少重复计算；只说速度更快不够完整。",
            }]
            self.validator.validate_request_shape(request)

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

    def test_unknown_source_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest = self.package(directory)
            manifest["assets"][0]["sourceMode"] = "fake_mockup"
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_generated_image_must_be_whole_image_without_local_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest = self.package(directory)
            manifest["assets"][0]["sourceDetails"]["wholeImageGenerated"] = False
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")
            manifest["assets"][0]["sourceDetails"]["wholeImageGenerated"] = True
            manifest["assets"][0]["sourceDetails"]["localLayoutApplied"] = True
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_package(request, manifest, directory, stage="reviewed")

    def test_authenticity_review_flags_are_required(self):
        for flag in (
            "authenticityVerified",
            "scenePlausibilityVerified",
            "deviceNeutralityVerified",
            "privacyVerified",
        ):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                request, manifest = self.package(directory)
                manifest["assets"][0]["review"][flag] = False
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

    def test_final_request_requires_real_collection_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest = self.package(directory)
            request = self.finalizer.replace_assets(
                request,
                manifest,
                {"kv-cache": {"url": "https://cdn.example.org/kv-cache.png"}},
            )
            del request["exercise"]["collectionId"]
            with self.assertRaises(self.validator.ContractError):
                self.validator.validate_final_request(request)

    def test_final_request_accepts_selected_collection_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            request, manifest = self.package(directory)
            request = self.finalizer.replace_assets(
                request,
                manifest,
                {"kv-cache": {"url": "https://cdn.example.org/kv-cache.png"}},
            )
            self.validator.validate_final_request(request)


if __name__ == "__main__":
    unittest.main()
