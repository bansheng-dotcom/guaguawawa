---
name: meitu-image-cutout
description: Separate the foreground subject from the background and output a transparent PNG (portrait/pet/product/shape-stamp) or white background via the meitu-local MCP `image-cutout` tool. Use for cutout, remove background, transparent background, isolate the subject, or a specified white-background version.
---

# 抠图 / 去背景（image-cutout）

把前景主体与背景精准分离，输出透明底 PNG（人像/宠物/商品/图形印章）或白底图。

## 工具

调用 `meitu-local` MCP Server 的 **`image-cutout`** 工具，传输入图路径。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 使用规则

- `model_type`：0=人像，1=商品，2=图形；省略自动判断。主体占画面足够显著时直接抠；小主体/多个候选先隔离再抠。
- **换背景 ≠ 抠图**：用户只说"换背景"→ 走 `image-background-replace`，不要先切去 `image-cutout`。需要透明底交付时才用本工具。
- 检查：主体边缘是否干净、有无残留背景、细节（发丝/毛发/商品边缘）是否完整。

## 质检（k_visual_asset_fidelity / k_ai_rendering_defects）

- P0：主体完整无断裂、边缘（发丝/毛发/商品轮廓）干净、无残留背景像素、无"物除影留"（影子残留）。
- P1：细节通道（半透明纱、玻璃反光、毛绒边缘）保留；主体比例未变形。
- 复杂主体/多候选一次不干净时，先隔离再抠，不无限重抠（累计最多 3 次）。

## 工作流

1. 确认输入图与主体类型（人像/商品/图形）。
2. 调用 `image-cutout` 输出透明底 PNG（或用户明确要的白底）。
3. 复核边缘与残留，必要时对主体细节逐项确认。

## 输出规范

- 标注主体类型、是否透明底，交付文件/URL。
- 若用户要透明素材做后续合成，提醒其可用透明底结果继续。