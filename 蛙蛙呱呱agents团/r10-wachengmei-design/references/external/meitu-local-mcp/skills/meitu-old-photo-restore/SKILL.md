---
name: meitu-old-photo-restore
description: Restore old photos by removing scratches/creases/stains/mold, fixing fading and blur, naturally colorizing B&W photos and repairing faces while keeping identity. Uses the meitu-local MCP `image-element-remove` (scratch/stain removal), `image-superres-enhance` (upscale) and `image-edit` (reinvention/colorize) tools. Use for old photo restoration, refurbishing, scratches/creasing removal, B&W coloring, or face repair.
---

# 老照片修复（old-photo-restore）

去除划痕、折痕、污渍、霉点，修复褪色与模糊，为黑白照片自然上色，修复人像面部时保留原始特征。

## 工具（`meitu-local` MCP Server）

- **`image-element-remove`** — 去除划痕、折痕、污渍、杂物（单点目标，避免误删主体）。
- **`image-superres-enhance`** — 提升清晰度/分辨率。
- **`image-edit`** — 褪色还原、黑白上色、整体色彩校正、老照片视觉缺陷修复（自然语言 prompt 走模型智能修复）。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 分流

- 清晰度/细节不足 → `image-superres-enhance`（自带轻量降噪兜底，不与 denoise 串联）。
- 划痕/折痕/水印/杂物 → `image-element-remove`。
- 褪色还原/黑白上色/整体色彩校正/老照片缺陷 → `image-edit`。
- 老照片既需超分又需修瑕疵：先 `image-element-remove` 去划痕，再 `image-superres-enhance` 或 `image-edit` 复原，按用户点名的处理动词逐项推进，不擅自开多步链。

## 规则

- **人像面部修复保留原始特征**：不脑补/篡改身份（脸型、年龄感、肤色基调、明显五官标志），prompt 锁定"保留面部结构，只修瑕疵/补色彩"。
- 迭代纪律：单次改动克制，最多 3 轮迭代后交付最佳；复核不达标按原图重做受影响步骤，不重复加工已达标区域。
- 输出尺寸如需像素对齐为 16 的倍数。

## 工作流

1. 确认照片问题清单（划痕/褪色/模糊/黑白上色等）。
2. 按分流逐项调用工具处理。
3. 质检：无残留瑕疵、填充自然、色彩自然、身份保留。

## 质检与交付

- P0：身份保留（不脑补/篡改脸型、年龄感、肤色基调、五官标志）、无残留瑕疵、无"过度现代化"（保持年代感，per prompt_formula 老照片修复）;P1：色彩自然、划痕填充无接缝伪影。
- 交付前确认可交付 `image_url`；黑白上色需说明色彩倾向是否经用户确认。

## 输出规范

- 列出每步处理命令、保留/还原的细节；黑白上色需说明色彩倾向是否经用户确认。