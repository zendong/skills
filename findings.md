# Findings

- Server `FollowContentBlockInput` 已支持 `blockType=image`、`mediaUrl` 和 `caption`。
- 共享 `normalizeFollowPlan` 只检查 mediaUrl 非空和长度；App 允许非 HTTP 值作为私有对象 ID。
- Open Track Action API 直接把 follow plan 交给 action service，适合在 handler 边界增加 HTTPS 专属校验。
- OSS Open API 已返回 `practiceAssets` 私人前缀和 STS。
- 当前 `pracmo-add-action` 没有图片 manifest、压缩、上传、最终化或严格审阅流程。
- 已删除的公共行动 skill 曾用 `assetId` 映射 content asset，但当前私人 action API 不接收资产清单，因此新流程应在本地 manifest 中映射并在最终请求中仅保留 HTTPS mediaUrl。
- 规格审阅要求 handler 比较前 trim 字段、审阅绑定 SHA-256、拒绝越界路径、使用确定性 OSS key、补全 resources/claims 合同，并覆盖 App 私有对象兼容性。
