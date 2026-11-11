---
name: meitu-video-postproduction
description: Post-production repair of existing videos via the meitu-local MCP video tools: upscale (video-resolution-upscale), denoise (video-denoise-enhance), frame-rate (video-framerate-enhance), low-light (video-lowlight-enhance), canvas expand (video-canvas-expand), element removal (video-element-remove) and content replace (video-content-replace). Use for video quality repair, making a clear sharp video, removing captions/watermarks, adding frames, brightening dark videos, expanding canvas or swapping video content; not for geometry/quality mixing confusion.
---

# 视频后期（video-postproduction）

对已有视频做后期修复与改造，按需单项路由。

## 工具（`meitu-local` MCP Server）

- **`video-resolution-upscale`** — 分辨率超分（720P/1080P/2K/4K），仅像素重建不含质量修复；须显式给 `target_resolution`。
- **`video-denoise-enhance`** — 去噪/去颗粒/去色块。
- **`video-framerate-enhance`** — 补帧/插帧（24→60 等，明确目标帧率）。
- **`video-lowlight-enhance`** — 暗部提亮/夜景修复。
- **`video-canvas-expand`** — 画布向外 outpainting 扩图（`expand_ratio`、`directions`）。
- **`video-element-remove`** — 去字幕/水印/路人/清屏文字。
- **`video-content-replace`** — 替换人物/场景/服装，保留运镜与动作。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 生成/引用门控（知识库）

- 视频生成单条直出：未指定时长默认 15s，一条完整视频不拆段、不拼接；超 15s 才分多次。
- 素材门控：图片≤9（单张<30MB）、视频≤3（总时长 2–15s）、音频≤3、混合≤12；不支持写实真人脸驱动（如涉及需评估）。
- 参考素材必须在 prompt 内**按顺序显式引用**（reference_image_list / image_list 等），不只靠隐式理解。
- 已有对白/旁白必须逐句写进 prompt，不删成"后期配音"；台词单句≤10 字、全片克制，口语化不写广告腔。

## 按需路由、不串链

- **单条视频若无后期诉求**（无清晰度/降噪/补帧/画幅诉求）直接返回原视频，不调用工具。
- 高清增强（超分）→ `video-resolution-upscale`（须用户给目标分辨率，不给则问）。
- 噪点/颗粒 → `video-denoise-enhance`；卡顿/补帧 → `video-framerate-enhance`（明确帧率）；暗部/夜场 → `video-lowlight-enhance`；去字幕/水印/移物/清屏 → `video-element-remove`；多平台比例/扩画布 → `video-canvas-expand`。

## 交付说明

- 注明处理内容、目标分辨率/帧率、是否降噪补帧。
- 口型/对白同步问题不属于视频修复阶段处理。
- 视频内容替换保留原运镜与动作，prompt 描述目标变化。