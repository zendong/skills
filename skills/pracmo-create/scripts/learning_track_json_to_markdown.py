#!/usr/bin/env python3
"""Render a learning-track package as a human-readable review document."""

import argparse
import json
from pathlib import Path


def render(payload):
    track, path = payload["track"], payload["path"]
    lines = [f"# {track['title']}", "", track.get("description", ""), "", "## 核心目标", "", track["goalStatement"]]
    if track.get("goalReason"):
        lines += ["", f"**为什么做：** {track['goalReason']}"]
    lines += ["", "## 目标路径", ""]
    for index, state in enumerate(path["states"], 1):
        lines += [f"### {index}. {state['title']}", "", state["description"], ""]
        lines += [f"- {criterion['description']} (`{criterion['criterionId']}`)" for criterion in state["criteria"]]
        lines.append("")
    lines += ["## 初始练习", ""]
    if not payload.get("exercises"):
        lines += ["暂无；这是一个可继续规划的甲程骨架。", ""]
    for exercise in payload.get("exercises", []):
        lines += [f"### {exercise['title']}", "", exercise.get("userRequest", ""), ""]
        for index, question in enumerate(exercise["questions"], 1):
            lines += [f"{index}. {question['questionContent']}", ""]
            for option_index, option in enumerate(question.get("options", [])):
                mark = "✓" if option["isCorrect"] else " "
                lines.append(f"   - [{mark}] {chr(65 + option_index)}. {option['content']}")
            if question.get("explanation"):
                lines += ["", f"   解析：{question['explanation']}"]
            lines.append("")
    lines += ["## 初始行动", ""]
    if not payload.get("actions"):
        lines += ["暂无。", ""]
    for item in payload.get("actions", []):
        lines += [f"- **{item['title']}** · `{item['contentMode']}` · `{item['scheduleType']}` · {item['deadlineLocalTime']}"]
    lines += ["", "## 导入摘要", "", f"- Request ID：`{payload['clientRequestId']}`", f"- 阶段：{len(path['states'])}", f"- 练习：{len(payload.get('exercises', []))}", f"- 行动：{len(payload.get('actions', []))}"]
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(payload), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
