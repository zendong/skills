# 练成 / Pracmo Skills

面向个人使用的 Agent Skill。它们只向用户**已经存在**的甲程添加私人内容：

| Skill | 适用区域 | 语言 | 后端 |
|---|---|---|---|
| `pracmo-add-exercise` | 国内 | 中文 | `apis.pracmo.com` |
| `pracmo-add-action` | 国内 | 中文 | `apis.pracmo.com` |
| `pracmo-global-add-exercise` | 海外 | English | `apis.pracmo.app` |
| `pracmo-global-add-action` | 海外 | English | `apis.pracmo.app` |

四个 skill 都**不会创建甲程**，也不会投稿或创建公开行动。

## 为什么分两套

国内与海外是**两套完整隔离的部署**：不同后端、不同 App、账号不互通。**一个区域的 API Key
在另一个区域无效**。所以每个 skill 都写清自己的后端与 App 名称，并且每条命令都显式带区域参数：

```bash
pracmocli --env prod   ...   # 国内
pracmocli --env global ...   # 海外
```

显式传参而不是依赖 `PRACMO_ENV` 环境变量，是因为用户完全可能两个区域的账号都有；
靠环境变量会互相覆盖，而显式参数无状态、无冲突。

选哪一套只看用户是哪个区域的账号。**如果用户没有说明，问清楚再动手 —— 不要猜。**

## 安装

```bash
# 国内
npx skills add https://github.com/zendong/skills --skill pracmo-add-exercise
npx skills add https://github.com/zendong/skills --skill pracmo-add-action

# 海外
npx skills add https://github.com/zendong/skills --skill pracmo-global-add-exercise
npx skills add https://github.com/zendong/skills --skill pracmo-global-add-action
```

四个 skill 都通过 `pracmocli` 完成认证、读取甲程/练习册、创建内容与图片流水线
（压缩、校验、OSS 直传、最终化）。**无需 Python / Pillow / oss2**：全部能力已内置到 CLI。

```bash
npm install -g @pracmo/pracmo-cli
pracmocli version
```

## 使用前准备

在本地配置 API Key；**不要把 Key 粘贴到聊天或提交到仓库**：

```bash
export PRACMO_API_KEY="你的_API_Key"     # 国内账号的 Key
```

也可以不设环境变量，改用绑定式登录（更适合交给 Agent 平台托管）：

```bash
pracmocli --env prod auth login      # 国内
pracmocli --env global auth login    # 海外
```

命令会打印对应区域的绑定 URL，在浏览器登录后确认绑定码即可。凭证按区域隔离存放
（`~/.pracmo/credentials.<env>.json`），因此**同一台机器可以同时登录两个区域**。

账号页：国内 `https://www.pracmo.com/app/api-key` ／ 海外 `https://www.pracmo.app/app/api-key`

若没有可用甲程，Agent 会提示：

```text
没有找到可用的存量甲程。请先到练成手机端创建甲程，创建后告诉我，我就能读取到并继续添加练习或行动。
```

（海外 skill 用对应的英文提示。）

## 使用示例

- “把这段内容做成练习，加到我的线性代数甲程。”（国内）
- “Turn this into practice questions in my IELTS track.”（海外）
- “在跑步甲程里创建一个每周三次的行动。”
- “给阅读甲程加一个小璞准备的每日轻阅读行动。”

当多个甲程都可能匹配时，Agent 会先让用户选择，不会自行猜测。详细约束见各目录下的 `SKILL.md`，
命令与退出码速查见 `references/cli-commands.md`。

## 测试

```bash
python3 tests/test_skill_contract.py
```

一份参数化测试覆盖全部四个 skill，两条防线：

1. **区域隔离** —— 国内 skill 不得出现海外域名/区域参数，反之亦然
   （两套账号不互通，走错后端只会得到一个难懂的鉴权失败）；
2. **跨区域结构对等** —— 中英两版必须章节数、表格行数、代码块数、用到的 `pracmocli`
   子命令集合、关键数字完全一致。文字可以不同，**结构不许不同**。

> 语言不同导致两套无法逐字比对，所以第 2 条是能拿到的最强一致性保证。
> 修改任何一侧时，记得同步另一侧并跑这个测试。

行为测试（图片校验/最终化、路径逃逸、审阅门禁等）随实现放在 CLI 仓库：
`private-skills/cli/pracmocli/internal/{images,contract,connector}`。
