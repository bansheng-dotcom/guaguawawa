---
name: meitu-image-poster-generate
description: Generate posters, marketing/campaign images, layouts with typography, covers and infographic-type visuals via the meitu-local MCP `image-poster-generate` tool, with optional reference styling or content rewrite. Use for poster design, campaign/activity/holiday artwork, platform covers, info posters and detail-page visuals; not for feed ad creative.
---

# 海报 / 营销图 / 封面（image-poster-generate）

按主题生成带版式的成品海报、场景营销图、活动/节点图、平台封面与信息型海报，支持参考图风格洗稿或从零规划。

## 工具

调用 `meitu-local` MCP Server 的 **`image-poster-generate`** 工具。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 适用范围与边界

- **不用于投流广告**：广告视觉走 `image-edit` / `text-to-image`（绑 nougat）；`image-poster-generate` 仅用于活动海报、通知、详情页、站内信息型海报、封面等。
- 有参考图时做风格模仿/重构；无参考图时从零创意规划。
- 海报中出现的文字内容、价格、活动节点等必须由用户提供或已确认，不擅自编造。

## Prompt 编写

- 说明产物类型（封面/海报/营销图/信息图）、版式（上字下图/居中/左右）、主体、色调、字体气质。
- 像素宽高须为 16 的倍数；同一平台同一批锁同一比例。
- 场景营销图套图（主题陈列/主体互动/节日节点）：先定统一风格前缀，逐张复用防漂移。
- **事实护栏（k_visual_asset_fidelity_and_fact_guardrails）**：海报中的文字、价格、活动节点、编号、地址、日期**必须用户提供或已确认**，不自行编造真实信息；不写入平台 Logo、App UI、二维码、水印、版权标识（除非用户明确要求且合规）。
- 精确色值（hex/Pantone）：默认不写进 prompt 或画面文字；用户明确要品牌标准色时才保留，可先转描述型方向（如"冷调雾蓝主色 + 银白点缀"）。
- 参考图风格洗稿只提取版式/风格/视觉 DNA，不复制参考图中无关主体、文字、Logo、水印或事实信息。

## 质检与交付

- P0：主体无畸变、文字完整可读、版式层级清晰；P1：留白与安全区合适、色彩统一、无错误/遮挡文字。
- 交付前确认可交付 `image_url`；套图多张逐张确认缺图不报完成。

## 平台尺寸速查

| 场景 | 比例 | 备注 |
|---|---|---|
| 小红书封面/轮播 | 3:4 | 文字占比≤20% |
| 公众号头图 | 2.35:1 | — |
| 电商主图 | 1:1 | 白底产品居中 |
| 方形/专辑 | 1:1 | — |

## 输出规范

- 说明海报主题、版式与调用的 `image-poster-generate`。
- 套图/多张时标注统一风格前缀与覆盖平台尺寸。