---
name: meitu-image-edit
description: Edit or create images from an existing base/reference image via the meitu-local MCP `image-edit` tool. Use for content edits, style replication, element changes, multi-image fusion, or producing a new image based on a reference; never use text-to-image when a source image exists.
---

# 图生图 / 通用编辑（image-edit）

基于已有底图做内容编辑，或基于参考图创作新图。覆盖电商出图、人像编辑、多图与一致性编辑、风格复刻、参考图创作。

## 工具

调用 `meitu-local` MCP Server 的 **`image-edit`** 工具，`image_list` 传入需保真/作为风格参考的全部素材图。

## 环境与前置

- 未连接美图账号时先引导授权；`meitu_auth_status` 作检查，绝不要 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh` 处理。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 工具选型铁律

- **有图必走本工具**：用户上传图、引用上一轮成图、或把图当"风格参考"（借色彩/质感/构图）都算有图，禁止降级为纯文字 `text-to-image` 重造。
- **资产保真**：prompt 先锁定不变项（"保持主体外观完全一致：外形/比例/配色/材质/细节"），再写要改的部分，结尾加"其余元素保持不变"防连带改动。
- 不得编造品牌、价格、销量、编号、时间等未提供的事实字段；精确色值默认不写入画面文字，改用描述词。
- 多图输入时逐一说明每张角色；同批多图锁同一 ratio + size。
- **图片生成统一显式传 `--model nougat`**（知识库契约硬规定：text_to_image / image_edit 必须显式 `model: nougat`，禁止省略或让平台默认路由）。功能差异通过 prompt 表达，不通过换模型名。

## Prompt 编写

- 以用户原话为主干，意图明确时最多追加一句范围保真，不要过度加料。
- 按下述顺序组织：产物类型 → 主体（含必须保留的资产）→ 修改/动作 → 背景 → 构图 → 风格 → 光照/质感 → 图中文字。
- 渲染缺陷（透视畸变、比例失真、材质塑料感、手指/五官异常、多余元素）先复核，需要时重做该步骤。
- 像素宽高须为 16 的倍数。

## 强度与编辑语气（知识库）

- 编辑 prompt 用**命令句**：`Remove / Replace / Add / Change` + 对象 + 约束，末尾加 `Keep all other elements unchanged`；不写描述句。
- **Strength 三档策略**（推荐起步）：人像美颜/肤色校正/降噪 0.2–0.4；背景替换/风格迁移/色彩 0.4–0.6；暗光提亮/老照片修复/物体移除 0.6–0.8。单次调整幅度≤0.2，最多 3 轮迭代；第 1 轮严重偏离回退原图。
- 局域编辑用 mask 思路：只描述要动的区域，保留区在 prompt 里显式保护。

## 质检自查（渲染缺陷）

- P0 必查：透视正确、物体不悬浮、比例合理、光影一致（单光源、阴影同向）。
- P1：留白不过满、材质具体（用真实材质名而非 `stone` 类笼统词）、风格纯正。
- 缺陷修复工具链：透视畸变→`image-transform`/`image-edit`；物体多余→`image-element-remove`；材质塑料感→`image-superres-enhance`；风格串味→`image-edit`(nougat)。

## 工作流

1. 收集底图/参考图（作为保真资产）与明确修改要求。
2. 判定有图→走 `image-edit`；选 model；锁 ratio/size。
3. 写保真 prompt 调用并复核结果；最多 3 轮迭代后交付最佳。

## 输出规范

- 说明基于哪些参考图、保留了什么、改了什么、用了什么 model。
- 多图/系列产物要写清统一前缀与一致性策略。