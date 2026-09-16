---
name: pracmo-add-exercise
display_name: 练成出题
description: "在用户已有的练成甲程和指定练习册中创建一组练习（也支持创建练习册），以及为题干或选项制作、检索、校验并上传事实可靠的图片、图表和示意图。用户说练一下、把内容做成练习、给某个甲程或练习册出题、补练习、看图出题时使用。必须先读取 API Key 所属用户的存量甲程；不得创建甲程。没有存量甲程时，提示用户先到练成手机端创建甲程。"
description_zh: "把对话、资料或目标整理成一组练习，加入用户已有的甲程与指定练习册；支持为题干/选项制作、检索、校验并上传事实可靠的图片。"
category: productivity
version: 0.1.10
author: 练成（evertrain）
user-invocable: true
---

# Pracmo Add Exercise

把对话、资料或目标整理成一组完整题目，并添加到用户选定的存量甲程和练习册。内容创建后归用户所有，后续如需公开可在公开内容流程中继续推进。这个 skill 可以在选定甲程内创建练习册，但不创建甲程。

开始前必须完整阅读：

- `references/exercise-json-contract.md`
- 涉及图片、图表、事实性数字或需要外部资料时，再完整阅读 `references/image-grounding-and-review.md`

## 强制前置步骤：确认甲程 + 练习册

写题前先确认登录：运行 `pracmocli --env prod auth status`，或以环境变量 `PRACMO_API_KEY` 提供 Key。未登录时提示用户运行 `pracmocli --env prod auth login`（或到 `https://www.pracmo.com/app/api-key` 获取 Key）；不要让用户把 Key 发到聊天里。`pracmocli` 安装/升级到最新版：`npm install -g @pracmo/pracmo-cli@latest --registry=https://registry.npmjs.org`（无 Python/Pillow/oss2 依赖）。

排障前置：
- 跨环境（prod/pre/global）API Key **不通用**：`invalid API key` 时先 `pracmocli --env prod doctor` 看 `baseUrl`。

调用 `GET /open/v1/learning-tracks?state=active&pageSize=100`；用户给了名称时同时传 `keyword`。也可使用：

```bash
pracmocli --env prod tracks list "甲程关键词"
```

甲程选择规则：

1. 只有一个明确匹配项时使用它，并在创建前告诉用户甲程名称。
2. 有多个合理匹配项时列出标题和 `trackId`，让用户选择；不要猜。
3. 没有 active 甲程，或搜索结果为空且不存在其他合理候选时，停止并原样提示：

```text
没有找到可用的存量甲程。请先到练成手机端创建甲程，创建后告诉我，我就能读取到并继续添加练习。
```

不得创建甲程，也不得调用任何 import、`with-exercise` 或甲程创建接口。用户明确要求“新建甲程”时同样使用上面的手机端提示。

选定甲程后必须调用 `GET /open/v1/learning-tracks/:trackId/exercise-collections`，或使用：

```bash
pracmocli --env prod collections list <trackId>
```

练习册选择规则：

1. 只依据响应中的 `isDefault` 识别系统默认册，不按“未分类”等显示名称猜测。
2. 如果列表里只有系统默认册，可以自动选中它；在创建前仍要把甲程与练习册名称一起告诉用户。
3. 只要存在任意命名练习册，就必须列出候选并让用户明确选择，不要根据练习主题自行推断。默认册仍是可选项。
4. 重名练习册使用描述和 `collectionId` 消歧；最终只使用 API 返回的真实 ID，不得根据名称构造 ID。
5. 列表正在加载、加载失败、为空或选择不明确时停止，不得通过省略 `collectionId` 静默回退默认册。

用户也可以选择在已确认的甲程内新建练习册。先确认一条完整目的地，例如：

```text
甲程 + 练习册：通用 AI 使用入门与进阶 / AI 协作闯关（将新建）
```

这一次确认同时授权选择甲程、选择或创建练习册以及随后提交已审阅的练习，不需要为创建练习册单独二次确认。若用户只要求草案、设计或预览，不得调用任何写接口；新练习册也等到用户授权实际创建时再创建。

新建练习册请求包含名称、可选描述和稳定的 `clientRequestId`：

```json
{
  "name": "AI 协作闯关",
  "description": "从提问到决策的进阶练习",
  "clientRequestId": "collection-20260827-ai-collab-v1"
}
```

实际创建时调用 `POST /open/v1/learning-tracks/:trackId/exercise-collections`，或使用：

```bash
pracmocli --env prod validate collection output/<slug>/collection.json   # 提交前先校验
pracmocli --env prod collections create <trackId> output/<slug>/collection.json
```

以创建响应中的 `collectionId` 作为后续练习目的地。网络超时或结果未知时，以同一个 `clientRequestId` 和完全相同的 JSON 重试；用户修改名称或描述后，这是新意图，必须生成新的 ID。

## 资料取证与出题

- 生成 3–100 道完整可作答题目；默认 10–15 道，除非用户指定。
- 支持单选、多选、判断、简答；每题包含 1–4 的 Bloom 层级、知识点和可测命题，每个选项包含答案标记和针对该选项的解析。
- 先读用户给出的材料。事实性内容不足时，主动检索并实际打开高质量来源；优先一手资料、官方文档、标准、原始数据和同行评审论文。
- 不得依赖模型参数记忆来断言事实、数字、原话、时效状态或专业关系。搜索摘要只能用于定位来源，不能作为唯一证据。
- 题干、答案、逐选项解析以及图片中的事实都必须能追溯到实际读取的材料；无法找到可靠依据时删去该命题、改成不带事实断言的题，或向用户索取材料。
- 题干与逐选项解析须面向 App 用户自包含，不能依赖 Agent 上下文或本地路径。
- 用户只要求“先看看”时，先输出或保存草稿并停止，不调用写接口。

## 选项级解析硬合同

解析只写在 `options[].explanation`，题目对象不得包含解析字段。每个 option 都必须有非空解析，包括错误选项；解析要直接说明这个选项为什么成立或不成立，不能只复述选项、只给正确项写解析，或用一段通用文字复制到所有选项。

- 单选、判断：恰好一个 option 的 `isCorrect` 为 `true`，每个 option 分别解释正确或错误的依据。
- 多选：至少两个 option 的 `isCorrect` 为 `true`，每个 option 分别解释为什么应选或不应选。
- 简答：`options` 中有且只有一个参考答案 option，`content` 是可判定的参考答案，`isCorrect` 固定为 `true`，`explanation` 写评分要点、成立边界和常见遗漏。

```json
{
  "questionType": "single_choice",
  "questionContent": "哪一种处理更合适？",
  "options": [
    {
      "content": "先核实关键信息再行动",
      "isCorrect": true,
      "explanation": "该选项先验证事实，能降低基于错误前提行动的风险。"
    },
    {
      "content": "立即按第一印象行动",
      "isCorrect": false,
      "explanation": "该选项跳过事实核验，第一印象不足以支持当前决策。"
    }
  ]
}
```

请求基础格式：

```json
{
  "schemaVersion": "pracmo-track-exercise@v1",
  "clientRequestId": "exercise-20260823-stable-id",
  "exercise": {
    "title": "练习标题",
    "collectionId": "collection_xxx",
    "userRequest": "练习目标",
    "difficultyLevel": 2,
    "questions": []
  }
}
```

创建接口暂不接受 `accessMode`、`createShare`，请求中不要携带；内容后续如需公开，另行走公开内容流程。

## 图片创作包

图片不是装饰。只有当它承载观察、比较、空间关系、流程、数据读取或辨认任务时才添加；纯装饰图应省略。

图片还必须具有可信的现实依据，只允许两种来源模式：

- `web_downloaded`：从实际打开的网页下载，登记原始 URL、资源 ID、许可和下载文件 SHA-256。
- `real_scene_generated`：按照真实场景生成，登记生成方法和场景依据。整张完整成图必须由图片生成工具直接产出。

生成图默认禁止本地排版：不得用 Pillow、Canvas、SVG、HTML/CSS、截图拼贴、后期贴字、透视合成或任何其它代码把文字、数字、UI、人物、背景或图形排到生成图上。只允许不改变可见内容的压缩、格式转换、元数据清理和透明通道处理。图片中的文字、数字、关系、姿态或真实性不合格时，整图重新生成；只有用户明确要求本地排版或合成时才能例外，并在 manifest 与交付说明中记录。

禁止用扁平卡片、占位框、低保真线框图冒充真实场景。手机画面应使用中性手机界面，不出现厂商 logo、型号、刘海、灵动岛、摄像头孔、实体按键或可识别的第三方 App 品牌。无法同时做到真实、清楚、可验证时，宁可不使用图片。

在最终上传前，用两个文件创作：

- `exercise.authoring.json`：保持最终 API 结构，在题干或选项 Markdown 中用 `asset://<assetId>` 临时占位。
- `exercise-images.json`：按 `pracmo-exercise-images@v1` 记录来源、逐条事实、预期可见文字、逻辑关系、使用位置、许可和严格审阅结果。
  每个 asset 还需 `sourceType`（与 resources 同一套取值）；`web_downloaded` 另需顶层 `sourceUrl` 与 `resourceId`（指向已登记的该图片来源资源）。缺字段会在 `images validate` 阶段被拒，先补齐再跑门禁。

示例：

```markdown
观察图示：![注意力缓存流程](asset://kv-cache-flow)
```

先把原图放入 `source-assets/`，再压缩到独立审阅目录：

```bash
pracmocli --env prod images compress \
  --manifest output/<slug>/exercise-images.json \
  -o output/<slug>/reviewed/exercise-images.json \
  output/<slug>/exercise.authoring.json
```

压缩会删除旧的 `review`（压缩后必须针对实际文件重新审阅）。CLI 内置全部能力，无需 Python/Pillow/oss2 依赖。

> 命令中的 flag 都写在位置参数**之前**。CLI 也兼容另一种顺序，但这一形式最不容易出错，请照抄。

## 图片正确性硬门禁

对 `reviewed/assets/` 中每张实际图片逐像素查看，逐项与证据清单和来源比较。OCR、程序检查和视觉模型只能辅助，不能替代完整人工式复核。至少确认：

1. 所有标题、标签、正文、符号、拼写和语言都准确、无乱码、无截断。
2. 所有数字、单位、比例、坐标轴、图例、日期、小数点和正负号与来源一致。
3. 箭头方向、因果、顺序、包含关系、空间位置、颜色映射和流程分支逻辑正确。
4. 图片、题干、选项、正确答案和逐选项解析互相一致；遮住答案后独立作答一次，正确答案唯一或符合题型定义。
5. 图片不直接泄露答案，干扰项仍合理，手机端缩放后文字可读，关键内容不依赖难以区分的颜色。
6. 检索图或改绘图的来源、许可和事实声明完整；事实图必须逐条引用资源 ID。
7. 场景的布局、光线、透视、设备操作和界面密度符合现实，不是示意卡片伪装成截图。
8. 手机界面保持设备中立；姓名、手机号、账号、订单号、地址、链接、二维码、银行卡和可识别品牌均不存在，或是明确登记且不可路由的虚构值。
9. 图片反映客观知识时，逐项核对数字、文字、状态和逻辑；任何无法从来源确认的内容都要删除或撤图。

将每项真实结果写入 manifest 的 `review`。有任何不确定、看不清、来源冲突或逻辑歧义时，修图后从头复核。任何一项未通过都不得创建。

复核后运行硬校验：

```bash
pracmocli --env prod images validate \
  --stage reviewed \
  --manifest output/<slug>/reviewed/exercise-images.json \
  output/<slug>/exercise.authoring.json
```

## 上传与最终化

只有 reviewed 校验通过后才能上传。下面的命令会经 CLI 使用当前账号的 `practiceAssets` 前缀 OSS 直传、重新下载并校验上传内容哈希，再把所有 `asset://` 替换成 HTTPS URL；内部证据清单不会进入 API 请求。不得绕过最终化命令手工拼 URL：

```bash
pracmocli --env prod images finalize \
  --manifest output/<slug>/reviewed/exercise-images.json \
  -o output/<slug>/exercise.json \
  output/<slug>/exercise.authoring.json

pracmocli --env prod images validate --stage finalized output/<slug>/exercise.json
```

最终 JSON 不得含本地路径、`asset://`、`file://`、base64 图片或不安全 URL。图片只允许 HTTPS Markdown URL。

## 创建

用户要求实际创建、目标甲程和练习册都明确且所有适用门禁通过时：

```bash
pracmocli --env prod exercises add <trackId> output/<slug>/exercise.json
```

这会调用 `POST /open/v1/learning-tracks/:trackId/exercises`。`trackId` 和 `exercise.collectionId` 都只能来自刚读取或刚创建的 API 响应，不可臆造或从别人的分享内容复制。无图片时也应以 `--stage finalized` 校验最终请求。

成功响应必须包含实际 `collection` 摘要。核对其中的 `collectionId` 与目标一致；如果练习册在确认后已删除、停用、越权或不属于该甲程，重新读取列表并让用户重新确认，不得自动切换到默认册或其他同名册。

## 原位替换既有题目图片

只替换既有题目的图片时，不得重新创建练习或用全量同步接口覆盖题目。先保存更新前快照，再为每张图片准备：

```json
{
  "schemaVersion": "pracmo-question-image-replace@v1",
  "clientRequestId": "replace-image-stable-id",
  "expectedOldUrl": "https://.../material/<accountId>/practice-assets/old.png",
  "newUrl": "https://.../material/<accountId>/practice-assets/new.png"
}
```

使用 `pracmocli --env prod exercises image-replace <trackId> <exerciseId> <questionId> <json-file>`（提交前可先 `pracmocli --env prod validate replace-image <json-file>`）。服务端只允许同一可信 OSS host、当前账户的 `practiceAssets` 前缀，并以旧 URL 恰好出现一次作为乐观锁；只修改指定题目的图片 URL并递增练习版本，不重建题目或选项。同一请求重试保持相同 ID 和 JSON；回滚使用新的稳定 ID 反向替换。

多张图片逐项维护台账并回读。必须确认 exerciseId、questionId、optionId、题型、题干非图片文字、选项、正确答案、逐选项解析、顺序、计划和概念关联均未改变。旧图片需保留，以兼容进行中 play 的冻结投影。

## 幂等与反馈

- 同一份内容重试必须保持相同 `clientRequestId` 和 JSON。
- 相同 ID 换内容会返回冲突；内容实质修改后生成新 ID。
- 超时后先用相同请求重试，不要换 ID 制造重复练习。写命令默认 HTTP 超时 120s（`PRACMO_HTTP_TIMEOUT_SECONDS`），`exercises add` 实测可能 1–5 分钟，**建议提交循环里设 `PRACMO_HTTP_TIMEOUT_SECONDS=300`**；退出码 4 时后端可能已建好，重试命中幂等在响应里能看到 **`reusedExisting: true`** 并返回同一 `exerciseId`。
- 成功后报告甲程标题、`trackId`、练习册名称、`collectionId`、练习标题、`exerciseId`、题目数和图片数，并说明内容归用户所有、后续可自行推进公开。
- 甲程不存在、已结束或不属于 API Key 用户时停止；不要自动换到其他甲程。

## 退出码与恢复动作

写操作默认**不自动重试**。提交前可用 `--dry-run` 只做本地结构校验、不发请求。

| 码 | 含义 | 恢复动作 |
|----|------|----------|
| 0 | 成功 | 解析 stdout JSON |
| 1 | 参数/用法错误 | 查看 `pracmocli help` 后修正命令；不要改 JSON 内容 |
| 2 | 未登录/凭证失效 | 引导用户 `pracmocli --env prod auth login`（或到 `https://www.pracmo.com/app/api-key` 取 Key）；不要让用户把 Key 发到聊天里 |
| 3 | 业务错误（后端 4xx 非冲突） | 按 stderr 错误信息处理；甲程/练习册越权或已删除时重新读取列表让用户重新确认 |
| 4 | 网络/超时 | **用相同 `clientRequestId` 与完全相同的 JSON 重试**，不得生成新 ID |
| 5 | 冲突（409 幂等冲突） | 内容未改 → 核对此前结果；内容已实质修改 → 生成新 `clientRequestId` |
| 6 | 本地门禁未过（校验失败） | 修图/改题干后**重新完整校验**；**不得创建** |

> `images validate` 的输出里带 `stage` 字段。**若 `stage` 与你要的阶段不一致，说明参数没被正确接受**——放行带 `asset://` 的请求会造成不可逆后果，必须停下来检查命令。

## 版本要求

请使用**最新版** CLI（历史版本的已知问题均已修复，以最新版为准）：

```bash
npm install -g @pracmo/pracmo-cli@latest --registry=https://registry.npmjs.org
```

命令与退出码速查见 `references/cli-commands.md`；回读审计、跨环境迁移既有练习册、公开内容与源包的关系见 `references/read-back-and-migration.md`。
