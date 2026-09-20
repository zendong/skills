"""四个 skill（国内 ×2 + 海外 ×2）的契约测试。

## 为什么是一份参数化测试，而不是四份

国内与海外是两套完整隔离的部署（不同后端、不同 App、账号不互通），因此 skill 必须
各自写清自己的后端与 App 名称，且语言不同（国内中文 / 海外英文）。代价是**两套无法
逐字比对**，漂移风险回来了。

所以这里的防线是两条，缺一不可：

1. **区域隔离**：国内 skill 不得出现海外域名/区域参数，反之亦然 —— 防止把 key
   打到错的后端上（两套账号不互通，打错只会得到一个难懂的鉴权失败）。
2. **跨区域结构对等**：中英两版必须章节数、表格行数、代码块数、用到的 pracmocli
   子命令集合、以及关键数字完全一致。文字可以不同，**结构不许不同** —— 这是
   在无法逐字比对的前提下能拿到的最强一致性保证。

行为测试（图片校验/最终化/路径逃逸等）随实现放在 CLI 仓库：
private-skills/cli/pracmocli/internal/{images,contract,connector}。
"""

from dataclasses import dataclass
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"

FRONTMATTER_REQUIRED_COMMON = ("name", "description", "version", "author")


@dataclass(frozen=True)
class Region:
    skill: str
    lang: str  # zh | en
    brand: str
    env_flag: str
    api_host: str
    web_host: str
    counterpart: str
    # 本区域绝不允许出现的字符串（防止跨区串台）
    forbidden: tuple

    @property
    def path(self) -> Path:
        return SKILLS_DIR / self.skill

    def text(self, rel: str = "SKILL.md") -> str:
        return (self.path / rel).read_text(encoding="utf-8")


ZH_EXERCISE = "pracmo-add-exercise"
ZH_ACTION = "pracmo-add-action"
EN_EXERCISE = "pracmo-global-add-exercise"
EN_ACTION = "pracmo-global-add-action"

ZH_FORBIDDEN = ("pracmo.app", "--env global", "description_en:", "descriptionEn")
EN_FORBIDDEN = ("pracmo.com", "--env prod", "description_zh:", "练成")

REGIONS = (
    Region(ZH_EXERCISE, "zh", "练成", "--env prod", "apis.pracmo.com", "www.pracmo.com",
           EN_EXERCISE, ZH_FORBIDDEN),
    Region(EN_EXERCISE, "en", "Pracmo", "--env global", "apis.pracmo.app", "www.pracmo.app",
           ZH_EXERCISE, EN_FORBIDDEN),
    Region(ZH_ACTION, "zh", "练成", "--env prod", "apis.pracmo.com", "www.pracmo.com",
           EN_ACTION, ZH_FORBIDDEN),
    Region(EN_ACTION, "en", "Pracmo", "--env global", "apis.pracmo.app", "www.pracmo.app",
           ZH_ACTION, EN_FORBIDDEN),
)


def frontmatter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def frontmatter_field(front: str, field: str):
    m = re.search(r'(?m)^%s:\s*"?(.*?)"?\s*$' % re.escape(field), front)
    return m.group(1) if m else None


def all_docs(region: Region):
    """返回 (相对路径, 内容) 列表，覆盖 skill 目录下**所有**文本文件。

    刻意不只读 SKILL.md 与 references/：agents/openai.yaml 与 evals/evals.json
    也含 skill 名、区域域名与用户提问样例 —— 曾经就因为只检查 markdown，
    导致这两个文件被原样拷成中文版而没被发现。

    唯一的排除项是 .gitignore 里的本地产物（output/、__pycache__、.DS_Store）：
    它们不进仓库、CI 中也不存在，扫描它们只会让本地结果与 CI 不一致。
    """
    docs = []
    for path in sorted(region.path.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".json", ".yaml", ".yml", ".txt"}:
            continue
        if "__pycache__" in path.parts or path.name == ".DS_Store":
            continue
        # output/ 是本地运行草稿产物（.gitignore 已排除），不算对外交付的 skill 文档
        if path.relative_to(region.path).parts[0] == "output":
            continue
        docs.append((str(path.relative_to(region.path)), path.read_text(encoding="utf-8")))
    if not docs:
        raise AssertionError("skill %s has no readable documents" % region.skill)
    return docs


def commands_in(text: str):
    """抽取所有 pracmocli 调用的子命令路径，例如 'tracks list'、'images validate'。"""
    found = set()
    for m in re.finditer(r"pracmocli\s+(?:--env\s+\w+\s+)?([a-z-]+(?:\s+[a-z-]+)?)", text):
        parts = m.group(1).split()
        # 第二段若是位置参数（不是子命令）就丢掉
        if len(parts) == 2 and parts[1] in {
            "list", "create", "add", "compress", "validate", "finalize",
            "image-replace", "login", "status", "logout",
        }:
            found.add(" ".join(parts))
        else:
            found.add(parts[0])
    return found


class SkillContractTest(unittest.TestCase):
    """领域硬约束：无论哪个区域、哪种语言，这些规则都必须存在。"""

    def test_requires_existing_track_and_private_endpoint(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                text = r.text()
                self.assertIn("GET /open/v1/learning-tracks", text)
                self.assertIn("/exercises" if "exercise" in r.skill else "/actions", text)
                self.assertNotIn("/learning-tracks/import", text)
                self.assertNotIn("/learning-tracks/with-exercise", text)
                self.assertNotIn("/public-actions", text)

    def test_forbids_track_creation(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                text = r.text()
                if r.lang == "zh":
                    self.assertIn("不得创建甲程", text)
                else:
                    self.assertRegex(text, r"(?i)(never|must not|do not)\s+create\s+a\s+track")

    def test_has_grounded_image_review_gate(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                text = r.text()
                combined = "".join(c for _, c in all_docs(r))
                if r.lang == "zh":
                    self.assertIn("不得依赖模型参数记忆", combined)
                    self.assertIn("任何一项未通过都不得创建", combined)
                else:
                    # 不接受简化措辞：必须点明"参数记忆"这件事，而不是笼统的"不要凭空断言"
                    self.assertTrue(
                        re.search(r"(?i)(parametric memory|model parameter memory)", combined),
                        "%s 必须点明不得依赖模型参数记忆" % r.skill,
                    )
                    self.assertTrue(
                        re.search(r"(?i)(you MUST NOT create|do not create|never create)", combined),
                        "%s 必须写明任何一项未通过都不得创建" % r.skill,
                    )
                # 出处与整图生成要求：两种模式的标识符是同一套英文枚举，中英都必须出现
                for token in ("web_downloaded", "real_scene_generated"):
                    self.assertIn(token, combined)

    def test_option_level_explanation_contract(self):
        for r in REGIONS:
            if "exercise" not in r.skill:
                continue
            with self.subTest(skill=r.skill):
                combined = "".join(c for _, c in all_docs(r))
                self.assertIn("options[].explanation", combined)
                self.assertNotIn("questions[].explanation", combined)


class RegionIsolationTest(unittest.TestCase):
    """区域隔离：任何一份都不得把用户引到另一个区域的后端。"""

    def test_no_cross_region_strings(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                for rel, content in all_docs(r):
                    for bad in r.forbidden:
                        if bad in content:
                            line = next(
                                (ln for ln in content.splitlines() if bad in ln), ""
                            ).strip()
                            self.fail(
                                "%s（%s）的 %s 出现跨区字符串 %r：%s\n"
                                "两套账号不互通，走错后端只会得到一个难懂的鉴权失败。"
                                % (r.skill, r.lang, rel, bad, line[:160])
                            )

    def test_states_its_own_backend_and_app_name(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                text = r.text() + "".join(
                    c for p, c in all_docs(r) if p != "SKILL.md"
                )
                self.assertIn(r.api_host, text, "必须写清自己的后端域名")
                self.assertIn(r.env_flag, text, "命令必须显式带本区域的 --env 参数")
                self.assertIn(r.brand, text, "必须写清自己的 App 名称")
                self.assertIn(r.web_host, text, "必须指向本区域的账号页")

    def test_every_command_carries_the_region_flag(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                for rel, content in all_docs(r):
                    for m in re.finditer(r"(?m)^[ \t]*pracmocli\b[^\n]*", content):
                        line = m.group(0)
                        # help/version 不触达后端，不需要区域参数
                        if re.match(r"[ \t]*pracmocli\s+(help|version)\b", line):
                            continue
                        self.assertIn(
                            r.env_flag, line,
                            "命令缺少 %s：%s:%s" % (r.env_flag, rel, line.strip()),
                        )

    def test_frontmatter_is_monolingual(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                front = frontmatter(r.text())
                for field in FRONTMATTER_REQUIRED_COMMON:
                    self.assertIsNotNone(
                        frontmatter_field(front, field),
                        "%s frontmatter 缺字段 %s" % (r.skill, field),
                    )
                lang_field = "description_zh" if r.lang == "zh" else "description_en"
                other = "description_en" if r.lang == "zh" else "description_zh"
                self.assertIsNotNone(frontmatter_field(front, lang_field),
                                     "%s 缺 %s" % (r.skill, lang_field))
                self.assertIsNone(frontmatter_field(front, other),
                                  "%s 不应包含另一语言的 %s" % (r.skill, other))
                self.assertRegex(front, r"(?m)^display_name:")
                self.assertRegex(front, r"(?m)^category:")

    def test_no_legacy_script_layer_or_env_var(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                blob = "\n".join(c for _, c in all_docs(r))
                for forbidden in ("python3 ", "scripts/pracmo-open-api.sh",
                                  "scripts/validate_", "scripts/finalize_",
                                  "scripts/compress_", "PRACMO_APIKEY"):
                    self.assertNotIn(forbidden, blob,
                                     "%s 不得引用已退役的脚本层/旧环境变量：%r" % (r.skill, forbidden))


class DeliveryContractTest(unittest.TestCase):
    """交付格式：退出码表、命令速查、引用完整性。"""

    def test_exit_code_recovery_table(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                combined = r.text() + r.text("references/cli-commands.md")
                self.assertRegex(combined, r"(?i)(exit code|退出码)")
                for code in ("2", "4", "5", "6"):
                    self.assertRegex(combined, r"(?m)^\|\s*%s\s*\|" % code,
                                     "%s 退出码表缺第 %s 行" % (r.skill, code))

    def test_cli_commands_reference_covers_used_commands(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                ref = (r.path / "references" / "cli-commands.md")
                self.assertTrue(ref.is_file(), "%s 缺 references/cli-commands.md" % r.skill)
                body = ref.read_text(encoding="utf-8")
                for cmd in ("tracks list", "images compress", "images validate", "images finalize"):
                    self.assertIn(cmd, body, "%s 的命令速查缺 %r" % (r.skill, cmd))
                self.assertIn("auth status", body)
                self.assertIn("add", body)

    def test_every_referenced_file_exists(self):
        for r in REGIONS:
            with self.subTest(skill=r.skill):
                for _, content in all_docs(r):
                    for name in set(re.findall(r"references/([A-Za-z0-9._-]+)", content)):
                        self.assertTrue(
                            (r.path / "references" / name).is_file(),
                            "%s 引用了不存在的 references/%s" % (r.skill, name),
                        )


class CrossRegionParityTest(unittest.TestCase):
    """跨区域结构对等 —— 语言不同无法逐字比对，但结构必须一致。"""

    def _structure(self, region: Region):
        blob = "\n".join(c for _, c in all_docs(region))
        return {
            "headings": len(re.findall(r"(?m)^#{1,3} ", blob)),
            "table_rows": len(re.findall(r"(?m)^\|[^|]*\|", blob)),
            "code_fences": blob.count("```") // 2,
            "commands": commands_in(blob),
            "numbers": set(re.findall(r"\b(?:512|10|15|100|12|900|60|40|20|8|64)\b", blob)),
        }

    def test_counterparts_have_identical_structure(self):
        for r in REGIONS:
            if r.lang != "zh":
                continue
            other = next(x for x in REGIONS if x.skill == r.counterpart)
            with self.subTest(pair="%s ↔ %s" % (r.skill, other.skill)):
                a, b = self._structure(r), self._structure(other)
                self.assertEqual(a["headings"], b["headings"],
                                 "章节数不一致：%s=%d vs %s=%d" %
                                 (r.skill, a["headings"], other.skill, b["headings"]))
                self.assertEqual(a["table_rows"], b["table_rows"],
                                 "表格行数不一致：%s=%d vs %s=%d" %
                                 (r.skill, a["table_rows"], other.skill, b["table_rows"]))
                self.assertEqual(a["code_fences"], b["code_fences"],
                                 "代码块数不一致：%s=%d vs %s=%d" %
                                 (r.skill, a["code_fences"], other.skill, b["code_fences"]))
                self.assertEqual(a["commands"], b["commands"],
                                 "命令集合不一致：仅 %s 有 %s；仅 %s 有 %s" %
                                 (r.skill, sorted(a["commands"] - b["commands"]),
                                  other.skill, sorted(b["commands"] - a["commands"])))
                self.assertEqual(a["numbers"], b["numbers"],
                                 "关键数字不一致：仅 %s 有 %s；仅 %s 有 %s" %
                                 (r.skill, sorted(a["numbers"] - b["numbers"]),
                                  other.skill, sorted(b["numbers"] - a["numbers"])))


if __name__ == "__main__":
    unittest.main()
