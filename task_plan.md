# Task Plan: 私人跟练行动图片闭环

## 需求链接

- `requirements/2026-08-23-private-action-images-requirements.md`
- `requirements/2026-08-23-private-action-images-dependencies.md`
- `docs/superpowers/specs/2026-08-23-private-action-images-design.md`

## 任务列表

### Task 1: 规格落盘与审阅
- 目标：固化已批准设计并完成独立审阅。
- 验收标准：规格审阅无阻塞问题。
- **Status:** complete

### Task 2: Skill 测试先行
- 依赖：Task 1
- 目标：为 action 图片合同、审阅门禁和最终化编写失败测试。
- 验收标准：测试因缺少实现按预期失败。
- **Status:** complete

### Task 3: Skill 图片闭环实现
- 依赖：Task 2
- 目标：实现文档、validator、压缩、OSS 上传和最终化。
- 验收标准：Skill 测试通过。
- **Status:** complete

### Task 4: Server Open API 兜底
- 依赖：Task 1
- 目标：测试先行增加 handler 专属 HTTPS 校验。
- 验收标准：非法 URL 被拒绝，HTTPS 与 App 共享逻辑不回归。
- **Status:** complete

### Task 5: 回归与交付
- 依赖：Task 3、Task 4
- 目标：执行两个仓库的定向验证并审阅差异。
- 验收标准：所有相关测试、静态检查和 diff 检查通过。
- **Status:** complete

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| 一次组合 apply_patch 因 openai.yaml 原文不匹配而未应用 | 1 | 拆分补丁并按实际文件内容更新 |
