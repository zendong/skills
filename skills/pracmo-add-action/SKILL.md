---
name: pracmo-add-action
display_name: 练成行动
description: "在用户已有的练成甲程中创建行动，包括自行完成、小璞准备和带文字/图片 block 的分层跟练计划。用户说创建行动、每日任务、轻阅读、快问答、跟练计划、动作示范图或分阶段训练时使用。必须读取并选择 API Key 用户的存量甲程；不得创建甲程。跟练图片必须经过可靠来源取证、动作与安全审阅、账号内上传和 HTTPS 最终化。"
description_zh: "在用户已有的甲程中创建行动：自行完成、小璞准备的分层内容或带文字/图片 block 的逐一跟练，并支持图片取证、审阅与上传。"
category: productivity
version: 0.1.10
author: 练成（evertrain）
user-invocable: true
---

# Pracmo Add Action

在用户选定的存量甲程中创建行动。内容创建后归用户所有，后续如需公开可在公开内容流程中继续推进；这个 skill 不创建甲程，也不含公开行动投稿/审核操作。

开始前完整阅读 `references/action-json-contract.md`。涉及跟练图片、事实性动作规范、次数/时长或健康安全内容时，再完整阅读 `references/follow-image-grounding-and-review.md`。

## 强制前置：读取并选择甲程

调用 `GET /open/v1/learning-tracks?state=active&pageSize=100`（用 `pracmocli --env prod tracks list`）；`pracmocli` 安装：`npm install -g @pracmo/pracmo-cli`（无 Python/Pillow/oss2 依赖）。先确认登录：`pracmocli --env prod auth status`，或以环境变量 `PRACMO_API_KEY` 提供 Key。未登录时提示用户运行 `pracmocli --env prod auth login`（或到 `https://www.pracmo.com/app/api-key` 获取 Key）；不要让用户把 Key 发到聊天里。

```bash
pracmocli --env prod tracks list "甲程关键词"
```

只有一个明确匹配项时使用，并在创建前说明甲程名称。🔴 STOP：多个合理匹配项时列出标题和 `trackId` 请用户选择，不要猜，用户确认前不得继续。没有 active 甲程时停止并原样提示：

```text
没有找到可用的存量甲程。请先到练成手机端创建甲程，创建后告诉我，我就能读取到并继续添加行动。
```

不得创建甲程。用户要求新建甲程时也只提示手机端创建。

## 设计行动

- `self_directed`：用户自行完成；完成方式可为 `one_tap`、`text`、`rich_media`。
- `puki_generated`：小璞准备轻阅读或快问答；完成方式为 `one_tap`，提供完整 `generatedContentConfig`。
- `follow_along`：分层跟练；完成方式为 `one_tap`，提供 1–20 个可重复练阶、文字/图片 block 和可选检查点。

明确标题、最小可观察行为、频率、时区、日期、截止时间、完成标准、进阶条件和安全边界。不要生成账号、甲程归属、打卡记录、守甲关系、审核状态或公开分类字段。

无图片 `self_directed` 行动的最小完整请求（`follow_along` 在 `action` 内另加 `followPlan.levels`）：

```json
{
  "schemaVersion": "pracmo-track-action@v1",
  "clientRequestId": "action-20260919-daily-plank",
  "action": {
    "title": "睡前平板支撑",
    "scheduleType": "daily",
    "timezone": "Asia/Shanghai",
    "startDate": "2026-09-19",
    "deadlineLocalTime": "22:00",
    "completionMode": "one_tap",
    "contentMode": "self_directed"
  }
}
```

事实性动作规范、健康安全、次数、时长和专业关系必须来自用户材料或实际打开的可靠资料。优先官方指南、正式标准、专业组织、论文原文及一手说明；不得依赖模型参数记忆。搜索摘要只能定位资料，不能作为唯一证据。无法确认时删去该断言、降低为非事实表达，或向用户索取资料。

## 截止时间与提醒（硬要求）

`deadlineLocalTime` 决定这次行动当天几点到期，同时是 `defaultBeforeDeadlineMinutes` 提醒的锚点（提醒 = 从截止时间往前推 N 分钟）。**默认不得写 23:59**：它把完成推到一天最后一分钟，也让提醒落在深夜，等于鼓励睡前赶任务。

- 禁止 `23:59`，也禁止 `00:00–05:00`；取值统一用整点或半点，不用边界值。
- 默认不晚于 22:00；确属睡前型的行动最晚 22:30，并在行动描述里写明理由。
- 截止时间应略晚于该行动自然发生的时段，留出缓冲，但不要贴着入睡时间。
- 取值顺序：先看甲程的 `targetUserDescription` 与 `requirements` 判断服务对象的作息，再看行动本身属于哪一类，两者取更早的那个。
- 宽限优先用 `two_hours` 兜底，而不是把截止时间本身拖到深夜。
- 提醒时刻要明显早于截止时间，不要只在截止前几分钟提醒，也不要用满五个时刻。

### 按行动性质取值

| 行动性质 | 典型例子 | 建议截止时间 |
| --- | --- | --- |
| 晨间型 | 早起、晨练、当天计划 | 09:00 前后 |
| 日间型 | 散步、户外活动、家务 | 12:00–18:00 |
| 收尾型 | 下班复盘、今日清点 | 18:00–20:00 |
| 睡前型 | 拉伸、冥想、晚安记录 | 21:00–22:00 |
| 全天弹性型 | 记录一条发现、喝水 | 20:00 前后 |

### 按服务对象取值

| 服务对象 | 建议区间 |
| --- | --- |
| 银发族、退休人群 | 17:00–20:00，整体提前 |
| 上班族、通勤人群 | 19:00–21:30，不拖到睡前 |
| 学生、孩子 | 20:00–21:00，不影响睡眠 |
| 夜班、跨时区 | 按其真实作息取值并写明依据 |

`weekly_quota` 的截止时间落在配额周的周日（服务端把到期日设为周日，提醒也只在到期日触发），同样按上表取值，不要因为「一周一次」就写 23:59。

**创建前自检**：截止时间不是 23:59；不晚于 22:00（睡前型不超过 22:30）；与服务对象作息和行动性质一致；提醒早于截止；宽限用 `two_hours` 兜底。

## 行动产出与依据（硬要求）

行动不能只让人「想一想」或「留意一下」。本节与设计行动、安全门禁同级：任何一条不满足，都不得交付，也不得创建。

- **每次都要有产出**：一次行动必须留下可观察的结果——一条记录、一个数字、一段能说出口的结论，或一次前后对照。只让用户「留意」「回想」「放松心情」而不产生任何结果的行动，属于空洞内容。
- **写清当次完成标准**：最小可观察行为、完成标准与进阶条件都要写明，用户做完能说出自己完成了什么，而不是模糊的「有感觉了」。
- **小璞准备的内容要有知识密度**：生成指令必须要求每次内容包含一个可复述的数字、换算或机制，并写明安全边界、不编造出处、无法可靠表达时换题。
- **能长期做下去**：行动要可持续并有变化（主题轮换、数字对比、阶段递进），不是一次性任务；频率、时长、次数与动作规范来自用户材料或实际打开的可靠资料。
- **安全边界具体**：健康与运动类内容给一般信息、停止条件和就医提示，不做个体化处方；不制造焦虑，也不承诺疗效或结果。

### 事实依据台账

事实性断言（数字、换算、机制、机构结论、日期、人物原话、专业关系）必须逐条落到**实际打开过的来源**上，而不是模型印象。

- 每条断言登记：来源 URL、原文摘录、适用边界，并对应到行动的具体内容；台账随内容一起交付。
- 搜索摘要、转载、二手复述和模型参数记忆都不能作为唯一依据；搜索只用于定位来源，找到后必须实际打开。
- 找不到可靠来源时只有三条退路：删掉该断言、降低为非事实表达，或者向用户索取材料。不得用「研究表明」这类无法追溯的措辞蒙混。
- 时效性内容（价格、行情、政策、模型版本、工具清单、排名）默认不写；确需写入时以实际打开的一手页面为准，并写清核对日期。
- 交付前逐条自检：每次行动都有产出与完成标准；内容有可复述锚点；所有事实断言都在台账里有出处；没有无法取证却保留的断言。

## 跟练图片创作包

图片只在能说明姿态、方向、步骤、器材位置或对比时使用，不添加纯装饰图。用两个文件创作：

图片只允许网页原图下载或真实场景生成。生成图的整张完整成图必须由图片生成工具直接产出，默认禁止本地排版：不得用 Pillow、Canvas、SVG、HTML/CSS、截图拼贴、后期贴字、透视合成或代码绘图把动作、文字、数字、箭头、器材或背景排到图上。只允许不改变可见内容的压缩、格式转换、元数据清理和透明通道处理。出现错字、错数字、错误姿态、安全问题或不真实时，整图重新生成；只有用户明确要求本地排版或合成时才可例外并记录。

图片生成连续失败或长时间无进展时停止重试（同一图不得超过 3 次尝试），向用户报告进展并给出选项：更换来源模式、调整场景描述、或稍后重试。

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
pracmocli --env prod images compress \
  --manifest output/<slug>/action-images.json \
  -o output/<slug>/reviewed/action-images.json \
  output/<slug>/action.authoring.json
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

OCR 和视觉模型只能辅助，不能代替逐项比较。任何不确定、来源冲突、姿态歧义或安全问题都必须先修正并重新审阅。🛑 任何一项未通过都不得创建。

```bash
pracmocli --env prod images validate \
  --stage reviewed \
  --type action \
  --manifest output/<slug>/reviewed/action-images.json \
  output/<slug>/action.authoring.json
```

## 图片上传与最终化

reviewed 校验通过后运行：

```bash
pracmocli --env prod images finalize \
  --manifest output/<slug>/reviewed/action-images.json \
  --type action \
  -o output/<slug>/action.json \
  output/<slug>/action.authoring.json

pracmocli --env prod images validate --stage finalized --type action output/<slug>/action.json
```

最终化使用 `clientRequestId + assetId + reviewedSha256` 构造确定性 `practiceAssets` key，上传后重新下载比较哈希，再将 `asset://` 替换为 HTTPS `mediaUrl`。CLI 内置全部能力，无需 Python/Pillow/oss2 依赖，不得绕过最终化命令。

无 image block 的行动跳过压缩、审阅与最终化：直接写 `output/<slug>/action.json`（不经过 `action.authoring.json`），用同一命令校验通过后即可创建：

```bash
pracmocli --env prod images validate --stage finalized --type action output/<slug>/action.json
```

创建失败或超时后重用同一份 `action.json`；不要重新最终化、改变 URL 或请求 ID。`action-images.finalized.json` 是续传台账，不得发送给行动 API。

## 创建

🛑 创建前逐项确认：目标甲程来自本次会话刚读取的 active 列表、所有适用门禁已通过、用户已授权实际创建——任一不满足立即停止，不创建。

用户要求实际创建、目标甲程明确且所有适用门禁通过时：

```bash
pracmocli --env prod actions add <trackId> output/<slug>/action.json
```

这会调用 `POST /open/v1/learning-tracks/:trackId/actions`。`trackId` 必须来自当前 API Key 刚读取到的 active 甲程。本 skill 不含公开行动投稿/审核操作。

该接口创建的行动默认状态为「已暂停」：不会生成打卡实例、不会发出提醒，也不占启用行动额度。`clientRequestId` 幂等重试返回的是同一份已暂停行动，不要重复创建。

## 幂等与反馈

- 同一内容重试保持相同 `clientRequestId` 和最终 JSON；相同 ID 换内容会冲突。
- 🛑 用户只要求草稿时保存/展示草稿并停止，不上传、不调用创建接口。
- 成功后报告甲程、`trackId`、行动标题、`actionId`、模式和图片数，并说明行动默认「已暂停」；内容归用户所有、后续可自行推进公开。
- **创建完成后的固定提醒**：告知用户行动已在「<甲程名>」中创建但默认暂停，需要到练成 App「甲程详情 → 行动」，打开该行动并点击「开启」后才会开始打卡与提醒。若用户表示开启完成或要求重新创建，再继续后续操作。
- 甲程不存在、已结束或不属于当前用户时停止；不要自动改投其他甲程。

## 红线（绝不做）

- 创建甲程，或调用任何甲程创建/导入接口。
- 用模型参数记忆、搜索摘要或未实际打开的转载充当事实依据。
- 对生成图做本地排版/合成（用户明确要求时除外并记录）。
- 为通过校验虚填 `review` 字段，或跳过 compress → 审阅 → validate 流程。
- 绕过 `images finalize` 手工拼 URL；重试时更换 `clientRequestId` 或修改 JSON。
- 在门禁未通过或用户未授权时执行创建。

## 退出码与恢复动作

写操作默认**不自动重试**。提交前可用 `--dry-run` 只做本地结构校验、不发请求。

| 码 | 含义 | 恢复动作 |
|----|------|----------|
| 0 | 成功 | 解析 stdout JSON |
| 1 | 参数/用法错误 | 查看 `pracmocli help` 后修正命令；不要改 JSON 内容 |
| 2 | 未登录/凭证失效 | 引导用户 `pracmocli --env prod auth login`（或到 `https://www.pracmo.com/app/api-key` 取 Key） |
| 3 | 业务错误（后端 4xx 非冲突） | 按 stderr 错误信息处理；甲程越权或已结束时重新读取列表让用户重新确认 |
| 4 | 网络/超时 | **用相同 `clientRequestId` 与完全相同的 JSON 重试**，不得生成新 ID |
| 5 | 冲突（409 幂等冲突） | 内容未改 → 核对此前结果；内容已实质修改 → 生成新 `clientRequestId` |
| 6 | 本地门禁未过（校验失败） | 修图/改动作说明后**重新完整校验**；**不得创建** |

> 行动的图片流水线**必须带 `--type action`**。省略它会拿练习的校验器去校验行动 JSON，
> 表现为 `request top-level keys must be exactly schemaVersion, clientRequestId, exercise`。
> 另外请确认校验输出里的 `stage` 与 `type` 与预期一致——门禁放行错误阶段会造成不可逆后果。

命令速查见 `references/cli-commands.md`。
