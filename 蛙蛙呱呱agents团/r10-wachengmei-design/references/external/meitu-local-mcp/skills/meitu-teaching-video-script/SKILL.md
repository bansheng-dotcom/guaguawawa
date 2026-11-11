---
name: meitu-teaching-video-script
description: Plan teaching explainer video scripts, storyboards and visual rhythm, producing a self-contained handoff brief, with key-frame visuals via the meitu-local MCP `text-to-image`/`image-edit` and dynamic clips via `image-to-video`/`text-to-video`, plus video quality repair via the video tools. Use for teaching/explainer videos, course videos, voiceover or no-voiceover classroom explainers, key-frame/visual generation for lessons.
---

# 教学解说视频脚本（teaching-video-script）

规划教学视频脚本、分镜与视觉节奏，产出可直接交付、可独立成片消费的 handoff brief，并配合关键帧视觉与动态片段生成。

## 工具（`meitu-local` MCP Server）

- 文本生成脚本/大纲：**`text-generate`**。
- 关键帧画面：**`text-to-image`**（无基线）或 **`image-edit`**（有参考/角色基线），`model: nougat`。
- 图生教学视频片段：**`image-to-video`**；文生教学视频：**`text-to-video`**。
- 视频画质修复：**`video-resolution-upscale`** / **`video-denoise-enhance`** / **`video-framerate-enhance`** / **`video-lowlight-enhance`**（按需单项路由）。
- 画面元素消除：**`video-element-remove`**（去字幕/水印/路人）。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 参数

- `usage_scenario` ∈ { media_publish / kids_explain / teacher_classroom }，默认 media_publish。
- `narration_mode` ∈ { voiceover（带讲解旁白）/ silent（无旁白，现场讲解）}，默认 voiceover。

| 维度 | voiceover | silent |
|---|---|---|
| 主信息载体 | 口播配音 | 字幕 + 现场讲解者 |
| 字幕角色 | 辅助（与口播同步） | 主力（独立成立） |
| 单画面停留 | 4–6 秒 | 6–10 秒 |
| 配音轨 | 出 | **禁止生成** |
| 现场讲解大纲 | 不需要 | 必出 |

- 风格档位：MG-Flat / PictureBook / Whiteboard / Screencast / LiveAction / Talker / Mixed。
- 时长档：短视频(1-3min)1 知识点+1 案例；中视频(3-8min)2-4 知识点;长视频(8-15min)体系化。

## 知识真实性与教学叙事

- 教学叙事四段式：钩子10-20% → 知识点拆解40-50% → 案例/实操25-35% → 总结/行动10-15%。
- 事实可追溯，不可追溯标 `[需校对]`；禁止编造定义/数据/历史。

## 工作流（场景 C：教学解说视频）

1. 需求洞察：确认主题/受众/`usage_scenario`/`narration_mode`/时长档/风格档。
2. 内容策划：判断教学类型（解释/步骤/混合），按四段式编排。
3. 脚本产出：voiceover 出每段口播+字幕+关键词高亮+画面建议；silent 出现场讲解大纲+字幕+画面停留时长建议。
4. 视觉生成：关键帧 `text-to-image` / `image-edit`；动态片段 `image-to-video` / `text-to-video`；画质 `video-resolution-upscale` 等按需。
5. 交付：自包含 handoff brief + 关键帧视觉素材。

## 输出规范

- 提供分镜脚本、口播文本/现场讲解大纲、字幕、关键词高亮、画面描述与时长规划、关键帧视觉；标注适用学段、教学目标、受众难度分级。