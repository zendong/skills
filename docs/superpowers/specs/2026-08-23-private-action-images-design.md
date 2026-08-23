# 私人跟练行动图片闭环设计

## 目标与边界

为 `pracmo-add-action` 增加跟练 image block 的创作、取证、审阅、压缩、私人上传和最终化能力。行动仍只能添加到 API Key 用户的存量 active 甲程，不创建甲程、不投稿、不公开。

Server 只在 Open API handler 增加最终 URL 约束，不修改共享 follow-plan 归一化逻辑，以免破坏 App 将非 HTTP 值作为私有对象 ID 渲染的兼容路径。

## 数据流

1. Agent 读取并选择存量甲程。
2. 对动作规范、健康安全、次数或时长等事实先读取可靠资料。
3. `action.authoring.json` 在 image block 的 `mediaUrl` 中使用 `asset://<assetId>`。
4. 独立 `action-images.json` 记录资源、事实声明、文字、数字、动作关系、使用位置和审阅结果。
5. 压缩脚本输出 `reviewed/assets/` 并删除旧 review。
6. Agent 实际查看压缩文件，与来源和整个跟练计划逐项比较。
7. reviewed 校验通过后，最终化脚本上传私人 `practiceAssets`、重新下载比较哈希，并替换占位符。
8. finalized 校验通过后调用私人行动创建接口。
9. Open API handler 再拒绝任何非 HTTPS image block。

## Manifest 与 block 映射

创作 block：

```json
{
  "blockType": "image",
  "mediaUrl": "asset://wall-pushup-start",
  "caption": "墙壁俯卧撑起始姿势"
}
```

Manifest 使用 `pracmo-action-images@v1`，每个 asset 记录：

- `assetId`、`localPath`、`altText`、`provenance`、`license`、`factuality`。
- 顶层 `resources[]`：唯一 `resourceId`、标题、发布者、HTTPS URL、检索时间、版本/发布日期和 `sourceType`。`sourceType` 只允许 `primary`、`official`、`standard`、`peer_reviewed`、`reputable_secondary`。
- `claims[]`：唯一 `claimId`、图片准确表达的完整事实文本和至少一个 `resourceIds`；引用必须存在。
- `expectedVisibleText[]`：逐字预期文本。
- `containsNumbers` 与 `expectedValues[]`：每项记录 label、精确 `displayValue`、单位和 `resourceIds`。
- `expectedRelations[]`：结构化记录主体、关系、客体和说明，用于姿态、关节、方向、步骤或器材关系。
- `usedBy`：`levelIndex` 与 `blockIndex`。
- review：来源、像素、文字、数字、动作逻辑、计划一致性、安全性、手机可读性和误导检查，以及绑定最终审阅文件的 `reviewedSha256`。

最终请求保留当前 `pracmo-track-action@v1` 合同，只将 `mediaUrl` 替换为 HTTPS URL，不携带 manifest 或 `assetId`。

## 校验和错误处理

本地 validator 负责：

- 行动 envelope、模式组合、日期和跟练结构的基础校验。
- image block 与 manifest 一一对应，不允许未声明或未使用 asset。
- `localPath` 只能是包内相对路径；拒绝绝对路径、`..`、越界 symlink，并要求 resolve 后仍位于 manifest 目录。
- 图片真实可读、格式合法、大小不超过 512 KiB；reviewed 校验和最终化都重新计算 SHA-256，并要求与 `review.reviewedSha256` 相同。
- 事实图片有来源；数值图片登记精确显示值。
- 所有 review flag 为真且 notes 非空。
- finalized 请求不含 `asset://`、`file://`、data URL 或非 HTTPS 图片。

任何失败都返回非零并阻止上传或创建。上传成功后若远端哈希不一致，不输出最终请求。

Open API handler 在业务 Create 前遍历 follow plan。比较前对 `contentMode` 和 `blockType` 使用 `strings.TrimSpace`，避免带空白的值绕过 handler 后又被共享 service 接受；当归一化值为 `follow_along`/`image` 时，要求 `mediaUrl` 是绝对 HTTPS URL，scheme 必须精确为 `https` 且 host 非空。共享 action service 仍接受 App 私有对象 ID。

## 幂等、续传与部分失败

- OSS object key 由 `practiceAssets` 前缀、`clientRequestId`、`assetId` 和 reviewed SHA-256 确定，不使用时间戳或随机数。相同图片重试覆盖/复用同一对象与 URL。
- 最终化成功后写出 `action-images.finalized.json` 上传台账和不可变的 `action.json`。创建超时或失败时必须重用同一份 `action.json`，不得重新最终化或改变 URL。
- 多图上传中断时，重跑会按确定性 key 复用已上传对象并继续；每个对象仍重新下载校验哈希。
- 未被行动引用的私人对象暂不主动删除，以保证失败恢复和避免误删；它们位于账号隔离的 request 目录，可由后续生命周期清理。该残留不允许被当作“创建成功”。

## 测试策略

- Skill RED/GREEN：缺少/未知/不可信来源、claim 缺少完整文本、审阅失败、reviewed SHA 不匹配、越界路径或 symlink、错误 block 映射、数值未登记、非法图片、占位符替换、最终非 HTTPS URL，以及最终输出不包含 manifest 字段或 `assetId`。
- Server RED/GREEN：Open API 拒绝 `asset://`、HTTP、无 host 的伪 HTTPS、私有对象 ID 和带空白的绕过形式，接受绝对 HTTPS；验证 service 未被非法请求调用。
- 兼容回归：共享 action service 仍接受 App 私有对象 ID；现有私人行动、私人练习 skill 测试；Server handler 定向测试及 action service 测试。

## 非目标

- 不实现视频或音频 block。
- 不新增数据库图片资产表。
- 不改变公共行动投稿或复制流程。
- 不自动声称视觉/动作正确；自动校验辅助，最终审阅必须实际完成。
