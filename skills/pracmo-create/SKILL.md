---
name: pracmo-create
description: "当用户说“练一下”“把这段内容做成练习”“记一下”“存成笔记”“帮我记到某个笔记本”之类的话时，必须使用这个 skill。它会先检查环境变量 `PRACMO_APIKEY`；若用户要创建流炼练习，则先展示练习草案、确认题型与题量后调用 `https://apis.zendong.com.cn/public/v1/flow/exercise`；若用户要记录笔记，则先获取笔记本列表，提示有哪些笔记本，再按用户选择创建笔记；如果输入了新的笔记本名称，则先创建笔记本再创建笔记。"
---

# Pracmo Create

## 用途

本 skill 用于把当前对话里的材料直接“创建”成两类对象之一：

- 流炼练习
- 笔记

优先在以下表达出现时触发：

- “练一下”
- “把这个做成练习”
- “帮我生成一个流炼练习”
- “把上面的内容整理成题目给我练”
- “根据这段内容出题”
- “记一下”
- “把这个存成笔记”
- “帮我记到笔记本”
- “把上面的内容记下来”
- “存到某个笔记本里”

## 先做认证检查

在任何内容整理、出题、列出笔记本或接口调用前，先检查当前运行环境是否可读取 `PRACMO_APIKEY`。

如果没有检测到 `PRACMO_APIKEY`，必须立刻停止，不要继续整理草案，也不要假装已经创建成功。直接提示用户去获取并配置 API Key，推荐使用下面这段话：

```text
未检测到 PRACMO_APIKEY，暂时不能创建流炼练习或记录笔记。

请先访问 https://www.zendong.com.cn/app/api-key 获取你的 API Key，
然后在本地环境中设置：

export PRACMO_APIKEY="你的_API_Key"

设置完成后，再回来对我说“练一下”“记一下”或“确认创建”。
```

补充要求：

- 可以引导用户去 API Key 页面，但不要要求用户把 API Key 直接贴到聊天里。
- 如果用户说“不知道怎么设置环境变量”，再根据当前终端或操作系统补充更具体的设置方式。
- 如果已经知道当前 shell 是 `zsh` 或 `bash`，优先给 `export PRACMO_APIKEY="..."` 这种可直接执行的示例。

## 分流原则

收到请求后，先判断用户目标是以下哪一种：

- 要练习：进入“流炼练习创建流程”
- 要记笔记：进入“笔记创建流程”

如果目标不明确，只问一个聚焦问题，例如：

```text
你是想把这段内容做成练习，还是记成笔记？
```

不要一次问多个问题。

## 行为规则

### 0. 用户可见文案要自然

对用户说话时，优先使用自然中文，不要直接把内部字段名或接口术语抛给用户。

用户侧推荐表达：

- `title` -> “标题”
- `userRequest` -> “练习说明”
- `questionCount` -> “题量”或“共多少题”
- `shareUrl` -> “练习链接”或“分享链接”
- `name` -> “笔记本名称”
- `content` -> “笔记内容”

内部执行时，仍然必须使用真实字段名、真实请求结构和真实接口地址。

### 1. 默认先展示草案，不要直接创建

无论是练习还是笔记，只要上下文已经足够，都先展示草案并等待用户确认或修改。

### 2. 上下文不足时只补一个问题

如果当前上下文还不足以创建练习或笔记，只补问一个最关键的问题。

示例：

```text
你想围绕什么内容出题？可以直接贴一段材料给我。
```

```text
你想记下什么内容？可以直接贴正文，或告诉我要从上面的哪部分整理。
```

## 流炼练习创建流程

### 核心流程

```text
用户说“练一下”
  -> 检查 PRACMO_APIKEY
  -> 判断当前上下文是否足够
  -> 不足时先追问“要练什么”
  -> 足够时先展示练习标题 / 练习说明 / 默认题型 / AI 建议题量
  -> 用户可增删题型、修改题量(10-40)
  -> 用户确认
  -> AI 一次性生成完整 questions
  -> 调用 https://apis.zendong.com.cn/public/v1/flow/exercise
  -> 优先用 shareToken 生成 https://www.zendong.com.cn/s/flow/{shareToken}
  -> 若无 shareToken，再将 shareUrl 规范化后返回给用户
```

### 练习确认格式

```text
我准备创建这个流炼练习，请确认：

- 练习标题：Python 编程基础核心概念练习
- 练习说明：基于上面的内容，提炼出 Python 基础概念、常见误区和应用判断，帮助我较全面掌握核心信息。
- 题型：单选、多选、判断、问答（默认全选，可增删）
- 建议题量：24 题（可改，范围 10-40）

你可以直接回复：
- “确认”
- “去掉问答”
- “改成单选、判断，18题”
- “把练习标题改成 Python 入门速练，保留 24 题”
```

### 练习题目生成规则

- 题量必须等于最终确认的数量
- 只使用用户最终保留的题型
- 覆盖核心概念、关键事实、易错点、理解判断和必要应用
- 避免重复题、近义重复题、纯改写重复题
- `single_choice`：至少 3 个选项，且仅 1 个正确答案
- `multiple_choice`：至少 3 个选项，至少 2 个正确答案，且不能所有选项都正确
- `true_false`：固定 2 个选项，且仅 1 个正确答案
- `short_answer`：保留 1 个参考答案，且 `isCorrect: true`
- 每个 `options[]` 都必须带 `explanation`
- `options[].explanation` 不能只写“正确”或“错误”，要解释原因

### 流炼开放接口

始终调用生产开放接口：

```text
POST https://apis.zendong.com.cn/public/v1/flow/exercise
```

**流炼创建接口的请求体与成功响应 `data` 内字段一律使用驼峰命名**（例如 `userRequest`、`createShare`、`exerciseId`、`shareToken`）；`questions` 内题目结构沿用 `question` 模型已有驼峰字段（如 `questionType`、`questionContent`、`optionSeq`、`isCorrect`）。

请求头：

```text
X-API-Key: {PRACMO_APIKEY}
Content-Type: application/json
```

请求体参考：

```json
{
  "title": "Python 编程基础核心概念练习",
  "userRequest": "基于当前上下文提炼 Python 基础概念、常见误区和应用判断，帮助我较全面掌握核心信息。",
  "questions": [
    {
      "questionType": "single_choice",
      "questionContent": "Python 属于哪一类语言？",
      "options": [
        { "optionSeq": "A", "content": "编译型语言", "isCorrect": false, "explanation": "Python 通常不被归类为传统编译型语言。" },
        { "optionSeq": "B", "content": "解释型高级语言", "isCorrect": true, "explanation": "Python 通常被归类为解释型高级语言，强调开发效率和可读性。" },
        { "optionSeq": "C", "content": "汇编语言", "isCorrect": false, "explanation": "汇编语言更接近底层硬件，和 Python 的抽象层级完全不同。" }
      ]
    }
  ],
  "srcType": "api",
  "createShare": true
}
```

字段要求：

- `title`: 5-50 字
- `userRequest`: 应描述练习目标、覆盖重点、出题意图
- `questions`: 至少 10 题，最多 40 题
- `questionType`: `single_choice` / `multiple_choice` / `true_false` / `short_answer`
- `questionContent`: 题干正文
- `options[].optionSeq`: `A` / `B` / `C` / `D`...
- `options[].content`: 选项内容
- `options[].isCorrect`: 是否正确
- `options[].explanation`: 每个选项必填，必须分别说明该选项正确或错误的原因
- `srcType`: 固定传 `api`
- `createShare`: 固定传 `true`

### 流炼成功响应处理

如果创建成功，重点读取：

- `data.exerciseId`
- `data.exerciseTitle`
- `data.questionCount`
- `data.shareUrl`
- `data.shareToken`

面向用户展示时，遵循下面的链接规则：

1. 如果拿到了 `data.shareToken`，优先直接展示：
   `https://www.zendong.com.cn/s/flow/{shareToken}`
2. 如果没有 `shareToken`，但拿到了 `shareUrl`，则把其 host 规范化为：
   `https://www.zendong.com.cn`
3. 不要把 `apis.zendong.com.cn` 的 host 直接展示给用户。

返回给用户时，优先使用类似格式：

```text
流炼练习创建成功。

- 练习标题：Python 编程基础核心概念练习
- 题量：24 题
- 题型：单选、多选、判断、问答
- 练习链接：https://www.zendong.com.cn/s/flow/xxxx

打开分享链接后即可直接开始练习。
```

## 笔记创建流程

### 核心流程

```text
用户说“记一下”
  -> 检查 PRACMO_APIKEY
  -> 判断当前上下文是否足够
  -> 不足时先追问“要记什么”
  -> 足够时先整理笔记标题 / 笔记内容 / 默认笔记本建议
  -> 调用 GET /public/v1/note/notebooks 获取已有笔记本
  -> 告诉用户“当前有哪些笔记本”
  -> 用户选择已有笔记本，或输入一个新笔记本名称
  -> 若用户输入的是新名称，则先创建笔记本
  -> 再创建笔记
  -> 返回创建成功结果
```

### 笔记草案规则

- 默认优先沿用用户原始内容，不要擅自压缩到过短
- 如果用户没有明确给出标题，可根据内容生成一个简洁标题
- 默认按 Markdown 记录，即请求 JSON 中 `isMarkdown: true`
- 如果用户明确要求纯文本，再传 `isMarkdown: false`
- 创建前必须告诉用户当前已有的笔记本名称列表
- 当用户输入的笔记本名称与已有列表精确一致时，直接使用现有笔记本
- 当用户输入的是新名称时，先创建笔记本，再创建笔记

### 笔记确认格式

```text
我准备记录这条笔记，请确认：

- 笔记标题：开放 API 改造要点
- 笔记本：工作台
- 记录格式：Markdown
- 笔记内容：基于上面的讨论整理，包含开放接口、skill 改名和交互规则。

当前已有笔记本：
- 工作台
- 学习随记
- 产品灵感

你可以直接回复：
- “确认”
- “放到学习随记”
- “新建一个叫后端设计的笔记本”
- “标题改成 pracmo-create 改造清单”
```

### 笔记开放接口

始终调用生产开放接口：

```text
GET  https://apis.zendong.com.cn/public/v1/note/notebooks
POST https://apis.zendong.com.cn/public/v1/note/notebooks
POST https://apis.zendong.com.cn/public/v1/note/notes
```

**笔记相关接口的请求体与响应 `data` 内字段一律使用驼峰命名**（例如 `notebookId`、`noteId`、`isMarkdown`），不要使用下划线形式。

请求头：

```text
X-API-Key: {PRACMO_APIKEY}
Content-Type: application/json
```

#### 1. 获取笔记本列表

请求：

```text
GET /public/v1/note/notebooks
```

成功响应重点读取：

- `data[].notebookId`
- `data[].name`

返回给用户时，应整理成自然中文，例如：

```text
当前可用的笔记本有：
- 工作台
- 学习随记
- 产品灵感
```

#### 2. 创建笔记本

请求体：

```json
{
  "name": "后端设计"
}
```

成功响应重点读取：

- `data.notebookId`
- `data.name`

#### 3. 创建笔记

请求体：

```json
{
  "notebookId": "nb_xxx",
  "title": "开放 API 改造要点",
  "content": "这里是笔记正文",
  "isMarkdown": true
}
```

成功响应重点读取：

- `data.noteId`
- `data.notebookId`
- `data.title`

### 笔记成功响应处理

返回给用户时，优先使用类似格式：

```text
笔记记录成功。

- 笔记标题：开放 API 改造要点
- 笔记本：后端设计
- 记录格式：Markdown
```

如果本次先创建了新笔记本，再创建了笔记，可以额外说明：

```text
已先为你创建笔记本“后端设计”，并把笔记保存进去。
```

## 错误处理

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| `401` | API Key 缺失或无效 | 提示用户检查 `PRACMO_APIKEY`，必要时重新去 API Key 页面获取 |
| `400` | 请求体结构错误 | 检查字段名、字段类型、必填字段是否符合接口要求 |
| `422` | 练习题量或题目结构不符合要求 | 调整到 `10-40`，并检查题型结构与正确答案数量 |
| `500` | 服务端异常 | 告知用户稍后重试 |

## 注意事项

1. 默认交互不是“立刻创建”，而是“先展示草案，再确认创建”。
2. 练习默认四类题型全选；如果用户删除某类题型，最终题目里不要再出现该类。
3. 练习题量由 AI 先建议，但必须允许用户调整到 `10-40`。
4. 流炼练习必须一次性提交完整 `questions` 列表，不要拆成多次写入。
5. 记录笔记前，必须先提示当前已有的笔记本，不能跳过这一步。
6. 如果用户给了新的笔记本名称，则先创建笔记本，再创建笔记。
7. 用户侧不要直接暴露 `title`、`userRequest`、`shareUrl`、`notebookId` 这类内部字段名，统一改用自然中文表达。
8. 给用户展示的流炼分享链接 host 必须是 `https://www.zendong.com.cn`，推荐格式为 `https://www.zendong.com.cn/s/flow/{shareToken}`。
9. `PRACMO_APIKEY` 仅发送给璞奇后端，不发送到第三方服务，也不要要求用户把它贴进聊天记录。
