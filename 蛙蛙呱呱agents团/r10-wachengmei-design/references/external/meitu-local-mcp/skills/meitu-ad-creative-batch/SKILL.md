---
name: meitu-ad-creative-batch
description: Batch ad-creative A/B testing for e-commerce/product teams using a fixed 3-direction contract (ingredient/tech/lifestyle), 2 variants each and 3 spec ratios (3:4, 1:1, 9:16) = 18 feed ads, via the meitu-local MCP `image-edit` (with base) or `text-to-image` (no base) tools, both bound to model nougat. Use for ad A/B testing, multi-direction feed material, or creative matrix; keep a unified style prefix for consistency.
---

# 广告创意批量测试（ad-creative-batch）

面向电商/产品设计团队的广告 A/B 测试与创意矩阵。核心是**固定合同 + 批量一致性**，不是随意出多张。

## 工具（`meitu-local` MCP Server）

- 有产品图/Logo/参考图：**`image-edit`**，`image_list` 带入全部需保真的素材图，`model: nougat`。
- 无任何输入图：**`text-to-image`**，`model: nougat`。
- 广告视觉**不**使用 `image-poster-generate`（那是站内信息型海报工具）。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 固定生成合同（唯一路径）

1. 从 brief 提取：产品/品牌素材、投放目标、目标人群、核心卖点、平台与比例；缺失项做合理默认，不中断。
2. **18 张投流图 = 3 方向 × 2 变体 × 3 规格(3:4/1:1/9:16)**：

| 方向 | 核心表达 | 变体只允许改的变量 |
|---|---|---|
| 成分功效 | 成分、功效依据、问题与改善感受 | 成分切入点或功效钩子 |
| 专业科技 | 技术原理、专业背书、产品细节 | 科技表达方式或专业场景 |
| 生活方式 | 真实使用场景、目标人群与情绪价值 | 使用场景或生活化钩子 |

3. 同一方向两张变体只改 1 个核心变量；产品外形、包装、Logo、主卖点、目标比例保持稳定。
4. 比例适配用 `image-edit` 重新组织主体/文字区/CTA 安全区，不用机械裁切替代重新排版。
5. 有历史 CTR/CVR/成本数据时保留表现好的卖点/钩子作优先测试项；数据不足标注"待验证假设"，不把推测写成结论。

## 批量一致性（2+ 图强制，防风格漂移）

1. 提炼 30–50 词统一风格前缀：锁定插画范式、色彩系统、质感、排版、否定约束 5 维；全批次逐字复用。
2. 先生成**锚点图**（信息量最大的主视觉），其余图并行生成。
3. 派生三模式：
   - 构图相似+同主体 → `Keep the exact same layout, color scheme, illustration style, and visual treatment unchanged.`
   - 主体不同但风格继承 → `Using the EXACT SAME visual style as this reference (...same palette, same texture, same background treatment). The visual style must be indistinguishable, but the subject matter is completely different.`
   - 构图不同但同主体 → `Maintain the same design system (...colors, shapes, whitespace, aesthetic).`
   - 写 `keep the visual STYLE the same, but the CONTENT is entirely new`；**禁止**写 `keep everything the same`。连续 2 次内容污染→放弃 image-edit，降级 text-to-image + 统一前缀。

## 工具契约红线

- 有图走 `image-edit`、无图走 `text-to-image`，广告默认 `model: nougat`。
- 同批锁同一 ratio + size；像素为 16 的倍数。
- 每条广告 prompt ≤200 字；单图 ≤3 个核心元素，超出拆图；删 `beautiful/amazing/stunning/best quality` 等无效词；色温只选一个方向。
- 平台名/UI 元素禁入图（不写"小红书/抖音"，用"竖版 3:4 信息流海报"抽象描述）。
- **事实护栏（k_visual_asset_fidelity_and_fact_guardrails）**：卖点中的成分/功效/技术原理若来自用户 brief 或已核实数据才入图；未经核实的销量、排行、证书编号、资质、团队规模等事实字段不写入描述或画面文字，避免虚假宣传；用户 brief 混入未核实事实时，视觉侧清洗后再出图。
- 交付前逐张确认可交付 `image_url`，18 张缺图不得汇报为全部完成。

## 工作流

1. 收集素材与 brief，套用固定合同。
2. 3 方向 × 2 变体生成 6 个创意母版（并行，统一前缀）。
3. 母版就绪后再出各自的 3 个比例版（母版未就绪不生成比例版，比例版间不互相引用）。
4. 交付 18 张清单并说明统一风格前缀、每张变体改动变量。

## 输出规范

- 标注 3×2×3（18 张）合同、每张变体改动变量、统一风格前缀摘要、目标平台规格；未提供的信息用合理默认并标注。