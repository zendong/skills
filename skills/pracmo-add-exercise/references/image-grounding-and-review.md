# 练习图片的取证、制作与严格复核

本规范适用于题干图、选项图、图表、流程图、地图、时间线、结构示意图和带事实文字的插图。目标不是“看起来像”，而是让图中每个可判定事实都能回到已读取的可靠来源。

## 1. 先取证，后画图

按以下顺序寻找资料：

1. 用户指定且可读取的原始材料。
2. 官方文档、政府或机构原始数据、正式标准、论文原文、作者或项目的一手说明。
3. 大学、博物馆、专业组织等可信机构的教学材料。
4. 有编辑审核、能链接回原始证据的可靠二手来源。

不得把搜索摘要、聚合页、无出处转载、社交媒体帖或模型参数记忆当作唯一证据。事实具有时效性时记录资料发布日期或版本以及 `retrievedAt`；高风险或存在争议的命题应优先使用一手来源并交叉核对，否则不出该题。

可以检索已有图片，也可以基于证据重新绘制。重新绘制通常更利于版权和清晰度，但“自己画”不等于可以省略来源。不得未经许可复制受保护的图；记录许可、公共领域状态或原创改绘说明。

## 2. Manifest 合同

图片 manifest 顶层：

```json
{
  "schemaVersion": "pracmo-exercise-images@v1",
  "clientRequestId": "与练习请求一致",
  "resources": [],
  "assets": []
}
```

每个 `resources[]` 至少包含：

- `resourceId`：本包唯一 ID。
- `title`、`publisher`、`url`、`retrievedAt`。
- `sourceType`：`primary`、`official`、`standard`、`peer_reviewed`、`reputable_secondary` 之一。

每个 `assets[]` 至少包含：

```json
{
  "assetId": "kv-cache-flow",
  "localPath": "assets/kv-cache-flow.png",
  "altText": "KV 缓存复用流程",
  "factuality": "factual",
  "provenance": "generated_from_sources",
  "sourceMode": "real_scene_generated",
  "sourceType": "official",
  "sourceDetails": {
    "generationMethod": "使用图片生成工具直接生成整张完整成图",
    "resourceIds": ["resource-1"],
    "wholeImageGenerated": true,
    "localLayoutApplied": false
  },
  "license": "original",
  "claims": [
    {
      "claimId": "claim-1",
      "text": "图中具体表达的事实",
      "resourceIds": ["resource-1"]
    }
  ],
  "expectedVisibleText": ["必须逐字出现的文本"],
  "expectedRelations": ["A 的箭头指向 B"],
  "containsNumbers": true,
  "expectedValues": [
    {
      "label": "图中标签或指标",
      "displayValue": "17.2%",
      "unit": "%",
      "resourceIds": ["resource-1"]
    }
  ],
  "usedBy": [{"questionIndex": 0, "field": "questionContent"}],
  "review": {}
}
```

`sourceType` 对每个 asset 必填：与 `resources[].sourceType` 同一套取值口径（`primary`/`official`/`standard`/`peer_reviewed`/`reputable_secondary`），CLI 只校验非空，但填错会让复核无从对齐。

`factuality` 为 `factual` 时必须有 `claims`，每条 claim 至少引用一个已登记资源。纯几何装饰或不表达外部事实的操作示意可以用 `non_factual`，但仍必须复核文字、逻辑和题目答案。

`containsNumbers` 必须显式声明。为 `true` 时，图中每个用于理解或作答的数字都应登记到 `expectedValues`，用 `displayValue` 保留小数点、百分号等精确显示形式，并引用来源；数字很多时可以按数据系列登记并在 `notes` 说明逐项比对方法，不得只抽查。

`usedBy.field` 使用 `questionContent` 或 `options[n].content`，必须与实际 `asset://` 出现位置完全一致。

### 来源模式合同

- `web_downloaded`：`sourceDetails` 必须包含 `resourceIds`、与登记资源一致的 HTTPS `originalUrl`、原下载文件的 `downloadSha256`；`license` 必须说明可使用依据。
  asset 顶层还必须写 `sourceUrl`（与 `sourceDetails.originalUrl` 同一 HTTPS 地址）与 `resourceId`（`resources[]` 中已登记的、描述该图片来源的那条资源 ID；CLI 会校验它确实存在）。
- `real_scene_generated`：`sourceDetails` 必须包含 `generationMethod`、支撑场景与事实的 `resourceIds`、`wholeImageGenerated: true` 和 `localLayoutApplied: false`。整张完整成图必须直接来自图片生成工具。
- 不允许其它来源模式。无法证明真实来源或真实场景时，删除图片引用，改用纯文字题。

## 3. 制作要求

- 默认禁止本地排版。不得使用 Pillow、Canvas、SVG、HTML/CSS、截图拼贴、后期贴字、透视合成或代码绘图改变可见内容；不得先生成底图再把文字、数字、UI、箭头、人物或背景叠上去。
- 只允许不改变可见内容的压缩、格式转换、元数据清理和透明通道处理。用户明确要求本地排版/合成时才可例外，并在 `generationMethod`、审阅 notes 和交付说明中记录。
- 生图结果有错字、伪字、数字错误、逻辑错误、姿态错误、品牌/机型泄露或真实性不足时，整图重新生成；禁止用局部覆盖或后期排版修补。
- 优先使用原始高分辨率资料或从证据重新绘制，禁止反复转存的模糊图。
- 图片只包含作答所需信息；不要通过高亮、文件名、角标或图中文字直接暴露答案。
- 以手机屏幕为基准设计字号、线宽、留白和对比度；色彩不能是区分答案的唯一手段。
- 压缩后的单张文件不超过 512 KiB，仅允许 PNG、JPEG、WebP。
- 替换、压缩、裁切、重绘之后，旧审阅全部失效，必须审阅最终待上传文件。

## 4. 严格比较清单

必须实际打开待上传文件，放大查看，并与 manifest、来源页面和练习题逐项对照：

- 文字：逐字核对标题、标签、脚注、专名、大小写、拼写、符号和语言。
- 数值：逐项核对数值、单位、量纲、比例、百分号、日期、精度、坐标刻度和图例。
- 结构：核对节点、箭头、顺序、方向、层级、集合关系、空间对应和颜色映射。
- 事实：每个 `claim` 都能从其 `resourceIds` 对应来源直接支持，不把推测画成事实。
- 题目：只看图片和题干独立作答，复算结果，再逐项对照选项、正确答案和各 option 的解析。
- 教学：难度与 Bloom 层级匹配，干扰项有诊断价值，图片没有额外歧义或答案泄漏。
- 呈现：按手机宽度查看仍清楚，压缩无明显伪影，色弱或灰度下仍能理解关键区别。

OCR 可用于发现漏字，但不能证明文字正确；自动图像相似度只能证明文件近似，不能证明事实、逻辑或答案正确。

审阅通过时写入：

```json
{
  "sourceVerified": true,
  "pixelInspected": true,
  "textVerified": true,
  "logicVerified": true,
  "numbersVerified": true,
  "questionAnswerVerified": true,
  "mobileReadabilityVerified": true,
  "answerLeakageChecked": true,
  "authenticityVerified": true,
  "scenePlausibilityVerified": true,
  "deviceNeutralityVerified": true,
  "privacyVerified": true,
  "reviewedAt": "ISO-8601 timestamp",
  "notes": "具体记录核对了哪些文字、数字、关系以及独立作答结果"
}
```

不得为了通过脚本虚填 `true`。任何一项不能确认时必须保持失败状态，修正或删除图片，不能继续上传和创建。

其中真实性与隐私复核还必须确认：画面不是低保真卡片或占位 UI；真实场景中的布局、透视与操作合理；手机不带特定厂商或机型特征；图中没有真实姓名、手机号、账号、订单号、地址、可路由链接、二维码、银行卡或可识别品牌。图片若表达客观知识，所有文字、数字和状态都要回到资源逐项核对。
