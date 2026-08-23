# 璞奇（Pracmo）Skills

本仓库提供两个面向个人使用的 Agent Skill。它们都只向用户已经在璞奇 App 中创建的存量甲程添加私人内容：

- `pracmo-add-exercise`：添加私人练习。
- `pracmo-add-action`：添加私人行动。

两个 skill 都不会创建甲程，也不会投稿或创建公开行动。

## 安装

```bash
npx skills add https://github.com/zendong/skills --skill pracmo-add-exercise
npx skills add https://github.com/zendong/skills --skill pracmo-add-action
```

## 使用前准备

在本地配置 API Key；不要把 Key 粘贴到聊天或提交到仓库：

```bash
export PRACMO_APIKEY="你的_API_Key"
```

获取入口：`https://www.zendong.com.cn/app/api-key`

每次创建前，Agent 都会读取 API Key 所属用户的 active 甲程。若没有可用甲程，会提示：

```text
没有找到可用的存量甲程。请先到璞奇手机端创建甲程，创建后告诉我，我就能读取到并继续添加练习或行动。
```

## 使用示例

- “把这段内容做成练习，加到我的线性代数甲程。”
- “给雅思甲程补一组错题练习。”
- “在跑步甲程里创建一个每周三次的行动。”
- “给阅读甲程加一个小璞准备的每日轻阅读行动。”

当多个甲程都可能匹配时，Agent 会先让用户选择，不会自行猜测。详细约束见各目录下的 `SKILL.md`。
