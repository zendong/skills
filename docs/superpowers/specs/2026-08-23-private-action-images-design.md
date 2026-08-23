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
- `claims[].resourceIds`。
- `expectedVisibleText`、`containsNumbers`、`expectedValues`。
- `expectedRelations`：姿态、关节、方向、步骤或器材关系。
- `usedBy`：`levelIndex` 与 `blockIndex`。
- review：来源、像素、文字、数字、动作逻辑、计划一致性、安全性、手机可读性和误导检查。

最终请求保留当前 `pracmo-track-action@v1` 合同，只将 `mediaUrl` 替换为 HTTPS URL，不携带 manifest 或 `assetId`。

## 校验和错误处理

本地 validator 负责：

- 行动 envelope、模式组合、日期和跟练结构的基础校验。
- image block 与 manifest 一一对应，不允许未声明或未使用 asset。
- 图片真实可读、格式合法、大小不超过 512 KiB。
- 事实图片有来源；数值图片登记精确显示值。
- 所有 review flag 为真且 notes 非空。
- finalized 请求不含 `asset://`、`file://`、data URL 或非 HTTPS 图片。

任何失败都返回非零并阻止上传或创建。上传成功后若远端哈希不一致，不输出最终请求。

Open API handler 在业务 Create 前遍历 follow plan；仅当 `contentMode=follow_along` 且 block 为 image 时要求 `mediaUrl` 是合法 HTTPS URL。共享 action service 仍接受 App 私有对象 ID。

## 测试策略

- Skill RED/GREEN：缺少来源、审阅失败、错误 block 映射、数值未登记、非法图片、占位符替换、最终非 HTTPS URL。
- Server RED/GREEN：Open API 拒绝 `asset://`、HTTP 和私有对象 ID，接受 HTTPS；验证 service 未被非法请求调用。
- 回归：现有私人行动、私人练习 skill 测试；Server handler 定向测试及 action service 测试。

## 非目标

- 不实现视频或音频 block。
- 不新增数据库图片资产表。
- 不改变公共行动投稿或复制流程。
- 不自动声称视觉/动作正确；自动校验辅助，最终审阅必须实际完成。
