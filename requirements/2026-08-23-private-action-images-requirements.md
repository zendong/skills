# 私人跟练行动图片闭环需求

## 概述

让 `pracmo-add-action` 能在用户存量甲程中创建包含可靠图片 block 的私人跟练行动，并在创建前完成来源、内容、安全性和上传完整性校验。

## 详细需求

### 事实取证与图片审阅

- 事实性、动作规范和健康安全内容优先读取一手、官方、标准或专业机构资料，不依赖模型参数记忆。
- 每张图片记录来源、许可、事实声明、可见文字、数字、动作/步骤关系及所在 content block。
- 校验动作姿态、关节位置、运动方向、步骤顺序、次数/时长、进阶条件、停止条件和安全边界。
- 图片、caption、文本 block、练阶目标与进阶标准必须一致；任一检查失败时禁止创建。

### 素材处理与创建

- 创作阶段 image block 使用 `asset://<assetId>` 占位。
- 压缩后的最终待上传图片不超过 512 KiB，仅允许 PNG、JPEG、WebP；压缩后旧审阅失效。
- 复核通过后上传到 API Key 用户的私人 `practiceAssets` 前缀，重新下载并核对 SHA-256。
- 审阅结果必须记录 reviewed SHA-256；校验和上传时都要求本地文件字节仍与审阅值一致。
- object key 由请求 ID、asset ID 和 reviewed SHA-256 确定，失败重试复用相同 URL 和最终 JSON。
- 最终请求仅包含 HTTPS `mediaUrl`，不得包含本地路径、占位符或内部 manifest。

### Server 兜底

- `POST /open/v1/learning-tracks/:trackId/actions` 对 follow-along image block 只接受带 host 的绝对 HTTPS URL，并阻止空白字符绕过。
- 不收紧共享 follow-plan 校验，保留 App 使用私有对象 ID 的现有兼容性。

## 验收标准

- [ ] Skill 文档包含完整图片工作流和严格安全审阅清单。
- [ ] 校验脚本拒绝未取证、未审阅、错误使用位置、超限或非法图片。
- [ ] 最终化脚本上传私人素材、替换占位符并验证远端哈希。
- [ ] Open API handler 拒绝非 HTTPS image block，普通 App 路径保持不变。
- [ ] 本地图片路径不能越过包目录，最终输出不泄漏 manifest 字段或 `assetId`。
- [ ] Skill 与 Server 定向测试通过。

## 约束条件

- 不创建甲程，不创建公开行动。
- 不修改公共行动投稿合同。
- 不把 `assetId` 或审阅 manifest 发送给当前私人行动 Open API。
