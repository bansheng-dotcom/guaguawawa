---
name: meitu-face-swap
description: Swap a source face onto a target scene image, keeping the target's composition, body and background with automatic skin-tone/blending, via the meitu-local MCP `image-face-swap` tool. Use only when the user supplies two images and expresses face swap / hair swap / put A's face onto B / P-face intent.
---

# 换脸（image-face-swap）

双图换脸/换头合成：将源图人脸替换到目标场景图，保留目标图构图、身体与背景，自动做肤色融合与光影匹配。

## 工具

调用 `meitu-local` MCP Server 的 **`image-face-swap`** 工具，传源脸图与目标场景图（两个参数位置按工具 schema 对齐）。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- **换脸仅支持真实人脸**，不与视频换脸接口混用（视频换脸需求需评估是否有对应能力）。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 使用规则

- 仅在用户明确提供两张图并表达换脸/换头/P 脸意图时触发。
- 融合描述写清期望（肤色、光影、表情自然度），但主要为"保留目标构图/身体/背景"。
- 身份与合规边界：不用于冒充他人、诈骗或损害他人权益的合成；告知用户合理使用。
- 迭代纪律：单次调整克制，**最多 3 轮**；每轮检验肤色/光影衔接与身份真实感，严重偏离回退源脸/目标图重来，不叠加出错结果。
- 像素输出为 16 的倍数；交付前确认有可交付 `image_url`，缺图不汇报为完成。

## 质检（k_ai_rendering_defects / k_strength_control）

- P0：脸与头/颈/发际无缝、五官无明显畸变、肤色与目标身体一致；P1：光影方向与目标场景匹配、表情自然不过度。
- 避免"物除影留"类伪影；若面部细节（发丝/下巴）衔接差，用 `image-edit` 小范围微调，不反复换脸。

## 工作流

1. 确认源脸图（提供脸的人）与目标场景图。
2. 调用 `image-face-swap`。
3. 复核脸部衔接、肤色/光影一致性，必要时迭代。

## 输出规范

- 说明源脸与目标场景、融合后保留的构图/身体/背景。