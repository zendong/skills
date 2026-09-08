---
name: pracmo-add-action
description: "在用户已有的多练甲程中创建私人行动，包括自行完成、小璞准备和带文字/图片 block 的分层跟练计划。用户说创建行动、每日任务、轻阅读、快问答、跟练计划、动作示范图或分阶段训练时使用。必须读取并选择 API Key 用户的存量甲程；不得创建甲程或公开行动。跟练图片必须经过可靠来源取证、动作与安全审阅、私人上传和 HTTPS 最终化。"
---

# Pracmo Add Action

在用户选定的存量甲程中创建私人行动。这个 skill 不创建甲程，不调用公开行动投稿或审核接口，也不生成公开模板。

开始前完整阅读 `references/action-json-contract.md`。涉及跟练图片、事实性动作规范、次数/时长或健康安全内容时，再完整阅读 `references/follow-image-grounding-and-review.md`。

## 强制前置：读取并选择甲程

检查 `PRACMO_APIKEY`，不要让用户把 Key 发到聊天里。调用 `GET /open/v1/learning-tracks?state=active&pageSize=100`（用 `pracmocli tracks list`）；`pracmocli` 安装：`npm install -g @pracmo/pracmo-cli`（无 Python/Pillow/oss2 依赖）。先确认登录：`pracmocli auth status` 或以 `PRACMO_API_KEY`/`PRACMO_APIKEY` 提供 Key，不要让用户把 Key 发到聊天里。

```bash
pracmocli tracks list "甲程关键词"
```

只有一个明确匹配项时使用，并在创建前说明甲程名称。多个合理匹配项时列出标题和 `trackId` 请用户选择，不要猜。没有 active 甲程时停止并原样提示：

```text
没有找到可用的存量甲程。请先到多练手机端创建甲程，创建后告诉我，我就能读取到并继续添加行动。
```

不得创建甲程。用户要求新建甲程时也只提示手机端创建。

## 设计行动

- `self_directed`：用户自行完成；完成方式可为 `one_tap`、`text`、`rich_media`。
- `puki_generated`：小璞准备轻阅读或快问答；完成方式为 `one_tap`，提供完整 `generatedContentConfig`。
- `follow_along`：分层跟练；完成方式为 `one_tap`，提供 1–20 个可重复练阶、文字/图片 block 和可选检查点。

明确标题、最小可观察行为、频率、时区、日期、截止时间、完成标准、进阶条件和安全边界。不要生成账号、甲程归属、打卡记录、守甲关系、审核状态或公开分类字段。

事实性动作规范、健康安全、次数、时长和专业关系必须来自用户材料或实际打开的可靠资料。优先官方指南、正式标准、专业组织、论文原文及一手说明；不得依赖模型参数记忆。搜索摘要只能定位资料，不能作为唯一证据。无法确认时删去该断言、降低为非事实表达，或向用户索取资料。

## 跟练图片创作包

图片只在能说明姿态、方向、步骤、器材位置或对比时使用，不添加纯装饰图。用两个文件创作：

图片只允许网页原图下载或真实场景生成。生成图的整张完整成图必须由图片生成工具直接产出，默认禁止本地排版：不得用 Pillow、Canvas、SVG、HTML/CSS、截图拼贴、后期贴字、透视合成或代码绘图把动作、文字、数字、箭头、器材或背景排到图上。只允许不改变可见内容的压缩、格式转换、元数据清理和透明通道处理。出现错字、错数字、错误姿态、安全问题或不真实时，整图重新生成；只有用户明确要求本地排版或合成时才可例外并记录。

- `action.authoring.json`：保持最终 API 结构，image block 临时使用 `asset://<assetId>`。
- `action-images.json`：使用 `pracmo-action-images@v1`，记录来源、事实、精确文字/数字、动作关系、block 位置、许可和审阅。

```json
{
  "blockType": "image",
  "mediaUrl": "asset://wall-pushup-start",
  "caption": "墙壁俯卧撑起始姿势"
}
```

先压缩到独立审阅目录：

```bash
pracmocli images compress output/<slug>/action.authoring.json \
  --manifest output/<slug>/action-images.json \
  -o output/<slug>/reviewed/action-images.json
```

压缩会清除旧 `review`。必须打开 `reviewed/assets/` 中的实际文件重新检查，并把实际 SHA-256 写入 `review.reviewedSha256`。

## 动作与安全硬门禁

逐图与来源、caption、文字 block、练阶目标和进阶条件比较：

1. 逐字核对图片文字、标签、符号、数字、单位、次数和时长。
2. 核对身体/器材位置、关节角度、支撑点、运动方向、先后顺序和动作范围。
3. 图片与 caption、练阶说明、目标训练量和晋级标准必须一致。
4. 核对热身、呼吸、停止条件、禁忌和风险提示；不得把高风险动作表现为无条件适用。
5. 检查裁切、镜像、箭头或高亮是否造成误导，手机端缩放后是否仍清楚。
6. 来源与许可完整；事实图中的 claims、数值和关系均可追溯。

OCR 和视觉模型只能辅助，不能代替逐项比较。任何不确定、来源冲突、姿态歧义或安全问题都必须先修正并重新审阅。任何一项未通过都不得创建。

```bash
pracmocli images validate output/<slug>/action.authoring.json \
  --manifest output/<slug>/reviewed/action-images.json \
  --stage reviewed
```

## 私人上传与最终化

reviewed 校验通过后运行：

```bash
pracmocli images finalize output/<slug>/action.authoring.json \
  --manifest output/<slug>/reviewed/action-images.json \
  -o output/<slug>/action.json

pracmocli images validate output/<slug>/action.json --stage finalized
```

最终化使用 `clientRequestId + assetId + reviewedSha256` 构造确定性私人 `practiceAssets` key，上传后重新下载比较哈希，再将 `asset://` 替换为 HTTPS `mediaUrl`。CLI 内置全部能力，无需 Python/Pillow/oss2 依赖，不得绕过最终化命令。

创建失败或超时后重用同一份 `action.json`；不要重新最终化、改变 URL 或请求 ID。`action-images.finalized.json` 是续传台账，不得发送给行动 API。

## 创建

用户要求实际创建、目标甲程明确且所有适用门禁通过时：

```bash
pracmocli actions add <trackId> output/<slug>/action.json
```

这会调用 `POST /open/v1/learning-tracks/:trackId/actions`。`trackId` 必须来自当前 API Key 刚读取到的 active 甲程。严禁调用公开行动投稿接口。

## 幂等与反馈

- 同一内容重试保持相同 `clientRequestId` 和最终 JSON；相同 ID 换内容会冲突。
- 用户只要求草稿时保存/展示草稿并停止，不上传、不调用创建接口。
- 成功后报告甲程、`trackId`、行动标题、`actionId`、模式和图片数，并明确这是私人行动。
- 甲程不存在、已结束或不属于当前用户时停止；不要自动改投其他甲程。
