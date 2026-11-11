---
name: meitu-image-superres-enhance
description: Upscale or enhance image sharpness/resolution by content type (general/e-commerce/photo/text document) via the meitu-local MCP `image-superres-enhance` tool. Use for make clearer, HD repair, upscale to 4K/2K/1080P, enhance quality, restore old photos, or sharpen product/scanned-text images; do not use for pure geometry resizing (use image-transform).
---

# 超清 / 画质提升（image-superres-enhance）

提升图片清晰度、放大分辨率，按内容类型自动选算法（通用/电商商品/文字文档）。

## 工具

调用 `meitu-local` MCP Server 的 **`image-superres-enhance`** 工具，传输入图路径与内容描述。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 关键判别

- `image-superres-enhance` = **画质/超分**（提升清晰度与分辨率）。
- `image-transform`（`sr_num`） = **几何变换**（比例放大缩小，不提升清晰度）。
- 二者不可互作兜底。"放大 2 倍"走 transform 的 `sr_num`；"变清晰/超清到 4K"走本工具。

## 使用规则

- prompt 给内容类型描述，如 `e-commerce white-background product` / `scanned text document` / 人像描述，帮助选算法。
- **不得与 `image-denoise-enhance` 串联**：超分自带轻量降噪兜底。明显噪点且用户点名"降噪"才单独走 denoise。
- 人像保留皮肤纹理与毛孔，不过度磨皮失真；文档保留文字边缘。
- 若需像素对齐，输出尺寸须为 16 的倍数。

## 工作流

1. 判断是"变清晰/超分"（本工具）还是"几何放大"（transform）。
2. 给内容描述 prompt，调用本工具。
3. 复核细节保留与是否过度处理。

## 质检与交付

- 复核：细节（文字边缘/皮肤毛孔/材质纹理）是否保留、有无过度锐化/塑料感假象。
- 交付前确认有可交付 `image_url`；注明输出尺寸并确认 16 倍数对齐。

## 输出规范

- 标注内容类型、放大倍数/目标清晰度、保留的细节；注明未做几何裁切（如需要走 transform）。