# 私人跟练行动图片闭环依赖

## 内部依赖

| 模块 | 依赖说明 | 状态 |
|---|---|---|
| Shixizhi Server Open Action API | 已接收 `followPlan` | ready |
| Follow content block | 已支持 `blockType=image` 与 `mediaUrl` | ready |
| OSS Open API | 已提供 `practiceAssets` 前缀与 STS | ready |
| Wancai | 已支持网络 URL 和私有对象 ID 图片渲染 | ready |

## 外部依赖

| 依赖项 | 版本要求 | 用途 | 状态 |
|---|---|---|---|
| Pillow | 可读取 PNG/JPEG/WebP | 图片验证与压缩 | ready |
| oss2 | 当前兼容版本 | 使用 STS 上传 OSS | runtime-required |

## 前置条件

- [x] 用户已批准 skill 与 Open API handler 同时改造。
- [x] Server 私人行动与 App 图片数据链路已核实。

## 风险项

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 全局收紧 mediaUrl 会破坏 App 私有对象 ID | App 回归 | 只在 Open API handler 校验 HTTPS |
| 压缩改变文字或动作细节 | 教学错误 | 压缩后清空审阅并重新逐图检查 |
| 远端上传内容与审阅文件不一致 | 展示错误 | 下载远端文件并比较 SHA-256 |
| Agent 虚填审阅字段 | 错误内容进入行动 | Skill 明确要求实际打开图片并记录具体 notes |
