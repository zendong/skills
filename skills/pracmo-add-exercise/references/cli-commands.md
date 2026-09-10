# pracmocli 命令速查

所有业务命令 stdout 输出 JSON（成功时 `exit 0`）；错误信息在 stderr，退出码见下表。

> **参数顺序**：推荐把 flag 写在位置参数**之前**（`pracmocli images validate --stage reviewed <file>`）。
> CLI 已兼容两种顺序，但这一形式最不容易出错，也便于与示例逐字比对。

## 命令

| 命令 | 用途 | 必填 |
|------|------|------|
| `pracmocli auth login` | 签发绑定码并打印授权 URL（前后空白、无引号，10 秒内） | 无 |
| `pracmocli auth status` | 登录态检查（无副作用、幂等）；已登录时输出含 `"logged in"` | 无 |
| `pracmocli auth logout` | 撤销绑定并清理本地凭证（幂等，未登录也返回 0） | 无 |
| `pracmocli tracks list [keyword]` | 列出 active 甲程（`state=active&pageSize=100`） | 无 |
| `pracmocli collections list <trackId>` | 列出练习册 | trackId |
| `pracmocli collections create <trackId> <file>` | 新建练习册（JSON：`name`/`clientRequestId`/可选 `description`） | trackId + file |
| `pracmocli exercises add <trackId> <file>` | 创建成品练习 → `POST /open/v1/learning-tracks/:id/exercises` | trackId + file |
| `pracmocli exercises image-replace <trackId> <exerciseId> <questionId> <file>` | 原位替换题目图片（`PATCH …/image-url`） | 3 个 ID + file |
| `pracmocli actions add <trackId> <file>` | 创建私人行动 → `POST /open/v1/learning-tracks/:id/actions` | trackId + file |
| `pracmocli validate exercise\|action\|collection\|replace-image <file>` | 提交前结构校验（`--manifest`/`--stage` 见下） | file |
| `pracmocli images compress --manifest <m> [-o out] <authoring.json>` | 压缩图片到 ≤512 KiB，清空 `review` 待重新审阅 | manifest + authoring |
| `pracmocli images validate --stage reviewed\|finalized [--manifest <m>] [--type exercise\|action] <file>` | 硬门禁校验 | file（reviewed 阶段还需 manifest） |
| `pracmocli images finalize --manifest <m> -o <out> [--final-manifest <f>] [--type exercise\|action] <authoring.json>` | OSS 直传 + 哈希回读 + `asset://` 替换为 HTTPS | manifest + out + authoring |
| `pracmocli doctor` | 环境自检（变量/凭证/**连通性**，只读） | 无 |
| `pracmocli version` | 打印版本 | 无 |

**写命令通用参数**：`--dry-run` —— 只做本地 JSON 结构校验，不发出任何请求。

**校验阶段的语义**（务必确认输出中的 `stage` 与预期一致）：

| 阶段 | 用途 | 是否要求 `collectionId` |
|------|------|------------------------|
| `reviewed` | 图片审阅后、上传前 | 否 |
| `finalized` | 最终请求（含 `asset://` 已替换） | **是** |

## 退出码

| 码 | 含义 | 处理 |
|----|------|------|
| 0 | 成功 | 解析 stdout JSON |
| 1 | 参数/用法错误 | 查看 `pracmocli help` |
| 2 | 未登录/凭证失效 | 引导 `pracmocli auth login` |
| 3 | 业务错误（后端 4xx 非冲突） | 按 stderr 错误信息恢复 |
| 4 | 网络/超时 | **相同 `clientRequestId` 与相同 JSON** 重试 |
| 5 | 冲突（409 幂等冲突） | 内容未改核对结果；内容已改则换新 ID |
| 6 | 本地门禁未过（校验失败） | 修图/题干后重新校验，**不得创建** |

## 全局参数

| 参数 | 说明 |
|------|------|
| `--base <url>` | 后端 Open API 地址（优先级最高） |
| `--env <name>` | 预设档 `prod` / `pre` / `global` / `local` |

优先级：命令行参数 > 环境变量 > 预设档 > 内置默认值。

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `PRACMO_OPEN_API_BASE` | `https://apis.pracmo.com/open/v1` | 后端地址 |
| `PRACMO_ENV` | `prod` | 预设档：`prod`（国内生产）/ `pre`（国内预发）/ `global`（海外生产）/ `local` |
| `PRACMO_API_KEY` | 空 | API Key（优先于凭据文件） |
| `PRACMO_CREDENTIALS_DIR` | `~/.pracmo` | 凭证目录（0600，跨重启有效，按环境隔离为 `credentials.<env>.json`） |
| `PRACMO_HTTP_TIMEOUT_SECONDS` | 30 | HTTP 超时 |
| `PRACMO_LOG_LEVEL` | `info` | 日志级别 `debug`/`info`/`warn`/`error` |
| `PRACMO_OSS_ENDPOINT` / `PRACMO_OSS_BUCKET` | 取自后端 STS | 仅联调覆盖（如本地 minio） |

> `PRACMO_ENV` 的内置默认值是 `prod`（国内生产）。本 skill 的每条命令都显式传 `--env prod`，
> 因此即使你机器上设过别的 `PRACMO_ENV`，也不会走错区域。

## 常见返回形态

```json
{ "success": true, "data": { "trackId": "track_xxx", "title": "线性代数" }, "code": "SUCCESS", "message": "success" }
```

> 注意：后端对**业务错误**也返回 HTTP 200，靠 `success:false` + `code` 表达失败
> （例如未知/过期的绑定码返回 `NOT_FOUND`）。CLI 已按 `success` 与 `code` 正确分类，
> 直接读退出码即可，不要只看 HTTP 状态。
