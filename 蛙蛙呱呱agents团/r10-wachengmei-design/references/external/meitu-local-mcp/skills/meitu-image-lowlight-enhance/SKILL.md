---
name: meitu-image-lowlight-enhance
description: Brighten underexposed, dark, or night images and recover shadow detail while keeping highlights, via the meitu-local MCP `image-lowlight-enhance` tool. Use when the user explicitly mentions dark/low-light/night/underexposed repair or wants smart brightening of dark regions.
---

# 暗部 / 夜景提亮（image-lowlight-enhance）

对偏暗、夜景或曝光不足的图片进行暗部提亮与细节恢复，保持亮部不过曝。

## 工具

调用 `meitu-local` MCP Server 的 **`image-lowlight-enhance`** 工具，传输入图路径。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 使用规则

- 仅在用户明确是暗光/夜景/欠曝修复时使用；泛化的"提亮"或普通调色需求不触发（走 `image-edit`）。
- 目标是恢复阴影细节、提亮暗部，同时**保持亮部不过曝**。
- 若同时有多重问题（如又暗又糊），按单点路由：先 `image-lowlight-enhance` 提亮，再按需判断是否超分，不擅自串链。

## 工作流

1. 确认暗部/夜景/欠曝问题。
2. 调用 `image-lowlight-enhance`。
3. 复核暗部细节恢复程度与亮部是否过曝。

## 质检与交付

- 暗光增强强度类比：暗光图需激进处理才有效（k_strength_control 暗光 0.7-0.8），但要**保持亮部不过曝**（跨动态范围检查）。
- 交付前确认可交付 `image_url`。

## 输出规范

- 说明做了暗部提亮与细节恢复；提示是否还需要其它修复（超分/降噪）。