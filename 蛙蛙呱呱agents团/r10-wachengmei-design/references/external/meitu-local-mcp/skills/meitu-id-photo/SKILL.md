---
name: meitu-id-photo
description: Generate standard ID/visa photos from a user's front-facing portrait using the meitu-local MCP `image-edit` tool (model nougat), with the original portrait as image_list and size/background/expression/head-ratio written into the prompt. Also covers single-person portrait sets (3-grid) and ID background-color change. Use for ID photo, 1-inch/2-inch, passport/visa/work-card/WeChat-avatar photo, ID background swap, or a portrait set; base on the user's original image, never regenerate from scratch.
---

# 证件照与写真套图（image-edit）

基于用户正面人像，用 **`image-edit`**（`model: nougat`）生成规格化证件照（一寸/二寸/护照/签证/工作证/微信头像证件版）与单人写真套图（三宫格等）。不用 `image-id-photo-generate`。

## 工具

调用 `meitu-local` MCP Server 的 **`image-edit`** 工具：

- `image_list`：用户原图（作**身份基准**）
- `model`: `nougat`
- `ratio` / `size`：**必传**，与目标证照比例一致（一寸/二寸→3:4，美签/头像→1:1；详见下方技术参数表）
- `prompt`：写入用途、尺寸/比例、底色、表情、头部占比与身份保真字段

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。
- 必须以用户原图为身份基准，不得从零 `text-to-image`；`image-edit` 是唯一出图路径。

## 证件照规格（k_id_photo_specs）

| 用途 | 尺寸 | 底色 | 表情与构图 |
|---|---|---|---|
| 中国普通一寸 | 25×35mm(295×413px) | 蓝/红/白 | 正面平视、自然表情、不露齿 |
| 中国普通二寸 | 35×49mm(413×579px) | 蓝/红/白 | 正面平视、自然表情、不露齿 |
| 中国护照 | 33×48mm(390×567px) | 白色 | 正面，通常不戴眼镜 |
| 美国签证/护照 | 51×51mm(600×600px) | 纯白 | 正面、不戴眼镜、肩部以上 |
| 日本履历书 | 30×40mm | 白色 | 正面半身 |
| 工作证/学生证 | 22×32mm 或 25×35mm | 白色 | 可自然微笑 |
| 微信头像证件版 | 1:1(1024×1024) | 蓝或白 | 自然微笑 |

- 未说明国家/用途时默认按中国普通一寸出图，交付时说明默认值；若用户给的机构要求与表格冲突，以用户提供/已核实的要求为准。

## Prompt 字段要求

- 目标用途 + 对应尺寸/比例。
- **描述性底色**（如白 / 蓝 / 红），不使用未经授权的精确 HEX。
- 正面平视、表情、露齿/眼镜要求。
- **头部占画面约 60%–70%**，肩颈完整、不切头顶。
- 严格保留五官比例、肤色与身份；只修正曝光与背景，**不美颜、不修脸型**。
- 证件照特殊规则：纯色 polo/衬衫/西装避免格纹；头发不遮挡眉毛与耳朵；不戴眼镜/帽子/口罩；自然轻妆。

## 技术参数（关键：尺寸必须显式传，不能只写进 prompt）

`image-edit` 每次调用**必须**显式传 `ratio` 或 `size`，与目标证照比例严格一致，否则会输出默认画幅导致尺寸错误。像素可用时优先传 16 倍数的 `size`（视觉契约要求）。

| 证照类型 | 物理尺寸 | ratio | 16 倍数 size 参考 |
|---|---:|---:|---|
| 中国普通一寸 | 25×35mm | 3:4 | 1152x1536 / 1728x2304 |
| 中国普通二寸 | 35×49mm | 3:4 | 1152x1536 / 1728x2304 |
| 美国护照/签证 | 51×51mm | 1:1 | 1024x1024 / 1536x1536 |
| 微信头像证件版 | 1:1 | 1:1 | 1024x1024 / 1536x1536 |
| 日本履历书 | 30×40mm | 3:4 | 1152x1536 |

- 工具收到 `ratio`/`size` 后可能按内部常量放大（实测 3:4 → 1728×2304，像素仍为 16 倍数）；此为符合平台生成规格的正常行为，**以 ratio/尺寸语义为准**，最终交付如需精确像素再按平台要求裁切/导出（知识库：发布规格与生成参数可分离）。
- 用户给定非 16 倍数像素时，对齐到最接近且不破坏画幅的 16 倍数，并在交付说明标注"已按 16 倍数对齐"。

## 任务路径

| 用户需求 | 处理 |
|---|---|
| 标准证件照（指定规格） | `image-edit`，**显式传**匹配的 `ratio`/`size` + prompt 写规格（尺寸/底色/表情/头部占比） |
| 上传旧照换底色 | `image-edit` 单次替换为指定纯色背景，并修正光线 |
| 写真/艺术照 | `image-edit`，prompt 写主题 + 风格 + 场景 + 服装 + 光线（默认 3:4 或 9:16） |
| 三宫格写真（同一人多 pose） | `image-edit` 分别生成 3 张同主题，prompt 强调跨张身份一致 |

## 质检（k_portrait_aesthetic 三维）

- **肌肤**：保留毛孔纹理，不塑料化；美白 1–2 档内，脸与脖子色差不过大；局部去瑕、不高光过曝。
- **五官**：瘦脸下颌≤8%、大眼≤10%、鼻翼≤5%、嘴型自然保留比例——强调"保留五官比例"。
- **光线**：单一主光源方向一致、单一色温、下颌有自然反射、人物与背景光匹配。

## 降级

- 用户原图为侧脸：提示重拍正脸照，**不强行翻正**（会身份漂移）。
- 原图分辨率<512px：直接用原图尽力出图，不索取高清原图。
- 底色不达标：先做纯色背景替换，再修正光线。
- 出图不像本人/身份漂移：重写 prompt 强化锁定（`keep facial features identical / lock eyes nose lips shape`）后重试；变化>15% 标记 `[IDENTITY_DRIFT]` 重做。

## 输出规范

- 标注规格（尺寸、底色、是否免冠露耳）、换装/换底情况，并注明采用的默认（国家/用途）。
- 所有解说使用用户的语言。