---
name: meitu-video-motion-transfer
description: Transfer the motion/pose of a reference video onto a target person or character image, keeping their appearance, via the meitu-local MCP `video-motion-transfer` tool. Use only when the user provides a target person image and a reference motion video and expresses motion transfer, pose-driven, dance replication, or imitating the video's motion.
---

# 视频动作迁移（video-motion-transfer）

把参考视频中的动作（舞蹈、手势、运动）迁移到目标人物或角色图片上，并保留其外貌。

## 工具

调用 `meitu-local` MCP Server 的 **`video-motion-transfer`** 工具。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。
- 仅在用户明确提供目标人物图 + 参考动作视频，并表达动作迁移/舞蹈复刻/让图跟视频做动作时触发。

## 使用规则

- 需要 1 张人物图 + 1 段参考动作视频。
- 人物身份保留由模型处理，prompt 可强调"保留人物五官/体型，仅迁移动作"。
- **素材门控（k_video_execution_contract）**：图片≤9（单张<30MB）、视频≤3（总 2–15s）；复杂任务（跨段一致性/系列）先确认关键素材再生成，不跳过素材准备直接调付费工具。
- **语种继承三字段**：生成前锁定用户原始语种、目标输出语言（默认同原始语种，仅用户明确指定才改）、用户意图与禁用项（否定词原样保留）；目标输出语言约束画面内可见文本。
- **参考素材必须显式 `@` 引用**：`@图片1` 人物主体 + `@视频1` 参考动作，禁止只放进参数靠模型隐式理解。
- 若动作迁移目标为写实真人脸驱动，涉及平台限制需评估是否支持，不强行生成。

## 边界

- 动作迁移是视频能力；图片间复刻用 `image-to-video` / `image-edit`。
- 不含换脸（换脸走 `image-face-swap`，仅图片）。

## 工作流

1. 确认目标人物图与参考动作视频。
2. 锁定语种与素材门控，调用 `video-motion-transfer`（异步用 `meitu_task_get` 跟进）。
3. 复核动作还原度与人物身份保留。

## 输出规范

- 说明人物图与参考动作来源、迁移效果；视频给出 URL/任务 ID。