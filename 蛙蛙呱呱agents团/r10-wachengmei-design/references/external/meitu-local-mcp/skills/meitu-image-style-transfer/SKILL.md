---
name: meitu-image-style-transfer
description: Apply an artistic style to an existing image (anime, 3D clay, illustration, pixel, oil painting, watercolor, Q-version, emoji, etc.) via the meitu-local MCP `image-style-transfer` tool, single-image stylization or dual-image reference transfer. Use for stylization, style transfer, converting an image to a specific art style, or simulating portrait retouch/beauty.
---

# 图像风格化（image-style-transfer）

对已有图片做风格化处理：动漫/油画/水彩/Q版/卡通/3D/像素/emoji等，保留主体特征与构图。

## 工具

调用 `meitu-local` MCP Server 的 **`image-style-transfer`** 工具。支持单图风格化 + 双图参考风格迁移。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## Prompt 编写

- 明确**目标风格**（动漫/3D黏土/手绘插画/像素/油画/水彩/emoji 等）+ **保留要素**（主体、五官、构图）+ **色调倾向**。
- 单图不堆互斥风格；一次一个清晰风格。
- 人物风格化遵循身份保真：prompt 三段式——`保留[面部结构/五官比例/肤色/体型]` → `只改[画风/色彩/质感]` → `不改[身份特征]`。
- 像素宽高须为 16 的倍数；同批多图锁同一 ratio + size。

## 美颜/轻修模拟（meitu 无 image-beauty-enhance 时）

- 单纯磨皮美白：用 `image-style-transfer`，prompt 写"柔焦磨皮、自然美白、五官精致、保留皮肤纹理"。
- 大幅重绘人像走 `image-portrait-generate`，不要用风格化硬造。

## 强度与质检

- strength 风格迁移档推荐 0.4–0.6；单次调整≤0.2，最多 3 轮，第 1 轮严重偏离回退原图。
- 复核主体是否保留、风格是否纯正（单图不堆互斥风格）；人物风格化保留皮肤纹理，不过度磨皮失真。
- **事实护栏（k_visual_asset_fidelity_and_fact_guardrails）**：风格化不篡改主体身份（五官/脸型/肤色/体型）；不把精确色值(hex/Pantone)当强参数自动写入，除非用户明确要品牌色复现；不复制参考图中的文字、Logo、水印或事实信息。
- 交付前确认可交付 `image_url`；同批多图逐张记录，缺图不报完成。

## 工作流

1. 确认输入图与目标风格；判断是否需要双图参考迁移。
2. 写"风格 + 保留要素"prompt，调用工具。
3. 复核主体是否被保留、风格是否达标；最多 3 轮迭代。

## 输出规范

- 标注应用了哪种风格、保留了哪些主体特征；双图迁移说明参考图角色。
- 若用于美颜模拟，注明仅风格化，非专业人像精修。