---
name: meitu-image-to-video
description: Drive a dynamic video from images via the meitu-local MCP `image-to-video` tool, covering single-image generation, multi-image reference fusion (1-9 images) and first/last-frame transition (1-2 images). Use for image-to-video, make a picture move, photo-to-video, multi-image fusion, first-last-frame, transition A-to-B video.
---

# 图生视频（image-to-video）

以一张或多张图片驱动生成动态视频，覆盖单图生成、多图参考融合（1–9 图）、首尾帧过渡（1–2 图）。

## 工具

调用 `meitu-local` MCP Server 的 **`image-to-video`** 工具，传输入图与动作/运镜 prompt。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## Prompt 编写

- 写清主体、动作、场景、运镜、光影、时长；避免多物体同动、精细手势、大幅转身等易畸变内容。
- 多图参考时逐一说明每张角色（主体？背景？过渡帧？）。
- 首尾帧过渡：明确首帧画面与尾帧画面的衔接期望。
- **参考素材必须在 prompt 内显式 `@` 引用**（`@图片1` 作为主体/`@图片2` 作为场景/`@视频1` 作为运镜），禁止只放在 image_list 靠模型隐式理解。已确认的角色/场景锚点也要按顺序显式引用。
- 素材门控：图≤9（单张<30MB）、视频≤3（总 2–15s）、混合≤12；不生成写实真人脸驱动（平台自动拦截）。
- 语种继承：画面内对白/字幕/文字跟随目标输出语言，不夹带别国语种；对白逐句写进 prompt（`说话人(情绪)：「台词」`），不判成后期配音删掉。

## 应用场景

- 适合产品展示/氛围/运镜类动效。
- 动作复刻类（让图中人物模仿某段视频动作）走 `video-motion-transfer`（需 1 张人物图 + 1 段参考动作视频）。

## 短视频方法参考

- 15s 三段式：镜1(0–5s) 抛钩子/立人设 → 镜2(5–10s) 反转或产品自然出场 → 镜3(10–15s) 结果落地 + CTA。
- 带货/种草：产品在场景化动作中自然出现，全片出镜 3–8s、单次特写≤2s。

## 工作流

1. 确认输入图（单图/多图/首尾帧）与动作、运镜 prompt。
2. 调用 `image-to-video`（任务异步时用 `meitu_task_get` 跟进）。
3. 复核动效自然度与主体一致性。

## 输出规范

- 说明输入图数量与角色、生成的动作/运镜；视频给出 URL/任务 ID 与成片结构。