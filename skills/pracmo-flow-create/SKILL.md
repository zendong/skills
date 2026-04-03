---
name: pracmo-flow-create
description: "当用户说“练一下”“把这段内容做成练习”“帮我生成流炼练习”之类的话时，必须使用这个 skill。它会先检查环境变量 `PRACMO_APIKEY`，若缺失则立即提示用户去 https://www.zendong.com.cn/app/api-key 获取并配置；若已配置，则把当前上下文整理成流炼练习草案，让用户确认题型与题量后，一次性调用 `https://apis.zendong.com.cn/public/open/v1/flow/exercise` 创建练习并返回分享链接。"
---

# Pracmo Flow Create

## 用途

本 skill 用于把当前对话里的材料提炼成可直接练习的流炼练习，并返回接口实际生成的分享链接。

优先在以下表达出现时触发：

- “练一下”
- “把这个做成练习”
- “帮我生成一个流炼练习”
- “把上面的内容整理成题目给我练”
- “根据这段内容出题”

## 先做认证检查

在任何内容整理、出题或接口调用前，先检查当前运行环境是否可读取 `PRACMO_APIKEY`。

如果没有检测到 `PRACMO_APIKEY`，必须立刻停止，不要继续整理草案，也不要假装已经创建成功。直接提示用户去获取并配置 API Key，推荐使用下面这段话：

```text
未检测到 PRACMO_APIKEY，暂时不能创建流炼练习。

请先访问 https://www.zendong.com.cn/app/api-key 获取你的 API Key，
然后在本地环境中设置：

export PRACMO_APIKEY="你的_API_Key"

设置完成后，再回来对我说“练一下”或“确认创建”。
```

补充要求：

- 可以引导用户去 API Key 页面，但不要要求用户把 API Key 直接贴到聊天里。
- 如果用户说“不知道怎么设置环境变量”，再根据当前终端或操作系统补充更具体的设置方式。
- 如果已经知道当前 shell 是 `zsh` 或 `bash`，优先给 `export PRACMO_APIKEY="..."` 这种可直接执行的示例。

## 核心流程

```text
用户说“练一下”
  -> 检查 PRACMO_APIKEY
  -> 没有则停止，并引导去 https://www.zendong.com.cn/app/api-key 获取
  -> 有则判断当前上下文是否足够
  -> 不足时先追问“要练什么”
  -> 足够时先展示练习标题 / 练习说明 / 默认题型 / AI 建议题量
  -> 用户可增删题型、修改题量(10-40)
  -> 用户确认
  -> AI 一次性生成完整 questions
  -> 调用 https://apis.zendong.com.cn/public/open/v1/flow/exercise
  -> 优先用 share_token 生成 https://www.zendong.com.cn/s/flow/{share_token}
  -> 若无 share_token，再将 share_url 规范化后返回给用户
```

## 行为规则

### 0. 用户可见文案要自然

对用户说话时，优先使用自然中文，不要直接把内部字段名或接口术语抛给用户。

用户侧推荐表达：

- `title` -> “练习标题”
- `userRequest` / `user_request` -> “练习说明”
- `question_count` -> “题量”或“共多少题”
- `share_url` -> “练习链接”或“分享链接”

内部执行时，仍然必须使用真实字段名、真实请求结构和真实接口地址。

### 1. 先判断上下文是否足够

如果当前对话已经包含足够材料，例如：

- 用户刚贴了一段文章、笔记、总结、方案
- 用户刚讨论完一个知识主题
- 用户明确说“把上面的内容给我练一下”

则直接进入“确认创建信息”步骤。

如果上下文不足，先只问一个聚焦问题，例如：

```text
要练什么内容？你可以直接贴一段材料，或告诉我要围绕哪个主题出题。
```

### 2. 默认先展示，不要直接创建

当上下文足够时，必须先展示以下信息，等待用户确认或修改：

- 练习标题
- 练习说明
- 默认题型：单选、多选、判断、问答
- AI 建议题量：根据内容密度、概念数量、易错点数量判断，范围 `10-40`

建议使用类似下面的确认格式：

```text
我准备创建这个流炼练习，请确认：

- 练习标题：Python 编程基础核心概念练习
- 练习说明：基于上面的内容，提炼出 Python 基础概念、常见误区和应用判断，帮助我较全面掌握核心信息。
- 题型: 单选、多选、判断、问答（默认全选，可增删）
- 建议题量: 24 题（可改，范围 10-40）

你可以直接回复：
- “确认”
- “去掉问答”
- “改成单选、判断，18题”
- “把练习标题改成 Python 入门速练，保留 24 题”
```

### 3. 用户可修改的范围

用户可以修改：

- 练习标题
- 练习说明
- 题型集合：单选 / 多选 / 判断 / 问答，可增删
- 题量：`10-40`

不要让用户调整底层 JSON 字段名或接口结构。

### 4. 用户确认后再生成完整题目

确认后，由 AI 一次性生成完整 `questions` 列表，并立即调用开放接口。

不要先创建空练习。
不要拆成多次补题请求。
不要调用旧的“先建练习再慢慢补题”的流程。

## 题目生成规则

### 总体要求

- 题量必须等于最终确认的数量
- 只使用用户最终保留的题型
- 覆盖核心概念、关键事实、易错点、理解判断和必要应用
- 避免重复题、近义重复题、纯改写重复题
- 题目应服务于“相对全面掌握核心信息”，不是机械凑数

### 题型约束

- `single_choice`
  - 至少 3 个选项
  - 有且仅有 1 个正确答案
  - 每个选项都必须提供 `options[].explanation`，分别说明为什么正确或为什么错误
- `multiple_choice`
  - 至少 3 个选项
  - 至少 2 个正确答案
  - 不能所有选项都正确
  - 每个选项都必须提供 `options[].explanation`，正确项说明成立原因，错误项说明错误点或易混点
- `true_false`
  - 固定 2 个选项
  - 中文语境下优先使用“正确”/“错误”
  - 有且仅有 1 个正确答案
  - 两个选项都必须提供 `options[].explanation`，分别解释为什么“正确”或“错误”
- `short_answer`
  - `options` 中保留 1 个参考答案
  - 该参考答案设置 `isCorrect: true`
  - 参考答案必须提供 `options[].explanation`，说明评分依据、关键词或标准答案要点

### 质量检查

生成完成后必须自审：

1. 每题是否能明确判定对错
2. 题型是否符合对应结构约束
3. 每个选项是否都写入了 `options[].explanation`，并真正帮助理解
4. 题量与覆盖面是否匹配用户目标
5. 是否只使用了用户确认后的题型

## 开放接口

始终调用生产开放接口：

```text
POST https://apis.zendong.com.cn/public/open/v1/flow/exercise
```

请求头：

```text
X-API-Key: {PRACMO_APIKEY}
Content-Type: application/json
```

请求体必须使用服务端当前真实接受的字段名，不要自造 snake_case 变体，也不要自行扩展字段。

本 skill 额外约束：

- 每个 `options[]` 都必须带 `explanation`
- `options[].explanation` 不能只写“正确”或“错误”，要解释原因

参考格式：

```json
{
  "title": "Python 编程基础核心概念练习",
  "user_request": "基于当前上下文提炼 Python 基础概念、常见误区和应用判断，帮助我较全面掌握核心信息。",
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
  "src_type": "api",
  "create_share": true
}
```

### 字段要求

- `title`: 5-50 字
- `user_request`: 应描述练习目标、覆盖重点、出题意图
- `questions`: 至少 10 题，最多 40 题
- `questionType`: `single_choice` / `multiple_choice` / `true_false` / `short_answer`
- `questionContent`: 题干正文
- `options[].optionSeq`: `A` / `B` / `C` / `D`...
- `options[].content`: 选项内容
- `options[].isCorrect`: 是否正确
- `options[].explanation`: 每个选项必填，必须分别说明该选项正确或错误的原因
- `src_type`: 固定传 `api`
- `create_share`: 固定传 `true`

## 成功响应处理

如果创建成功，重点读取：

- `data.exercise_id`
- `data.exercise_title`
- `data.question_count`
- `data.share_url`
- `data.share_token`

面向用户展示时，遵循下面的链接规则：

1. 如果拿到了 `data.share_token`，优先直接展示：
   `https://www.zendong.com.cn/s/flow/{share_token}`
2. 如果没有 `share_token`，但拿到了 `share_url`，则把其 host 规范化为：
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

内部可以读取接口返回的 `share_url` 和 `share_token`，但给用户展示时，链接必须规范成：
`https://www.zendong.com.cn/s/flow/{share_token}`。

## 错误处理

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| `401` | API Key 缺失或无效 | 提示用户检查 `PRACMO_APIKEY`，必要时重新去 API Key 页面获取 |
| `400` | 请求体结构错误 | 检查字段名、字段类型、必填字段是否符合接口要求 |
| `422` | 题量或题目结构不符合要求 | 调整到 `10-40`，并检查题型结构与正确答案数量 |
| `500` | 服务端异常 | 告知用户稍后重试 |

## 注意事项

1. 默认交互不是“立刻创建”，而是“先展示草案，再确认创建”。
2. 默认四类题型全选；如果用户删除某类题型，最终题目里不要再出现该类。
3. 题量由 AI 先建议，但必须允许用户调整到 `10-40`。
4. 必须一次性提交完整 `questions` 列表，不要拆成多次写入。
5. 用户侧不要直接暴露 `title`、`userRequest`、`share_url` 这类英文属性名，统一改用自然中文表达。
6. 给用户展示的分享链接 host 必须是 `https://www.zendong.com.cn`，推荐格式为 `https://www.zendong.com.cn/s/flow/{share_token}`。
7. `PRACMO_APIKEY` 仅发送给璞奇后端，不发送到第三方服务，也不要要求用户把它贴进聊天记录。
