---
name: meitu-image-text-replace
description: Replace existing text on an image (A to B), either simple precise character replacement or complex text editing, via the meitu-local MCP `image-text-replace` tool. Use for changing/rewriting text, titles, prices, names, slogans, or decorative fonts on an image; not for removing text (use image-element-remove).
---

# 图上文字替换（image-text-replace）

把图片上已有的文字内容替换为新的文字（A → B），支持简单精准改字和复杂改字（花字/手写/多处/字符数变化）。

## 工具

调用 `meitu-local` MCP Server 的 **`image-text-replace`** 工具，传输入图路径、源词与目标词。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 使用规则

- 简单改字：`source_words`（原文）→ `target_words`（新文），如改价格/标题/名字/广告语。
- 装饰性/花字/手写多处替换：叠加 `prompt` 描述目标字体气质与位置。
- 仅做**替换**；若用户要"去除"文字走 `image-element-remove`。
- **事实护栏（k_visual_asset_fidelity_and_fact_guardrails）**：新文字内容、价格、数据、数字、品牌名必须**用户提供或已确认**，不得自行编造价格/销量/排行/编号等事实字段写入画面；不改用未核实的品牌/机构名称。
- 保留原文字的字体风格、位置、颜色与排版感觉，只换内容（除非用户要求同时改字型）。
- 迭代纪律：**最多 3 轮**；每轮复核替换内容准确性与文字风格一致性。

## 质检

- 简单替换：新文字内容准确无误、无漏字/串行；复杂/花字：字形风格还原、位置自然不遮挡主体。
- 涉及精确数字（价格、日期、编号）逐字核对与用户提供的原文一致。

## 工作流

1. 确认图上原文与目标新文。
2. 调用 `image-text-replace`，必要时补 prompt。
3. 复核替换后的文字内容、位置与风格是否达标。

## 输出规范

- 标注原文与新文、是否含装饰字体微调；多字/花字说明处理方式。