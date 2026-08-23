---
name: pracmo-add-exercise
description: "在用户已有的璞奇甲程中创建一组私人练习，也支持为题干或选项制作、检索、校验并上传事实可靠的图片、图表和示意图。用户说练一下、把内容做成练习、给某个甲程出题或补练习、看图出题时使用。必须先读取 API Key 所属用户的存量甲程；不得创建甲程。没有存量甲程时，提示用户先到璞奇手机端创建甲程。"
---

# Pracmo Add Exercise

把对话、资料或目标整理成一组完整题目，并添加到用户选定的存量甲程。这个 skill 只创建私人练习，不创建甲程、不公开练习、不创建分享链接。

开始前必须完整阅读：

- `references/exercise-json-contract.md`
- 涉及图片、图表、事实性数字或需要外部资料时，再完整阅读 `references/image-grounding-and-review.md`

## 强制前置步骤：读取并选择甲程

写题前检查 `PRACMO_APIKEY`，不要让用户把 Key 发到聊天里。缺少时提示用户从 `https://www.zendong.com.cn/app/api-key` 获取并在本地设置。

调用 `GET /open/v1/learning-tracks?state=active&pageSize=100`；用户给了名称时同时传 `keyword`。也可使用：

```bash
scripts/pracmo-open-api.sh list-tracks "甲程关键词"
```

选择规则：

1. 只有一个明确匹配项时使用它，并在创建前告诉用户甲程名称。
2. 有多个合理匹配项时列出标题和 `trackId`，让用户选择；不要猜。
3. 没有 active 甲程，或搜索结果为空且不存在其他合理候选时，停止并原样提示：

```text
没有找到可用的存量甲程。请先到璞奇手机端创建甲程，创建后告诉我，我就能读取到并继续添加练习。
```

不得创建甲程，也不得调用任何 import、`with-exercise` 或甲程创建接口。用户明确要求“新建甲程”时同样使用上面的手机端提示。

## 资料取证与出题

- 生成 10–100 道完整可作答题目；默认 10–15 道，除非用户指定。
- 支持单选、多选、判断、简答；每题包含答案、解析、1–4 的 Bloom 层级、知识点和可测命题。
- 先读用户给出的材料。事实性内容不足时，主动检索并实际打开高质量来源；优先一手资料、官方文档、标准、原始数据和同行评审论文。
- 不得依赖模型参数记忆来断言事实、数字、原话、时效状态或专业关系。搜索摘要只能用于定位来源，不能作为唯一证据。
- 题干、答案、解析以及图片中的事实都必须能追溯到实际读取的材料；无法找到可靠依据时删去该命题、改成不带事实断言的题，或向用户索取材料。
- 题干与解析须面向 App 用户自包含，不能依赖 Agent 上下文或本地路径。
- 用户只要求“先看看”时，先输出或保存草稿并停止，不调用写接口。

请求基础格式：

```json
{
  "schemaVersion": "pracmo-track-exercise@v1",
  "clientRequestId": "exercise-20260823-stable-id",
  "exercise": {
    "title": "练习标题",
    "userRequest": "练习目标",
    "difficultyLevel": 2,
    "questions": []
  }
}
```

不要输出或依赖 `accessMode`、`createShare`；即使传入，Server 也会强制为 private 且不会分享。

## 图片创作包

图片不是装饰。只有当它承载观察、比较、空间关系、流程、数据读取或辨认任务时才添加；纯装饰图应省略。

在最终上传前，用两个文件创作：

- `exercise.authoring.json`：保持最终 API 结构，在题干或选项 Markdown 中用 `asset://<assetId>` 临时占位。
- `exercise-images.json`：按 `pracmo-exercise-images@v1` 记录来源、逐条事实、预期可见文字、逻辑关系、使用位置、许可和严格审阅结果。

示例：

```markdown
观察图示：![注意力缓存流程](asset://kv-cache-flow)
```

先把原图放入 `source-assets/`，再压缩到独立审阅目录：

```bash
python3 scripts/compress_exercise_images.py \
  output/<slug>/exercise-images.json \
  -o output/<slug>/reviewed/exercise-images.json
```

压缩脚本会删除旧的 `review`，因为必须针对压缩后的实际文件重新审阅。缺少依赖时只在本地安装 `Pillow`，不得降低校验。

## 图片正确性硬门禁

对 `reviewed/assets/` 中每张实际图片逐像素查看，逐项与证据清单和来源比较。OCR、程序检查和视觉模型只能辅助，不能替代完整人工式复核。至少确认：

1. 所有标题、标签、正文、符号、拼写和语言都准确、无乱码、无截断。
2. 所有数字、单位、比例、坐标轴、图例、日期、小数点和正负号与来源一致。
3. 箭头方向、因果、顺序、包含关系、空间位置、颜色映射和流程分支逻辑正确。
4. 图片、题干、选项、正确答案和解析互相一致；遮住答案后独立作答一次，正确答案唯一或符合题型定义。
5. 图片不直接泄露答案，干扰项仍合理，手机端缩放后文字可读，关键内容不依赖难以区分的颜色。
6. 检索图或改绘图的来源、许可和事实声明完整；事实图必须逐条引用资源 ID。

将每项真实结果写入 manifest 的 `review`。有任何不确定、看不清、来源冲突或逻辑歧义时，修图后从头复核。任何一项未通过都不得创建。

复核后运行硬校验：

```bash
python3 scripts/validate_exercise_package.py \
  output/<slug>/exercise.authoring.json \
  --manifest output/<slug>/reviewed/exercise-images.json \
  --stage reviewed
```

## 上传与最终化

只有 reviewed 校验通过后才能上传。下面的命令会使用私人 `practiceAssets` OSS 前缀上传、重新下载并校验上传内容哈希，再把所有 `asset://` 替换成 HTTPS URL；内部证据清单不会进入 API 请求。缺少上传依赖时在本地安装 `oss2`，不得绕过最终化脚本手工拼 URL：

```bash
python3 scripts/finalize_exercise_images.py \
  output/<slug>/exercise.authoring.json \
  --manifest output/<slug>/reviewed/exercise-images.json \
  -o output/<slug>/exercise.json

python3 scripts/validate_exercise_package.py \
  output/<slug>/exercise.json --stage finalized
```

最终 JSON 不得含本地路径、`asset://`、`file://`、base64 图片或不安全 URL。图片只允许 HTTPS Markdown URL。

## 创建

用户要求实际创建、目标甲程明确且所有适用门禁通过时：

```bash
scripts/pracmo-open-api.sh add-exercise <trackId> output/<slug>/exercise.json
```

这会调用 `POST /open/v1/learning-tracks/:trackId/exercises`。`trackId` 只能来自刚读取的 API 结果，不可臆造或从别人的分享内容复制。无图片时也应以 `--stage finalized` 校验最终请求。

## 幂等与反馈

- 同一份内容重试必须保持相同 `clientRequestId` 和 JSON。
- 相同 ID 换内容会返回冲突；内容实质修改后生成新 ID。
- 超时后先用相同请求重试，不要换 ID 制造重复练习。
- 成功后报告甲程标题、`trackId`、练习标题、`exerciseId`、题目数和图片数，并明确它是用户自己的私人练习。
- 甲程不存在、已结束或不属于 API Key 用户时停止；不要自动换到其他甲程。
