---
name: meitu-text-to-image
description: Generate a brand-new image from a text prompt with no source image, using the meitu-local MCP `text-to-image` tool. Use when the user asks to create/generate/draw an image from scratch, a concept/promo/cover/campaign image, or mentions multi-image reference fusion with no existing base image.
---

# 文生图（text-to-image）

从一段文字描述从零生成一张全新图片。仅在**完全没有输入底图**时使用。

## 工具

调用 `meitu-local` MCP Server 的 **`text-to-image`** 工具。

## 环境与前置

- 若 `meitu_auth_status` 显示未连接，先引导用户在 TRAE 连接器授权美图账号，绝不索取 AK/SK 或 token。
- 预期工具缺失时用 `meitu_registry_status` 检查，必要时 `meitu_registry_refresh`。
- 本地文件只用项目工作区内路径；交付时给出媒体 URL / 任务 ID；不触发充值/购买/账户操作。

## 余额不足与后续充值问答

- 余额不足时，把服务端专属地址写成 `[前往 MeituHub 充值](<服务端地址>)`，备用页写成 `[MeituHub 套餐定价](https://meituhub.cn/zh-cn/pricing)`。
- 链接 URL 只能作为 Markdown 目标，不能作为可见文字输出。该规则在同一对话的后续轮次持续生效；用户随后再问“充值链接”“充值入口”或“在哪里充值”时，即使不再调用 MCP，也必须继续使用文字链接。
- 不自动打开充值链接或发起购买。

## 工具选型铁律

- **有图必走 `image-edit`，禁止降级到文生图重造。** 只要用户上传图、引用上一轮成图、或把图当"风格参考"，一律走 `image-edit`；只有完全无图才用 `text-to-image`。
- 多图参考融合时，在 prompt 里显式说明每张图的角色（哪张是主体/风格参考/配色参考），禁止笼统写"参考这些图"。
- 保真主体（人像/商品/Logo/角色）必须基于用户素材，不擅自改主体；未提供的 Logo/文字/数据不得凭空编造进画面。

## Visual Prompt 结构化公式

按"**产物类型 → 主体(数量/外观) → 动作/状态 → 环境/背景 → 构图 → 风格 → 光照/质感 → 图中文字**"组织。先写具体可见元素，把"高级感/网感"等空泛词改写为材质、光线、构图、字号层级的可执行描述。

- 像素宽高须为 **16 的倍数**：1:1→1024/1536/2048；3:4→1152x1536/1536x2048；9:16→720x1280/1088x1936/1440x2560；16:9→1024x576/1280x720/1920x1088。
- **必须显式传 `model: nougat`**（知识库契约硬规定：文生图/图生图统一 nougat，禁止省略或让平台选 `auto` 默认路由）。
- 图上要加字：写清具体文字内容、是否加粗、衬线/无衬线、字色与位置，不要只写"加点文字"；不需要字时写 `no text`。

## 平台尺寸速查（作为参数，不写进画面文字）

| 场景 | 比例 | 备注 |
|---|---|---|
| 小红书封面/轮播 | 3:4 | 封面文字占比≤20% |
| 抖音/视频号竖视频 | 9:16 | — |
| 视频封面 | 9:16 / 16:9 / 1:1 | 标题≤12 字 |
| 公众号头图 | 2.35:1 | — |
| 电商主图 | 1:1 | 白底产品居中 |
| 方形/专辑 | 1:1 | 1024² 起 |

## 输出规范

- 说明生成思路、调用的 `text-to-image` 与保留/新增的内容。
- 同一批多图必须锁同一 ratio + size，避免风格与画幅漂移。

## 质检与交付

- P0：主体无畸变/多指/多余肢体，透视、比例、光影一致；P1：风格纯正不串味、文字正确（如有/确无 `no text`）、无未授权 Logo/平台标识/水印。
- 事实护栏：未提供的价格/销量/编号/地址/机构名不写入画面文字，精确色值不自动入 prompt。
- 交付前确认可交付 `image_url`；多张逐张记录，缺图不报完成。
