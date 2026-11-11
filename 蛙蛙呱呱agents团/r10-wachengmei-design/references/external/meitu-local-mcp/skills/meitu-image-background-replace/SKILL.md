---
name: meitu-image-background-replace
description: Replace the whole background / swap the scene of an image while keeping the foreground subject unchanged, via the meitu-local MCP `image-background-replace` tool. Use for change background, swap scene, product scene change, portrait background change or ID-photo background color change; cannot output a transparent background (use image-cutout for that).
---

# 换背景 / 换场景（image-background-replace）

替换图片整体背景/换场景，保留前景主体不变。适用于人像换背景、商品换场景、证件照换底色等；**不能输出透明背景**。

## 工具

调用 `meitu-local` MCP Server 的 **`image-background-replace`** 工具，传输入图路径与目标场景 prompt。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 使用规则

- **换背景 ≠ 抠图**：直接按目标 prompt 替换背景，不要先切去 `image-cutout`。需要透明底交付时才用 `image-cutout`。
- prompt 给目标场景，如 `white background`、商品棚拍场景、人像生活场景。
- 换背景后必须检查：主体边缘是否干净、主体与新背景的光照方向/色温是否一致、主体比例是否自然。

## 质检（k_prompt_formula / k_ai_rendering_defects）

- P0：主体边缘干净、主体与新背景的比例/透视自然、无"悬浮/漂浮"感；P1：光照方向与色温一致（如 cert background 用 `light from [方向], shadows casting to [方向], single light source`）、边缘过渡自然无硬边。
- prompt 用背景替换模板：`将背景替换为[目标背景]，保留前景[主体]不变，光照方向匹配[光源方向]，边缘过渡自然无硬边`。
- 迭代纪律：**最多 3 轮**；换底涉及证件照底色时按证件规范（纯白/纯蓝/纯红、头部占 60-70%），底色用标准色彩描述，不写精确色值除非用户要求。

## 工作流

1. 确认输入图与目标背景场景。
2. 调用 `image-background-replace`。
3. 复核主体保留与光照一致性，必要时迭代。

## 输出规范

- 标注保留的主体、替换后的背景场景；说明不输出透明底，如需透明底提示改用 `image-cutout`。