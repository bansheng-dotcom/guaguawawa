---
name: meitu-outfit-swap
description: Swap a single person's clothing while keeping the face and body, supporting text description or a clothing reference image, via the meitu-local MCP `image-outfit-swap` tool. Use for virtual try-on / outfit change on an existing portrait image; does not change hairstyle.
---

# 换装（image-outfit-swap）

AI 换装：保留人物面部和体型只替换衣物，支持文字描述或服装参考图。

## 工具

调用 `meitu-local` MCP Server 的 **`image-outfit-swap`** 工具，传单人人物图与目标服装描述。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。
- 仅在用户明确要求对已有单人人物图换装/试穿并已提供人物图时触发。

## 使用规则

- 文件就绪则用目标服装描述或服装参考图（`clothes_image_url`）。
- **只换衣物，不改发型**；保持人物面部与体型不变。prompt 显式锁定"保留面部结构、发型、体型不变，只替换服装款式/面料/色彩"。
- 若用户要连同发型/姿态一起改，改走 `image-edit` 或 `image-portrait-generate`。
- 服装描述具体化（款式/面料/版型/颜色），不只写"换件衣服"。
- 迭代纪律：**最多 3 轮**，单次调整≤0.2；每轮检验面部/体型保留与服装贴合自然度，严重偏离回退原人物图。
- 事实护栏：若换品牌服装/联名款，涉及商标与授权需谨慎，不擅自伪造品牌标识；像素输出为 16 的倍数，交付前确认可交付 `image_url`。

## 质检

- P0：面部/发型复现无漂移、换装不改变人物比例；P1：衣料光影/褶皱与场景一致、领口袖口过渡自然。
- 避免服装"穿模/悬浮"、面料塑料感等渲染缺陷，必要时换 `image-edit` 微调衔接。

## 工作流

1. 确认人物图与目标服装（描述或参考图）。
2. 调用 `image-outfit-swap`。
3. 复核服装替换自然度、面部/体型是否保留。

## 输出规范

- 说明目标服装来源（文字/参考图）与保留的面部/体型；确认未改发型。