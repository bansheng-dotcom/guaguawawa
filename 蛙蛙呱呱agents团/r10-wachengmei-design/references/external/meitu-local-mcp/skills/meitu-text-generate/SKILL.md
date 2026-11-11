---
name: meitu-text-generate
description: Generate or rewrite text copy, scripts, storyboards, ad copy, product descriptions, social copy and prompt optimization via the meitu-local MCP `text-generate` tool. Use for writing/refining copy, slogans, product descriptions, social posts, article/script/storyboard writing, or prompt refinement; disable when full context is already supplied.
---

# 文案 / 脚本生成（text-generate）

调用独立 LLM 从零生成文本：营销文案、商品描述、社媒文案、视频脚本/分镜、法定读物、prompt 优化。

## 工具

调用 `meitu-local` MCP Server 的 **`text-generate`** 工具。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 上下文已有完整内容时禁用本工具（应直接产出成品）。
- 本地文件只用工作区内路径。

## 文案模式

- **小红书种草**：标题抓"人群+痛点/数字+结果/反常识/测评"；正文 痛点→共鸣→引入→卖点→软 CTA + 标签；第一人称闺蜜感、用具体数字。
- **电商文案 FAB+E**：Feature 功能 → Advantage 优势 → Benefit 利益 → Evidence 证据。
- **广告/营销**：先锁受众、场景、承诺、调性；标题优先"具体利益+记忆点"。
- **视频脚本/分镜**：按"钩子→知识点/卖点→案例→总结/CTA"编排；台词短句、钩子前置。
- **prompt 优化**：把空泛词改写为具体可见元素与可执行描述。

## 合规红线

禁止绝对化词（最/第一/100%/全网最低价）、国家级背书、功效承诺（美白祛斑/减肥/根治→改提亮肤色/推荐/长效）；数据须可复核。

## 输出规范

- 给出文案/脚本正文并说明采用模式；涉及数据标注需复核。