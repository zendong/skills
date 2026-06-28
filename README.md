# 璞奇（Pracmo）Skills

本仓库是璞奇对外发布的 Agent Skills 仓库。目前只保留最新的 `pracmo-create`：

- 路径：`skills/pracmo-create/`
- 作用：把当前对话、资料、Markdown、术语清单或学习目标创建为璞奇甲程练习。
- 能力：支持新建甲程 + 首个完整练习，或向已有甲程队尾追加一组完整练习。

## 安装

```bash
npx skills add https://github.com/zendong/skills --skill pracmo-create
```

## 使用前准备

`pracmo-create` 通过璞奇开放 API 创建甲程练习。使用前需要配置 API Key：

```bash
export PRACMO_APIKEY="你的_API_Key"
```

API Key 获取入口：

```text
https://www.zendong.com.cn/app/api-key
```

不要把 API Key 粘贴到聊天里，也不要提交到仓库。

## 当前 Skill

### `pracmo-create`

适用表达：

- “练一下”
- “把这段内容做成练习”
- “围绕这个建个甲程练一下”
- “根据这段内容出题”
- “创建甲程和第一个练习”
- “给已有甲程再补一组”

核心流程：

1. 检查 `PRACMO_APIKEY`。
2. 判断是新建甲程还是复用已有甲程。
3. 提炼稳定知识点和可测命题。
4. 由 Agent 生成完整题目、选项、答案、解析和 Bloom 层级。
5. 通过 `scripts/pracmo-open-api.sh` 创建或追加甲程练习。
6. 使用本地 `cache/` 记录来源到甲程映射和创建请求台账，辅助后续补练与超时恢复。

详细规则见：

```text
skills/pracmo-create/SKILL.md
```

## 目录结构

```text
skills/
  pracmo-create/
    SKILL.md
    cache/
    scripts/
```

`cache/` 下的运行缓存不会提交到仓库。

## 反馈

如果你在使用 `pracmo-create` 时遇到问题，欢迎通过 Issue 反馈：

- 你使用的 Agent / 运行环境
- 触发 skill 的原始请求
- 是否已配置 `PRACMO_APIKEY`
- 失败时的错误信息或终端输出

本仓库会随璞奇开放 API 和 Agent 使用方式持续更新。
