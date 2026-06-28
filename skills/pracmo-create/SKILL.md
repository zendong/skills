---
name: pracmo-create
description: "当用户说“练一下”“把这段内容做成练习”“围绕这个建个甲程练一下”“帮我生成一组题”“根据这段内容出题”“基于资料创建甲程”“创建甲程和第一个练习”等练习/甲程创建请求时，必须使用这个 skill。只处理甲程+练习。流程：先检查 `PRACMO_APIKEY`，基于对话或资料提炼 concepts，查询已有甲程并让用户选择复用或新建；需要新建甲程时先询问用户是否有合适标题，用户不提供再自动生成标题与适配说明；复用前读取已有 concepts 和练习队列，生成完整题目并通过开放 API 创建；当甲程归属、标题选择、练习目标、题量题型和题目内容已经明确时，可以直接创建，创建后提示用户在 App 打开或用共享链接分享。"
---

# Pracmo Create

## 用途

本 skill 只用于把当前对话、资料、Markdown、术语清单或学习目标创建成：

- 一个新甲程 + 首个完整练习
- 或追加到已有甲程队尾的一组完整练习

触发表达包括：

- “练一下”
- “把这个做成练习”
- “围绕这个建个甲程练一下”
- “基于这段资料创建甲程”
- “帮我生成一组题”
- “根据这段内容出题”
- “创建甲程和第一个练习”

非甲程练习创建请求不要进入本流程；本 skill 只负责甲程练习创建。

练习类请求不支持孤立练习。即使用户说“只要练习，不要甲程”，也必须解释：现在练习会归属到甲程里，可以新建一个甲程或加入已有甲程；不得调用旧的孤立练习接口。

## 先做认证检查

在任何内容整理、出题、列出甲程或接口调用前，先检查当前运行环境是否可读取 `PRACMO_APIKEY`。

如果没有检测到 `PRACMO_APIKEY`，必须立刻停止，不要继续整理草案，也不要假装已经创建成功。直接提示用户：

```text
未检测到 PRACMO_APIKEY，暂时不能创建甲程练习。

请先访问 https://www.zendong.com.cn/app/api-key 获取你的 API Key，
然后在本地环境中设置：

export PRACMO_APIKEY="你的_API_Key"

设置完成后，再回来对我说“练一下”或“确认创建”。
```

不要要求用户把 API Key 贴到聊天里。

CHECKPOINT · STOP：缺少 `PRACMO_APIKEY` 时到此结束。不要继续提炼 concepts、生成题目、查询甲程或输出创建草案。

## 用户可见文案

对用户说话时用自然中文，不要直接暴露内部字段名。

- `trackTitle` -> “甲程标题”
- `trackDescription` -> “甲程说明”
- `existingTrackId` / `trackId` -> “已有甲程”
- `exerciseTitle` -> “练习标题”
- `userRequest` / `exerciseUserRequest` -> “练习目标”
- `questionCount` / `targetCount` -> “题量”
- `shareUrl` / `shortShareUrl` -> “分享链接”
- `concepts` / `questions[].concept` -> “知识点”

内部执行仍使用真实字段名、真实请求结构和真实接口地址。

## API 调用入口

所有开放 API 调用都通过 `scripts/pracmo-open-api.sh`、`scripts/pracmo-cache.sh` 和 `scripts/pracmo-oss-upload.sh` 完成。不要在执行流程里手写 host、接口地址或 HTTP 方法；脚本已经内置正式开放 API 入口。

## 总流程

```text
用户提出练习/甲程创建请求
  -> 检查 PRACMO_APIKEY
  -> 判断当前上下文是否足够
  -> 不足时只追问“要围绕什么主题或资料创建甲程练习”
  -> 如有文件/URL/文本来源，先用 scripts/pracmo-cache.sh 生成 source fingerprint，并查本地 source mapping
  -> 基于对话或资料提炼 concepts，形成甲程+首练习草案
  -> 若本地缓存命中 trackId，先用脚本查询 timeline 或甲程列表验证该甲程仍存在
  -> 用 scripts/pracmo-open-api.sh 查询已有甲程
  -> 若有强/中匹配：让用户选择复用某个已有甲程，或仍创建新甲程
  -> 若完全无匹配：准备创建新甲程
  -> 若需要新建甲程且用户未提供标题：先询问用户是否有合适甲程标题
  -> 若用户不提供标题或授权 Agent 决定：结合内容自动生成甲程标题，并让甲程说明适配标题导向
  -> 若用户指定/选择复用已有甲程：先查该甲程练习时间线，了解当前练习队列，不因为存在未完成练习而停止
  -> 若用户指定/选择复用已有甲程：再查该甲程已关联 concepts，作为生成题目的 concept 约束
  -> 若甲程归属、练习目标、题量题型仍不明确：展示元信息草案并等待用户确认
  -> 若待确认内容已经明确：直接生成完整 questions，且每题内联 concept / testableClaim / evidence
  -> 若用户要求先看题/修改题：展示题目清单并等待确认
  -> 若题目内容已明确或用户授权直接创建：构造完整请求图，生成稳定 clientRequestId，把后端请求体写入 JSON 文件
  -> 调 scripts/pracmo-cache.sh ledger-start <请求体文件> [sourceFingerprint]
  -> 执行 scripts/pracmo-open-api.sh learning-track-exercise <文件>
  -> 成功后调 scripts/pracmo-cache.sh ledger-success，并在有 source fingerprint 时 record-source
  -> 返回甲程与练习创建结果，并提示 App 打开方式和共享链接用途
```

## 资料输入边界

当用户提供网页、B 站链接、PDF、本地文件、Markdown 长文、截图或明显资料内容时，资料只作为 Agent 理解和出题的输入来源。主路径不要求创建 `material`，也不要求后端抓取资料、转换 PDF、抽字幕、拼 prompt 或生成题目。

处理要求：

1. Agent 自行读取和理解资料，提炼 concepts、testable claims、题目、选项和解析。
2. 提交给后端时必须已经是完整结构化 questions；server 只接收和校验结构。
3. `exercise.userRequest` 写清来源边界，例如“基于用户提供的 Markdown 笔记生成；答案依据以笔记内容为准”。
4. 每题用 `evidenceRef` / `evidenceSnippet` 保留可追溯依据，例如 `agent-source:file:notes.md#section-2`；不要把大段原文塞进请求体。
5. 如需后续“继续基于这个文件补一组”，用 `scripts/pracmo-cache.sh fingerprint-file|fingerprint-url|fingerprint-text` 建立本地来源指纹，再通过 source mapping 找回上次甲程。

只有题目本身必须展示图片时，才使用 `pracmo-oss-upload.sh --category practice-assets` 上传图片资产，并把 HTTPS OSS URL 写入题干或选项 Markdown。资料原文上传和 `materialId` 不属于当前主流程。

## 执行速查

按下面顺序执行，不跳步：

1. 无 `PRACMO_APIKEY`：立即停止，只提示用户本地设置 API Key。
2. 上下文不足：只问“要围绕什么主题或资料创建甲程练习”。
3. 有强/中匹配甲程：先让用户选择“复用哪一个”或“创建新甲程”。
4. 新建甲程且无标题：先问一次标题；用户说“你来定/直接创建/确认”后再自动生成。
5. 有来源文件/URL/文本时：先生成 source fingerprint，查本地 source mapping；命中后必须向 server 验证 track。
6. 复用已有甲程：先查 timeline，再查 concepts，然后再生成题目。
7. 用户要求审题、改题或等待确认：先展示完整题目清单，确认后再调用接口。
8. 条件明确且用户未要求暂停：直接构造完整 JSON，写入文件，先写 ledger pending，再调用 `learning-track-exercise`。
9. 成功后：写 ledger succeeded；若有 source fingerprint，写 source -> track 映射。
10. 接口超时、无响应、`curl 失败` 或疑似 500 后已提交：先写 ledger uncertain，再走“可能部分成功”恢复流程，不要立刻重复提交创建请求。

## 直接创建条件

默认不为了形式化确认而打断用户。满足以下条件时，可以直接调用接口创建：

- 已检测到 `PRACMO_APIKEY`。
- 已经能确定是新建甲程，或用户已经明确指定/选择了要复用的已有甲程。
- 若是新建甲程，用户已经提供甲程标题，或已经明确表示“没有标题 / 你来定 / 按内容生成 / 直接创建 / 确认”，允许 Agent 自动生成标题。
- 若复用已有甲程，已经读取该甲程练习时间线和 concepts。
- 甲程标题选择、甲程说明、练习标题、练习目标、题量、题型、核心 concepts 都能从上下文或用户要求中明确推出。
- 完整 `questions` 已生成，且每题都有 `concept`、`testableClaim`、`questionContent`、`options[]`、`bloomLevel`。
- 如果本次基于资料创建，Agent 已经读完资料并明确题目来源边界；不要求 `materialId`。
- 用户没有要求“先给我看看题”“先不要创建”“等我确认后再创建”等暂停语义。

必须停下来确认的情况：

- 有多个强/中匹配甲程，需要用户选择复用哪一个或新建。
- 需要新建甲程，但用户尚未提供标题，也尚未授权 Agent 自动生成标题。
- 复用甲程已有过多未完成练习，或创建接口明确返回队列已满。
- 题量、题型、范围、难度或材料边界存在明显歧义。
- 生成题目后发现 concept 过宽、题目依据不足、题型结构不合法，必须先修正或让用户确认。
- 用户明确要求先审题或先看草案。

CHECKPOINT · STOP：命中以上任一条时，不要调用创建接口；先向用户展示选择项、元信息草案或题目清单。

如果直接创建，创建前不需要把完整题目清单展示给用户；但请求体必须在内部完整构造并通过自检。

## Concept 提炼方法

核心规则：

> Concept 是“可被提问验证的最小稳定学习对象”，不是关键词、章节标题、宽泛主题或用户的学习动作。

本 skill 必须自包含完成 concept 提炼，不依赖外部文档。采用轻量命题图谱法：

1. 识别输入场景。
2. 从资料或对话中提取可验证命题，而不是直接抽关键词。
3. 将命题归并为 1-5 个稳定 concepts；普通首练习优先 1-3 个，避免范围过宽。
4. 为每个 concept 写出 1-3 条可测命题，作为题目的 `testableClaim` 候选。
5. 围绕 concepts 生成题目，并把每题的 concept、testableClaim、Bloom 和 evidence 直接写在 question 上。

提炼步骤：

1. 划定来源边界：本次依据来自对话、资料、用户枚举，还是已有甲程 concepts。
2. 找出材料中能被判对错的陈述，例如定义、条件、因果、区别、步骤、适用边界。
3. 合并同义陈述，删除只有标题没有正文支撑的词。
4. 给 concept 命名时写完整对象和关系，不写“区别”“应用”“影响”这类空壳。
5. 为每个 concept 检查至少能生成一道明确可评分题；不能出题的条目不要作为 concept。
6. 生成题目时让 `testableClaim` 比 concept 更具体，能对应到一个判断动作或应用动作。
7. 材料题必须写 `evidenceRef/evidenceSnippet`；对话题也应写简短来源说明，便于后续审计。

场景规则：

- `conversation`：用户只描述学习目标、困惑或想练的方向。首个练习保持窄范围，普通主题优先 1-3 个核心 concepts。
- `material`：用户提供 Markdown、文章、转录稿或资料。题目必须以资料为事实锚点；外部常识只能辅助解释，不能作为答案依据。
- `enumeration`：用户提供术语、单词、成语、公式、案例清单。尽量保留清单，每个有意义条目成为一个 concept。
- `reinforcement`：用户要求补弱或错题巩固。优先使用已有甲程 concepts 和薄弱 Bloom 层，不重新发散大主题。

Concept 选择过滤：

- 名称可独立理解。
- 来源能追溯到对话、资料、用户枚举或已有甲程 concepts。
- 至少能生成一道明确可评分题。
- 粒度不过宽也不过碎。

避免把这些写成 concept：

- “影响”
- “优缺点”
- “应用”
- “区别”
- “学习某主题”
- 资料中只有标题提到、正文没有解释的词

推荐 concept 名称：

- “分布式系统中的 CAP 定理”
- “Cache-Control 与 Expires 的优先级”
- “望梅止渴与画饼充饥的区别”
- “二分查找的边界更新规则”

## 主题与元信息草案

上下文不足时只问一个问题：

```text
你想围绕什么主题创建甲程练习？可以直接贴材料，或告诉我要练的主题。
```

## 新建甲程标题与说明

当确定需要新建甲程时，先判断用户是否已经给出甲程标题：

- 用户明确说“创建甲程《xxx》”“甲程叫 xxx”“标题用 xxx”时，直接使用用户标题。
- 用户只给主题、资料或练习目标，但没有给甲程标题时，先询问一次。
- 用户回复“没有”“你来定”“按内容生成”“直接创建”“确认”等，视为不提供标题；此时 Agent 自动生成标题并继续，不再反复追问。

询问格式保持轻量：

```text
我会新建一个甲程。你有想用的甲程标题吗？

如果没有，可以回复“你来定”，我会根据内容生成标题和说明。
```

自动生成标题时，不要只抽主题关键词，要先判断这组甲程的导向：

- `概念入门导向`：标题聚焦一个核心概念或小主题，例如“经济学中的稀缺概念”。
- `体系学习导向`：标题覆盖一组相关概念，例如“宏观经济学基础概念入门”。
- `材料精读导向`：标题体现材料主题和理解任务，例如“《xxx》观点精读与理解练习”。
- `应用训练导向`：标题体现使用场景，例如“用供需关系分析生活案例”。
- `补弱巩固导向`：标题体现薄弱点或复习目标，例如“线性代数易错概念巩固”。

甲程说明必须跟随标题导向适配：

- 概念入门标题：说明写清要理解的定义、边界、常见误区。
- 体系学习标题：说明写清覆盖范围和首个练习在整个甲程中的位置。
- 材料精读标题：说明写清以材料为依据，训练提取观点、理解逻辑和判断细节。
- 应用训练标题：说明写清要把哪些规则或模型迁移到哪些场景。
- 补弱巩固标题：说明写清要修正的薄弱点、易错判断和复习目标。

不要出现标题像“经济学入门”，说明却只围绕“稀缺”单点展开的错配；如果标题较宽，说明要承认本次首练习只是起点。如果标题较窄，说明不要承诺覆盖整个大领域。

上下文足够时，先整理出可确认的甲程和首练习草案：

```text
我先把它整理成一个甲程练习草案：

- 甲程：经济学中的稀缺概念
- 甲程说明：理解稀缺为何是经济学的基础事实，以及稀缺与人的需求升级之间的关系。
- 首个练习：稀缺：经济学的基础事实
- 练习目标：围绕资料内容考察核心概念、易错判断和必要应用，不引入资料外事实作为答案依据。
- Concepts：稀缺作为经济学的基础事实、稀缺产生的两个原因、稀缺的广义资源范围
- 建议题量：10 题
- 题型：单选、多选、判断
```

题量规则：

- 后端 `with-exercise` 当前要求最少 10 题、最多 100 题。
- 用户未指定题量时，默认 10 题。
- 用户明确要求更多时可以增加，但必须覆盖所有核心 concepts，且不超过 100。
- 如果用户要求少于 10 题，需要说明接口至少需要 10 题，并按 10 题生成。

## 已有甲程匹配

先通过脚本查询：

```bash
scripts/pracmo-open-api.sh get 'learning-tracks?keyword=主题关键词&state=active&pageSize=20'
```

匹配规则：

- 标题完全相同或高度近似：强匹配。
- 标题/说明包含核心关键词：中匹配。
- 只是同一大领域：弱匹配，不默认建议复用。
- `archived` 默认不复用，除非用户明确指定。

有强/中匹配时，必须让用户选择：

```text
我找到可能相关的已有甲程：

1. 经济学入门
   说明：……
2. 生活中的经济学概念
   说明：……

你想把这组练习放到哪：
- 加入「经济学入门」
- 加入「生活中的经济学概念」
- 创建一个新的甲程
```

CHECKPOINT · STOP：存在多个强/中匹配甲程时，用户未选择前不要默认复用，也不要绕过复用检查直接新建。

完全没有匹配时，准备新建甲程。若用户还没有给出甲程标题，按“新建甲程标题与说明”规则先询问一次；若用户不提供标题，再自动生成标题和适配说明并继续。

## 复用已有甲程前置检查

只要用户指定或选择复用已有甲程，在生成题目之前必须先执行两个只读检查。

第一步，通过脚本读取该甲程当前练习队列：

```bash
scripts/pracmo-open-api.sh get 'learning-tracks/track_xxx/timeline?nodeType=exercise&pageSize=20'
```

处理规则：

- 不再因为存在未完成练习而停止。新创建的练习会追加到甲程练习队列队尾。
- 统计状态不是 `completed` 且不是 `dismissed` 的练习节点，作为用户可见上下文；如果有未完成练习，创建成功后提示“已加入队尾，完成或跳过当前练习后会继续推进”。
- 如果未完成练习数量已经接近或达到服务端上限（当前队列上限为 20 个 active 练习），应提示用户先完成/跳过/删除部分练习，避免继续创建失败。
- 如果最终创建接口返回队列已满或生成中冲突，停止并按错误提示处理，不要改走新建甲程或孤立练习作为兜底。

第二步，通过脚本获取该甲程已关联 concepts：

```bash
scripts/pracmo-open-api.sh get 'learning-tracks/track_xxx/concepts?limit=50'
```

处理规则：

- 把返回的 `concepts[]` 作为本次出题的 concept 参照，重点读取 `conceptId`、`name`、`masteryLevel`、`state`、`relatedQuestionCount`。
- 生成题目时优先复用语义完全一致或高度一致的已有 concept 名称，不要为同义概念创造新名称。
- 若本次材料确实引入新的核心 concept，可以新增；新增 concept 必须服务于当前甲程主题，不得随意扩展到无关方向。
- 复用已有 concept 时，可以把接口返回的真实 `conceptId` 连同 `name` 一起写入 `questions[].concept`。
- 新增 concept 时只写 `questions[].concept.name`，不得编造 `conceptId`。
- 在元信息确认或题目展示时，可以自然说明“会参考已有 concept：向量加法、矩阵乘法条件……，并补充本次新 concept：……”，但不要暴露内部字段名。

## 元信息确认

当甲程归属、练习目标、题量或题型不明确时，先让用户确认甲程归属和首个练习元信息：

```text
我准备创建这个甲程，并在里面放入第一组完整练习，请确认：

- 甲程：新建「经济学中的稀缺概念」
- 甲程说明：理解稀缺为何是经济学的基础事实，以及稀缺与人的需求升级之间的关系。
- 首个练习：稀缺：经济学的基础事实
- 练习目标：覆盖核心概念、材料中的关键例子和应用判断。
- Concepts：稀缺作为经济学的基础事实、稀缺产生的两个原因、稀缺的广义资源范围
- 题型：单选、多选、判断
- 题量：10 题

你可以回复：
- “确认”
- “加入已有甲程 xxx”
- “题量改成 16”
- “去掉多选”
```

CHECKPOINT · STOP：元信息仍不明确时，只接受用户对甲程归属、题量、题型、范围的确认或修改；不要提前生成请求体并提交。

## 题目清单门禁

用户要求先看题、修改题、审核题目，或前面元信息存在歧义时，Agent 必须生成完整 `questions`，每题都内联 concept / testableClaim / evidence，并逐题展示给用户审核。此时禁止未展示题目清单就调用创建接口。

如果用户已经明确授权直接创建，或待确认内容已经明确且不需要用户审题，可以跳过题目清单展示，直接创建。

题目清单至少包含：

- 题号
- 题型
- 题干
- Bloom 层级（记忆 / 理解 / 应用 / 分析）
- 主 concept
- 单选/多选/判断的全部选项
- 每个选项是否正确
- 每个选项的解析
- 简答参考答要点（如果使用简答）

推荐展示格式：

```text
这是甲程「经济学中的稀缺概念」里的第一组练习题目。确认无误后回复「确认创建甲程」；需要修改请直接说题号和修改意见。

第 1 题（单选）
Bloom 层级：理解
主 concept：稀缺产生的两个原因
题干：……
A. …（错误）解析：……
B. …（正确）解析：……
C. …（错误）解析：……
正确答案：B
```

用户要求改题后，必须重新展示变更部分或全量清单。只有用户确认修改结果，或再次明确要求直接创建，才能调用接口。

CHECKPOINT · STOP：一旦用户说“先看题”“改一下”“等我确认”，题目清单就是硬门禁；未确认前不得调用 `learning-track-exercise`。

## 题目生成规则

- 题量必须等于最终确定的数量；如果用户未指定，默认按 10 题生成。
- 只使用用户最终保留的题型。
- 覆盖所有核心 concepts；普通主题不要为同义说法制造多个 concept。
- 避免重复题、近义重复题、纯改写重复题。
- `single_choice`：至少 3 个选项，且仅 1 个正确答案。
- `multiple_choice`：至少 3 个选项，至少 2 个正确答案，且不能所有选项都正确。
- `true_false`：固定 2 个选项，且仅 1 个正确答案；中文语境必须使用 `正确` / `错误`，英文语境才使用 `True` / `False`。
- `short_answer`：只在用户要求主观题时使用；保留 1 个参考答案选项，且 `isCorrect: true`。
- 每个 `options[]` 都必须带 `explanation`。
- 判断题只允许正确选项的 `explanation` 非空，错误选项可为空。
- 材料题必须以材料为事实锚点，不能把资料外事实作为答案依据。

## Bloom、question 内联 concept 与可测命题

新协议以 question 为中心。不要生成请求级 `concepts` 或 `planRows`；每道题自己携带足够的结构化归因信息，后端会从 question 投影出 `question_plan`：

- `questions[].concept`：本题唯一主 concept，必须有 `name`；复用已有甲程 concept 时才传真实 `conceptId`。
- `questions[].testableClaim`：本题实际考察的可测命题或能力点，必须具体可判分。
- `questions[].bloomLevel`：整数 `1-4`。
- `questions[].questionType`：必须和题目结构一致。
- `questions[].evidenceRef` / `questions[].evidenceSnippet`：材料题或对话题的审计证据，能写则必须写。

Bloom 只表示认知动作，不表示难度：

- `1`：回忆定义、事实、步骤或材料显性陈述。
- `2`：解释含义、分类、识别关系或区分简单差异。
- `3`：把规则、方法、模型或区分应用到具体场景。
- `4`：分析原因、假设、取舍、结构或反例。

`questions[].concept.name` 要求：

- 必须完整、明确、可独立理解。
- 不要写依赖上下文的碎片，例如“区别”“这个公式的应用”。
- 比较类 concept 必须写出比较对象，例如“线性相关与线性无关的区别”。
- 同一个 concept 跨多题时名称必须完全一致。
- 不要编造 `conceptId`。
- 复用已有甲程 concept 时，只有 concepts 查询结果明确返回真实 `conceptId`，才可以把 `conceptId` 与 `name` 一起传入 `questions[].concept`。
- 新增 concept 只传 `questions[].concept.name`，由后端归一化并创建/关联 concept。

`questions[]` 要求：

- 每题必须有 `concept`、`testableClaim`、`bloomLevel`、`questionType`。
- `testableClaim` 不要写宽泛主题，例如“理解 CAP 定理”；应写“判断具体系统在网络分区时牺牲的 CAP 目标”。
- `claimIndex` 是同一 concept 下 claim 的序号；不确定时可省略。
- 不传 `primaryConcept`；新写入协议不使用该字段。

## 后端请求体

最终只能通过 `scripts/pracmo-open-api.sh learning-track-exercise <json-file>` 提交。

不得 fallback 到孤立练习接口。若新接口失败，直接说明创建未完成，不要单独创建一个脱离甲程的练习。

每次创建请求都必须在 `exercise.clientRequestId` 写入一个稳定幂等键。生成规则：

- 同一次用户请求、同一份题目内容、同一甲程归属，在所有重试中必须复用同一个值。
- 推荐格式：`pracmo-create-<slug>-<YYYYMMDDHHMMSS>`；如果已经写入 JSON 文件，后续重试必须直接复用文件里的 `clientRequestId`，不要重新生成。
- 如果第一次请求新建甲程后超时，只读查询发现甲程已出现但没有可确认的成功响应，后续重试必须改为复用该甲程，并保留相同 `clientRequestId`。
- 不要把 API Key、账号 ID 或隐私材料写入 `clientRequestId`。

新建甲程请求体：

```json
{
  "track": {
    "mode": "create",
    "title": "经济学中的稀缺概念",
    "description": "理解稀缺为何是经济学的基础事实，以及稀缺与人的需求升级之间的关系。",
    "category": "economics"
  },
  "exercise": {
    "title": "稀缺：经济学的基础事实",
    "clientRequestId": "pracmo-create-scarcity-20260528162000",
    "userRequest": "基于给定材料，覆盖核心概念、关键例子和应用判断；答案依据以材料为准。",
    "questions": [
      {
        "questionType": "single_choice",
        "bloomLevel": 2,
        "concept": {
          "name": "稀缺产生的两个原因",
          "conceptType": "principle"
        },
        "testableClaim": "识别材料中解释稀缺产生的两个原因",
        "claimIndex": 1,
        "evidenceRef": "agent-source:text#scarcity-causes",
        "evidenceSnippet": "你想要的东西别人也想要，且人的需求不断变化升级。",
        "questionContent": "材料认为稀缺产生的两个原因是什么？",
        "options": [
          {
            "optionSeq": "A",
            "content": "你想要的东西别人也想要，且人的需求不断变化升级",
            "isCorrect": true,
            "explanation": "材料直接列出这两个原因。"
          },
          {
            "optionSeq": "B",
            "content": "土地总量太少，且人永远保持理性",
            "isCorrect": false,
            "explanation": "材料反而不把理性人作为最基础假设，也区分了土地和位置。"
          },
          {
            "optionSeq": "C",
            "content": "技术不会进步，且所有商品都会涨价",
            "isCorrect": false,
            "explanation": "材料没有用这两点解释稀缺。"
          }
        ]
      }
    ],
    "srcType": "api",
    "createShare": true
  }
}
```

复用已有甲程请求体：

```json
{
  "track": {
    "mode": "reuse",
    "trackId": "track_xxx"
  },
  "exercise": {
    "title": "稀缺：经济学的基础事实",
    "clientRequestId": "pracmo-create-scarcity-20260528162000",
    "userRequest": "基于用户本次提供的材料继续补充练习；答案依据以材料内容为准。",
    "questions": [
      {
        "questionType": "single_choice",
        "bloomLevel": 2,
        "concept": {
          "conceptId": "concept_xxx",
          "name": "稀缺产生的两个原因",
          "conceptType": "principle"
        },
        "testableClaim": "识别材料中解释稀缺产生的两个原因",
        "claimIndex": 1,
        "evidenceRef": "agent-source:text#scarcity-causes",
        "evidenceSnippet": "你想要的东西别人也想要，且人的需求不断变化升级。",
        "questionContent": "……",
        "options": [
          {
            "optionSeq": "A",
            "content": "……",
            "isCorrect": true,
            "explanation": "……"
          },
          {
            "optionSeq": "B",
            "content": "……",
            "isCorrect": false,
            "explanation": "……"
          },
          {
            "optionSeq": "C",
            "content": "……",
            "isCorrect": false,
            "explanation": "……"
          }
        ]
      }
    ],
    "srcType": "api",
    "createShare": true
  }
}
```

字段说明：

- `exercise.title` 对应练习标题。
- `exercise.clientRequestId` 对应本次创建请求的幂等键；重试同一请求时必须保持不变，服务端会用它复用已创建的练习节点，避免重复创建。
- `exercise.userRequest` 对应首练习内容要求；写清来源、范围、难度、题型和材料约束。
- `questions[].concept` 对应题目主 concept；新增 concept 不传 `conceptId`，复用已有 concept 才传真实 `conceptId`。
- `questions[].testableClaim` 对应题目实际考察的可测命题。
- `questions[].questionContent` 对应题干。
- `questions[].options[]` 对应选项；每个选项必须有 `optionSeq`、`content`、`isCorrect`、`explanation`。
- `questions[].evidenceRef/evidenceSnippet` 记录 Agent 侧来源依据；不要保存大段原文。
- `exercise.materialId` 不属于当前主流程；不要为了创建练习而先走 material 接口。
- 不要在请求体里传 `qualityChecks` 或无引用关系的顶层草案字段。

## 图片 Markdown 自检

题干、选项和解析可以使用 Markdown 图片，但必须先上传到 OSS，再写入请求体：

```markdown
![供需曲线示意图](https://bucket.oss-cn-hangzhou.aliyuncs.com/material/1001/practice-assets/diagram.png)
```

提交前逐题自检：

- 所有图片 URL 必须以 `https://` 开头，并位于 `oss-config` 返回的 `objectKeyPrefix` 下。
- 禁止 `file://`、`/Users/...`、相对路径、`data:image/...base64`、非 OSS 第三方图片链接。
- 图片 Markdown 必须有简短 alt 文本，不能写成 `![](url)`。
- 选项可以含图片，但必须保留必要文字，避免纯图片选项无法理解。
- `single_choice` 恰好一个正确答案；`multiple_choice` 至少两个正确答案；`true_false` 只能有两个判断选项；`short_answer` 不传选择题选项。
- 每题仍必须保留 `concept`、`testableClaim`、`evidenceRef/evidenceSnippet`，图片不能替代可追溯依据。

## 创建接口调用

当满足“直接创建条件”，或用户确认题目清单后，先将最终请求体写入 JSON 文件，再写本地创建台账：

```bash
scripts/pracmo-cache.sh ledger-start /tmp/pracmo-create/<slug>.json [sourceFingerprint]
```

然后执行：

```bash
scripts/pracmo-open-api.sh learning-track-exercise /tmp/pracmo-create/<slug>.json
```

如果接口报错，不要改走旧孤立练习路径。

创建成功后，必须把响应写入台账：

```bash
scripts/pracmo-cache.sh ledger-success <clientRequestId> /tmp/pracmo-create/<response>.json
```

如果本次有来源指纹，还要记录 source -> track 映射：

```bash
scripts/pracmo-cache.sh record-source /tmp/pracmo-create/<source-track-map>.json
```

映射只是候选缓存。下次命中后仍必须向 server 查询 timeline 或 `learning-tracks?keyword=...` 验证 track 仍存在并属于当前 API Key 对应账号。

如果接口无响应、超时、终端会话中断、`curl 失败`，或返回可能发生在服务端提交后的 `500`，必须按“可能部分成功”处理：

1. 不要立刻重新提交创建请求。
2. 用 `pracmo-cache.sh ledger-uncertain <clientRequestId> "<reason>"` 标记不确定状态。
3. 先保留原 JSON 文件和其中的 `clientRequestId`。
4. 优先用 `pracmo-cache.sh ledger-lookup <clientRequestId>` 查看是否已有 succeeded 记录。
5. 如果是新建甲程请求，先按甲程标题查询 `learning-tracks?keyword=...&state=active&pageSize=20`，确认是否已经出现新甲程。
6. 如果找到本次标题/说明匹配的甲程，查询 `learning-tracks/{trackId}/timeline?nodeType=exercise&pageSize=20`。
7. 如果时间线里已有本次练习标题或响应中的练习节点，直接按成功处理，并补写 `ledger-success`；如果有多条本次重试产生的 active 练习节点，只保留最新一条，把较早重复节点用 `scripts/pracmo-open-api.sh dismiss-node <nodeId>` 标记为跳过。
8. 如果新甲程已出现但时间线没有练习节点，才把原请求改成 `track.mode="reuse"`、`track.trackId=<已出现的甲程>`，并保持同一个 `exercise.clientRequestId` 后重试。
9. 如果复用请求返回 `reusedExisting=true`，按成功处理，不再继续提交。
10. 如果明确返回“队列已满”或“同甲程已有生成中的练习”，停止；提示用户先完成/跳过/删除队列中的练习，或等待生成完成后再试，不要通过新建甲程绕开。

CHECKPOINT · STOP：疑似部分成功时，第一动作是只读查询和复用原 `clientRequestId`；不要重新生成 `clientRequestId`，不要重新提交原创建请求。

## 成功响应处理

重点读取：

- `data.trackId`
- `data.trackTitle`
- `data.exerciseId`
- `data.exerciseTitle`
- `data.questionCount`
- `data.shareToken`
- `data.shareUrl`
- `data.shortShareUrl`

链接规则：

1. 创建接口在 `createShare=true` 时返回的是**甲程分享**链接，必须对齐 App 端甲程分享：生产环境通常是 `https://u.zendong.com.cn/s/t...`，Web/App 会按 `t...` token 进入甲程分享落地页。
2. 优先展示响应里的 `shareUrl`；如果 `shareUrl` 为空但有 `shortShareUrl`，展示 `shortShareUrl`。
3. 如果只有 `shareToken`，按短链规则构造 `https://u.zendong.com.cn/s/{shareToken}`；不要把 `t...` token 拼成 `https://www.zendong.com.cn/s/flow/{shareToken}`。
4. 不要把 `apis.zendong.com.cn` 的 host 展示给用户；不要把后端已返回的 `u.zendong.com.cn` 短链强行改写成 `www.zendong.com.cn`。

返回格式：

```text
已创建：

- 甲程：经济学中的稀缺概念
- 首个练习：稀缺：经济学的基础事实，10 题
- 分享链接：https://u.zendong.com.cn/s/txxx

请优先打开璞奇 App，在甲程里查看并继续练习；也可以使用上面的分享链接在 Web/App 中查看或分享给他人。
```

复用旧甲程时说明：

```text
已加入已有甲程「经济学入门」。
```

如果响应里有 `appDeepLink`，可以补充：

```text
如果你在当前设备已安装璞奇 App，可以直接打开 App 进入练习；如果打不开，就使用上面的分享链接查看。
```

## 命令行脚本

优先使用仓库脚本提交已生成的 JSON，请勿在对话中临时重写 HTTP 客户端。

开放 API 脚本路径：

```text
scripts/pracmo-open-api.sh
```

子命令：

| 子命令 | 作用 |
|---|---|
| `learning-track-exercise <文件|->` | 一次性创建/复用甲程并创建练习节点 |
| `get <path>` | 查询开放 API 资源，例如 `learning-tracks?keyword=xxx` |
| `dismiss-node <nodeId>` | 用于超时恢复时跳过重复练习节点 |

示例：

```bash
export PRACMO_APIKEY="..."

scripts/pracmo-open-api.sh get 'learning-tracks?keyword=线性代数'
scripts/pracmo-open-api.sh get 'learning-tracks/track_xxx/timeline?nodeType=exercise&pageSize=20'
scripts/pracmo-open-api.sh get 'learning-tracks/track_xxx/concepts?limit=50'
scripts/pracmo-open-api.sh learning-track-exercise /tmp/pracmo-create/linear-algebra.json
```

本地缓存脚本路径：

```text
scripts/pracmo-cache.sh
```

缓存只保存两类信息：来源到甲程映射、创建请求台账。不要缓存 API Key、大段原文资料、用户作答明细、掌握度快照、错题详情或 SRS 进度。

缓存目录默认是 skill 内的 `cache/`，可用 `PRACMO_CREATE_CACHE_DIR` 临时覆盖；缓存内容由该目录下的 `.gitignore` 忽略，不提交到仓库。缓存按 `accountScope + 脚本内置 API 入口` 隔离。

常用子命令：

| 子命令 | 作用 |
|---|---|
| `cache-dir` | 初始化并输出缓存目录 |
| `fingerprint-file <path>` | 生成文件来源指纹，不保存文件内容 |
| `fingerprint-url <url>` | 生成规范化 URL 指纹 |
| `fingerprint-text <text>` | 生成规范化文本摘要指纹，不保存全文 |
| `lookup-source <sourceFingerprint>` | 查询本地 source -> track 候选 |
| `record-source <json-file|->` | 创建成功后记录 source -> track 映射 |
| `ledger-start <payload-json-file> [sourceFingerprint]` | 创建前保存 payload，并写 pending 台账 |
| `ledger-success <clientRequestId> <response-json-file|->` | 创建成功后写 succeeded 台账 |
| `ledger-uncertain <clientRequestId> [reason]` | 超时、curl 失败、疑似 500 后写 uncertain 台账 |
| `ledger-lookup <clientRequestId>` | 按幂等键读取最新台账 |

典型顺序：

```bash
source_json="$(scripts/pracmo-cache.sh fingerprint-file ./notes.md)"
source_fingerprint="$(printf '%s' "$source_json" | jq -r '.fingerprint')"
scripts/pracmo-cache.sh lookup-source "$source_fingerprint" || true

scripts/pracmo-cache.sh ledger-start /tmp/pracmo-create/notes.json "$source_fingerprint"
scripts/pracmo-open-api.sh learning-track-exercise /tmp/pracmo-create/notes.json > /tmp/pracmo-create/notes.response.json
scripts/pracmo-cache.sh ledger-success "$(jq -r '.exercise.clientRequestId' /tmp/pracmo-create/notes.json)" /tmp/pracmo-create/notes.response.json
```

API Key 鉴权接口由脚本统一处理；不要在 `SKILL.md` 中手写接口地址。

## 开放 API 创建配额

开放 API 创建类操作实行按日限额：同一 API Key 对应账户，每个自然日（Asia/Shanghai）合计最多成功创建 10 次。

计入创建次数的操作：

- 创建甲程练习（`learning-track-exercise`）

查询类请求不占用额度，例如：

- 甲程列表查询
- 甲程时间线查询
- 甲程 concepts 查询

超限通常返回 HTTP 429 / `LIMIT_EXCEEDED`。遇到 429 时不要盲目重试，应说明今日开放接口创建次数已达上限。

## 错误处理

| 错误码 | 含义 | 处理方式 |
|---|---|---|
| `401` | API Key 缺失或无效 | 提示用户检查 `PRACMO_APIKEY` |
| `400` | 请求体结构错误 | 检查字段名、字段类型、必填字段 |
| `422` | 题目结构不符合要求、队列已满或同甲程已有生成中的练习 | 调整题量和题目结构；若提示队列已满或生成中，则让用户先处理队列或稍后再创建 |
| `429` | 超出每日创建配额 | 说明配额已满，不要盲目重试 |
| `500` | 服务端可能已部分提交或提交后报错 | 先写 `ledger-uncertain`，再按 `clientRequestId`、甲程标题和 timeline 做只读恢复；确认没有部分成功前不得重新提交创建请求 |

如果新接口创建失败，不允许 fallback 到孤立练习。应说明：

```text
创建没有完成，我不会单独创建一个脱离甲程的练习。你可以让我重试，或调整甲程/题目后再创建。
```

## 反例与黑名单

以下行为禁止执行；命中时必须回到对应检查点：

| 反例 | 为什么禁止 | 正确做法 |
|---|---|---|
| 缺少 `PRACMO_APIKEY` 仍继续整理草案或生成题目 | 会让用户误以为已经进入创建流程 | 立即停止，只给 API Key 设置说明 |
| 用户说“只要练习，不要甲程”就调用旧孤立练习接口 | 当前产品约束是练习归属甲程 | 解释必须新建甲程或加入已有甲程 |
| 手写 host、接口地址或绕过脚本直接请求开放 API | 会绕过当前 skill 的固定创建通道，导致缓存和创建台账不可比对 | 始终使用 `scripts/pracmo-open-api.sh` |
| 发现强/中匹配甲程后默认选一个复用 | 可能把练习放错甲程 | 展示候选，等待用户选择 |
| 复用甲程时跳过 timeline 或 concepts 查询 | 容易忽略队列状态和重复 concept | 先查 timeline，再查 concepts |
| 为新增 concept 编造 `conceptId` | `conceptId` 必须来自后端 | 新 concept 只传 `name` |
| 用户要求审题时直接创建 | 违反用户暂停语义 | 展示完整题目清单，确认后再创建 |
| 超时或 500 后立刻重新提交创建请求 | 可能创建重复甲程或重复练习节点 | 按标题、timeline 和原 `clientRequestId` 做恢复 |
| 队列已满或生成中时改为新建甲程绕开 | 会破坏用户原甲程结构 | 停止并提示用户处理队列或稍后再试 |
| 把 `t...` 分享 token 拼成旧 `/s/flow/...` 链接 | 甲程分享和练习分享路由不同 | 优先用响应里的 `shareUrl`，否则构造 `https://u.zendong.com.cn/s/{shareToken}` |
| 把 API Key、账号 ID 或隐私材料写入 `clientRequestId` | 会泄露隐私并污染幂等键 | 使用无隐私 slug 和时间戳 |

## 注意事项

1. 只创建“新甲程 + 首个完整练习”或“已有甲程 + 队尾追加一组完整练习”。
2. 默认先查已有甲程并让用户选择复用或新建。
3. 复用已有甲程前，必须先查练习时间线；已有未完成练习时仍可追加到队尾，但要在成功后提示用户先完成或跳过当前练习。
4. 复用已有甲程前，必须先查该甲程 concepts；生成题目时复用或补充 concepts，不得重复制造同义 concept。
5. 待确认内容明确时可以直接创建；不为形式化确认而额外打断用户。
6. 用户要求先看题、修改题或等待确认时，题目清单确认才是硬门禁。
7. 练习必须一次性提交完整 `questions`，不拆成多次写入。
8. 每道题必须带 `concept`、`testableClaim`、`bloomLevel` 和 `questionType`。
9. 不要编造 `conceptId`；只有复用已有甲程且 concepts 接口返回真实 ID 时才传。
10. 中文判断题必须使用 `正确` / `错误`，不能写 `True` / `False`。
11. 没有真实旧甲程要复用时，不要输出空的 `trackId` / `existingTrackId`。
12. 用户侧不要暴露内部字段名。
13. 分享链接必须对齐后端返回的甲程分享短链；生产环境通常是 `https://u.zendong.com.cn/s/t...`，不要改写成旧的 `/s/flow/...` 练习分享链接。
14. `PRACMO_APIKEY` 仅发送给璞奇后端，不发送到第三方服务。
