---
name: meitu-image-denoise-enhance
description: Remove grain/noise and blocky artifacts from an image while keeping detail, via the meitu-local MCP `image-denoise-enhance` tool. Use only when the user explicitly asks for denoising or mentions noise, grain, ISO, dirty/noisy picture; do not chain it blindly with super-resolution.
---

# 降噪 / 画质净化（image-denoise-enhance）

去除图片颗粒感/噪点/杂色色块，保留细节同时降噪。

## 工具

调用 `meitu-local` MCP Server 的 **`image-denoise-enhance`** 工具，传输入图路径。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 使用规则

- **单点路由，不串链**：仅在用户点名"降噪/去颗粒"时用本工具。清晰度不足走 `image-superres-enhance`（自带轻量降噪兜底），不要与 denoise 强行串联。
- 保留细节纹理，避免过度平滑丢细节。
- 降噪后如需放大分辨率，再按需走 superres（用户明确点名才做）。

## 工作流

1. 确认噪点/颗粒确实存在且用户要求降噪。
2. 调用 `image-denoise-enhance`。
3. 复核细节是否保留、噪点是否清除、有无过度磨皮/油画感。

## 质检与交付

- 降噪强度类比：过度降噪会丢细节变"油画感"（k_strength_control 降噪 0.4-0.5 平衡档）；人像保留皮肤纹理。
- 交付前确认可交付 `image_url`。

## 输出规范

- 说明做了降噪处理；若顺带需要变清晰，提示补走 superres。