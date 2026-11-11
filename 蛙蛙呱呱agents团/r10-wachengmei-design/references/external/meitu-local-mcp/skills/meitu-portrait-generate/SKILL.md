---
name: meitu-portrait-generate
description: Generate high-fidelity portraits from portrait/pet reference images (ID-style portraits, business headshots, artistic portraits, pet portraits, multi-person and dual-person composites / hair-style adjustment) via the meitu-local MCP `image-portrait-generate` tool. Use for AI portrait set, business avatar, artistic portrait, or dual-person composite; not for spot retouch/pose adjustment (use image-edit).
---

# 人像写真 / 形象照（image-portrait-generate）

从参考图（人像/宠物）生成高精度写真：证件照/形象照/艺术照/宠物写真/多人写真/双人合影/发型调整。

## 工具

调用 `meitu-local` MCP Server 的 **`image-portrait-generate`** 工具，`image_list` 传入人像参考图。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 身份保真铁律

- **不要脑补或篡改身份特征**（脸型骨相、年龄层、种族、肤色基调、明显五官标志）。同人连续产物保持五官/发色/肤色一致。
- 事实护栏：地点、机构、编号、日期等事实字段除非用户提供或已核实，否则不写入画面/prompt；艺人/角色关系不混入未核实信息。
- prompt 三段式锁定身份：
  1. `保留`[面部结构、五官比例、肤色基调、眼型、发型、脸型骨相]
  2. `只改`[服装、姿势、场景、背景、光线、情绪]
  3. `不改`[年龄感、面部结构、五官比例、肤色、身份标志]
- prompt 结构 = 主题 + 风格 + 场景 + 服装 + 光线 + "保持人物身份特征不变"。
- **不做局部化妆/姿态调整**：那类需求改 `image-edit`。
- 商务/艺术写真默认交付高保真、真实肤色，不擅自加过度美颜。

## 强度与迭代（知识库 k_strength_control）

- 人像美颜/肤色校正归 `image-edit`；本工具做写真重绘/换场景，`image-edit` 强度仅作类比参考（人像 0.2-0.4 偏保守）。
- 迭代纪律：单次改动克制，**最多 3 轮**；单次调整≤0.2；每轮后评估身份一致性，第 1 轮严重偏离回退原图重规划，不在错误结果上叠加。
- 每轮生成前显式锁定同一 ratio + size，像素为 **16 的倍数**；不做"连环叠图"，上一轮失败结果不作下一轮源图。

## 质检与交付

- P0：身份一致性（五官/发色/肤色）、画面无畸形/多指/悬浮/透视错误；P1：肤色真实不过度磨皮、背景融入自然。
- 交付前确认有可交付 `image_url`；跨张多图逐张记录，缺图不得汇报为全部完成。
- 若生成图主体保留比重生更重要，标记适合转修图/智能构图，不无限重生。

## 工作流

1. 确认参考图（单人/多人和合影时 image_list 顺序 = 人物顺序）与风格/场景/服装。
2. 按三段式写身份锁定 prompt，调用工具。
3. 复核身份一致性；跨张多图保持同一人五官一致；按质检清单确认交付。

## 输出规范

- 标注写真风格、场景、是否双人/宠物；明确以用户原图为身份基准。