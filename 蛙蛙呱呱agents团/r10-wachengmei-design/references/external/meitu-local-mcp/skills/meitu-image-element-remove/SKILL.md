---
name: meitu-image-element-remove
description: Remove watermarks, text, or local objects/elements from an existing image via the meitu-local MCP `image-element-remove` tool. Use for watermark removal, removing selected text, removing passers-by/objects, stamps/reflections/screen textures, or cleaning up a region; do not use for replacing text (use image-text-replace) or swapping backgrounds (use image-background-replace).
---

# 元素 / 水印 / 文字消除（image-element-remove）

从已有图片中去除水印、文字或局部物体，覆盖通用水印消除、文档半透明水印、局部物体与指定文字消除。

## 工具

调用 `meitu-local` MCP Server 的 **`image-element-remove`** 工具，传输入图路径。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 场景分类（先分类再定 target / prompt）

| 情况 | 判定 | target 与 prompt |
|---|---|---|
| A 基础水印 | 非半透明或单一水印 | `target: watermark`，可不填 prompt |
| B 全图去字 | 去除画面全部文字 | `target: text` |
| C 文档半透明水印 | 半透明字水印 + 纯文字文档/白底文字页 | `target: watermark` |
| D 复杂消除 | 指定文字/指定颜色文字、路人、杂物、投影阴影、印章公章、线条、Logo、反光、屏幕纹等 | 用 prompt 精确描述消除内容与位置 |

## 执行规则

- 复杂消除**禁止先做图片分析**：直接生成消除 prompt，再把它**原样、不删减**带入原图执行。
- 消除 prompt 模板：`移除图片中的[目标]，用周围环境自然填充，保持[周围区域]连续性，不影响[需保护元素]`。
- 只移除目标本身；目标越大越需小范围分次；涉及阴影/反射要说明一并处理，避免"物除影留"。
- 印章类消除后若需透明素材，对结果图再 `image-cutout`。
- 重做口径：用户要求重新生成→用**用户原图**；重新上传→用新图；新的修改描述→用**上一轮结果图**。
- 累计最多尝试 3 次；达上限交付当前最佳或请用户提供更清晰原图/更精确目标。
- **mask 覆盖**：消除区域 mask 比目标实际大 10–20%，覆盖阴影与反射，避免"物除影留"。
- **大面积移除**：分多次小范围执行，不要一次性覆盖过大区域。
- **二次检查**：目标是否完全移除（无残留）、填充自然（无接缝伪影）、周围纹理/光照连续。
- 物体移除 strength 推荐 0.6–0.7，单次调整≤0.2。

## 边界

- 替换/修改文字 → `image-text-replace`；换背景 → `image-background-replace` / `image-edit`；删整张背景 → `image-cutout`；视频去水印 → `video-element-remove`。

## 输出规范

- 标注 target、消除 prompt、是否残留与填充是否自然，及重做输入图口径。
- 交付前确认有可交付 `image_url`；印章消除后若需透明素材，交付时提示可继续走 `image-cutout`。