#!/usr/bin/env python3
"""Deterministically export a Public Action JSON payload as review Markdown."""

import argparse
import importlib.util
import json
from pathlib import Path


CATEGORY_LABELS = {
    "habit": "习惯养成", "reading": "阅读", "fitness": "健康运动", "skill": "技能",
    "study": "学习备考", "language": "语言学习", "writing": "写作表达",
    "creative": "创作兴趣", "work": "工作成长", "mind": "心智修炼", "other": "其他",
}
SCHEDULE_LABELS = {"daily": "每日", "weekdays": "工作日", "weekly_quota": "每周定额", "once": "一次"}
MODE_LABELS = {"self_directed": "自行完成", "puki_generated": "小璞准备", "follow_along": "跟练计划"}
COMPLETION_LABELS = {"one_tap": "一键完成", "text": "文字记录", "rich_media": "图文记录"}
QUESTION_TYPE_LABELS = {
    "auto": "自动选择", "single_choice": "单选题", "multiple_choice": "多选题",
    "true_false": "判断题", "short_answer": "简答题", "mixed": "混合题型",
}


def load_validator(script_dir: Path):
    path = script_dir / "validate_public_action_json.py"
    spec = importlib.util.spec_from_file_location("pracmo_public_action_validator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def render(payload: dict) -> str:
    catalog = payload["catalog"]
    template = payload["template"]
    lines = [
        f"# {template['title']}",
        "",
        template.get("description", ""),
        "",
        "## 行动信息",
        "",
        f"- 分类：{CATEGORY_LABELS.get(catalog['category'], catalog['category'])}",
        f"- 标签：{'、'.join(catalog.get('tags', [])) or '无'}",
        f"- 频率：{SCHEDULE_LABELS.get(template['scheduleType'], template['scheduleType'])}",
        f"- 内容类型：{MODE_LABELS.get(template['contentMode'], template['contentMode'])}",
        f"- 完成方式：{COMPLETION_LABELS.get(template['completionMode'], template['completionMode'])}",
        "",
    ]
    cover_url = catalog.get("coverImage", {}).get("url")
    if cover_url:
        lines.extend([f"![{catalog['coverImage']['alt']}]({cover_url})", ""])
    mode = template["contentMode"]
    if mode == "self_directed":
        lines.extend(["## 执行说明", "", template.get("description") or "按行动说明自行完成。", ""])
        lines.extend([f"<!-- source: {payload['schemaVersion']} · clientRequestId: {payload['clientRequestId']} -->", ""])
        return "\n".join(lines)

    if mode == "puki_generated":
        generated = template["generatedContentConfig"]
        type_label = "轻阅读" if generated["type"] == "reading" else "快问答"
        lines.extend([f"## 小璞准备 · {type_label}", "", "### 内容要求", "", generated["instruction"], ""])
        if generated["type"] == "quick_qa":
            question_type = generated["quickQa"]["questionType"]
            lines.extend([f"- 题型：{QUESTION_TYPE_LABELS.get(question_type, question_type)}", ""])
        lines.extend([f"<!-- source: {payload['schemaVersion']} · clientRequestId: {payload['clientRequestId']} -->", ""])
        return "\n".join(lines)

    plan = template["followPlan"]
    estimated = sum(int(level.get("estMinutes", 0)) for level in plan["levels"]) // max(len(plan["levels"]), 1)
    lines.extend([f"- 每次预计：{estimated} 分钟", "", "## 跟练计划", ""])
    for index, level in enumerate(plan["levels"], start=1):
        lines.extend([f"### 练阶 {index}：{level['title']}", ""])
        if level.get("description"):
            lines.extend([level["description"], ""])
        lines.append(f"- 目标次数：{level.get('targetSessions', 1)}")
        if level.get("estMinutes"):
            lines.append(f"- 预计用时：{level['estMinutes']} 分钟")
        if level.get("promotionCriterion"):
            lines.append(f"- 进阶标准：{level['promotionCriterion']}")
        lines.append("")
        for block in level["contentBlocks"]:
            if block["blockType"] == "text":
                lines.extend([block["textContent"], ""])
            elif block.get("mediaUrl"):
                caption = block.get("caption") or block.get("assetId") or "跟练图片"
                lines.extend([f"![{caption}]({block['mediaUrl']})", ""])
    lines.extend(["## 成就节点", "", "| 练阶 | 节点 | 说明 | 关键节点 |", "| --- | --- | --- | --- |"])
    for checkpoint in plan.get("checkpoints", []):
        description = checkpoint.get("description", "").replace("|", "\\|")
        title = checkpoint["title"].replace("|", "\\|")
        lines.append(f"| {checkpoint['levelIndex'] + 1} | {title} | {description} | {'是' if checkpoint['isKey'] else '否'} |")
    lines.extend(["", f"<!-- source: {payload['schemaVersion']} · clientRequestId: {payload['clientRequestId']} -->", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    validator = load_validator(Path(__file__).resolve().parent)
    validator.validate(payload, base_dir=args.input.parent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
