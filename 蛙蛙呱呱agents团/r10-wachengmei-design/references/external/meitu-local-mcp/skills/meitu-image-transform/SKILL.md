---
name: meitu-image-transform
description: Apply geometric transforms / smart composition / sizes on an image without changing its content (rotate, flip, scale by multiple, resize, smart-compose, canvas expand / outpaint) via the meitu-local MCP `image-transform` tool. Use for rotate/flip/mirror, enlarge N times, shrink to size, change ratio, expand canvas or smart recomposition; do not use for quality/sharpness enhancement (use image-superres-enhance).
---

# 图像变换 / 智能构图（image-transform）

图片几何变换与尺寸变换，**不改画面内容**：旋转/翻转、倍数缩放、无损缩小、调整尺寸、智能构图、画布扩展/扩图。

## 工具

调用 `meitu-local` MCP Server 的 **`image-transform`** 工具，传输入图路径。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 关键判别

- `image-transform` = **几何**（尺寸/比例/旋转，不提升清晰度）。
- `image-superres-enhance` = **画质/超分**。
- "放大 2 倍"→ transform 的 `sr_num`；"变清晰/超清到 4K"→ superres。二者不可互作兜底。

## 分支判定

| 用户意图 | 处理方式 |
|---|---|
| 等比放大/缩小/按倍率 | `sr_num: 2/4/8`，保持比例 |
| 旋转 / 翻转 | `rotate` / `flip_x` / `flip_y` |
| 指定新比例并重构画面 | `width`/`height` + prompt（outpaint 补全） |
| 指定目标宽高尺寸 | `target_width` / `target_height` |
| 变清晰 / 超分 | 走 `image-superres-enhance`（非本工具） |

## 规则

- 等比缩放到指定宽高时目标须与原图等比；非等比先换算成等比并告知用户。
- **outpaint / 尺寸延展必须保留主体**：人像护全脸+发际+肩颈；商品护本体+包装文字+Logo+投影根部；品牌 KV 护主视觉+标题+Logo 安全区。
- 语义补全贴合画面意图（室内续墙地窗光、户外续天地透视、商品续品牌色），不凭空造新主体/多余肢体。
- 像素输出须为 16 的倍数。
- 禁止：GIF 输入、局部旋转（走 `image-edit`）、视频画布扩展（走 `video-canvas-expand`）。

## 工作流

1. 判断是否几何变换（是→本工具；变清晰→superres）。
2. 按上表选 mode/参数；outpaint 写延展 prompt。
3. 复核主体保留与结果尺寸。

## 输出规范

- 标注原图尺寸、变换类型、结果尺寸；outpaint 给出延展 prompt 与保留区域。