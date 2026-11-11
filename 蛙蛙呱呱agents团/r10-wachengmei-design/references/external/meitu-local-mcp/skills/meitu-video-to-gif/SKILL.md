---
name: meitu-video-to-gif
description: Convert a video to a GIF (normal GIF long-edge ≤480px or transparent-background 240x240 sticker) via the meitu-local MCP `video-to-gif` tool. Use for video-to-GIF, making stickers/memes, making animated GIFs, or transparent-background floating stickers.
---

# 视频转 GIF（video-to-gif）

把视频转成 GIF 动图，支持普通 GIF（长边 ≤480px）和透明底 GIF（240×240px 贴纸）。

## 工具

调用 `meitu-local` MCP Server 的 **`video-to-gif`** 工具，传视频路径。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 使用规则

- 普通 GIF：长边 ≤480px，适合表情包/示意动图。
- 透明底 GIF：240×240px，适合贴纸/浮动表情。

## 工作流

1. 确认选段（若视频较长先确定转哪段）与输出类型（普通/透明底）。
2. 调用 `video-to-gif`。
3. 复核动效与格式。

## 输出规范

- 标注 GIF 类型、尺寸；交付 URL/文件。
- 透明底 GIF 主要用于贴纸/浮动表情，确认背景已透明、无残留色边；像素符合 240×240 规格。