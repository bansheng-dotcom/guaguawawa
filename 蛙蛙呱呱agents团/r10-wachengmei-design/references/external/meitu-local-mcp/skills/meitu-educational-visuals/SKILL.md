---
name: meitu-educational-visuals
description: Create education visuals: courseware covers/diagrams, picture-book illustrations, literacy cards, flashcards, wall charts, teaching posters and knowledge visuals for learners of all ages, following teaching-appropriate color/density rules and a series-consistency contract. Uses the meitu-local MCP `text-to-image` (no base, model nougat) and `image-edit` (with character/style baseline), plus `image-text-replace` for text polish. Use for courseware, picture-book visuals, flashcards, knowledge cards, teaching wall charts or educational infographics.
---

# 教学视觉 / 课件 / 绘本（educational-visuals）

把教学需求转化为高质量教学视觉资产：课件封面/知识可视化图、绘本插图、识字卡/单词卡、教学挂图、知识卡片。核心是"**清晰优先于美观、留白优先于堆砌、中性优先于强烈**"。

## 工具（`meitu-local` MCP Server）

- 无输入图/纯文字从零生成 → **`text-to-image`**（`model: nougat`）。
- 有参考图/角色/风格基线 → **`image-edit`**（`model: nougat`）。
- 画面文字精修/替换 → **`image-text-replace`**。
- 图片智能构图/扩图 → **`image-transform`**。
- 事实校对（科普/历史/真实人物）→ 检索后使用。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## 教学法框架

- 内容骨架有序：SCQA / 5W1H / KWL / 布鲁姆分类法，按内容类型选一。
- 受众难度分级决定信息密度与术语处理（零基础→必出定义+类比；业余→定义+简短背景；进阶→直接术语）。
- **知识真实性铁律**：事实须可追溯（用户材料/检索标注/常识级），否则标 `[需校对]`，禁止编造。

## 教学视觉调性

- 配色：主背景中性（灰/米白/浅蓝/浅绿），主文字深灰/深蓝，强调色单一柔和（蓝/绿/橙之一），禁多色彩虹/撞色/高饱和（饱和度≤70%）。
- 字体：无衬线为主，标题加粗/正文常规/辅助，≤3 档；禁用花字艺术字。
- 信息密度上限：思维导图 中心1+第一层≤7、概念图节点≤12、流程图步骤≤10、对比矩阵≤5×5、时间线≤8、分步≤6；超出拆多张。
- **宁可拆多张，不要一张挤满。**

## 绘本/图书一致性契约

- 图书形态：picture_book / flashcard / wall_chart / workbook_illustration / series_cover；介质 print（CMYK/出血/DPI≥300）/ digital / both。
- 调性分档（受众年龄）：early_childhood(3-6)/lower_grade(6-9)/upper_grade(9-15)/young_adult(15+)，对应配色、角色风格与文字密度。
- **角色基线契约**：凡含重复角色，先建 character sheet（正面+侧面+3 表情），后续所有页/卡复用同一基线，不得逐页独立重生成。
- 文字版式：默认 integrated（文字入画落在低影响区）；禁"上图下白条"或文字硬贴主角脸。
- 系列一致性：角色/画风/配色(3-5 色)/版式/字体/背景调性跨页一致。

## 角色基线与文字策略（知识库）

- **角色档案（character_bible）**：凡含重复角色的产物，先建角色名、关键特征、颜色提示、必出道具、性格/说话方式；再出角色 sheet（正面+侧面+3 表情）。
- 后续所有页/卡复用同一基线，不得逐页独立重生成。
- **图中文字生成**：短文（中英≤30 字）优先让模型直接画入画面；长文或字体一致性要求高时用占位符 + 排版工具补字。
- 正面/主体/关键道具上方禁止压文字；默认 integrated（文字落低影响区 + 留白衬底）。
- **装饰禁则**：禁用与知识无关的装饰图形（花纹、气泡、星星）、拟物化装饰、emoji、阴影/渐变/光效、营销符号；允许简洁箭头、单色线条、几何形状、必要图标。

## Prompt 8 要素（顺序）

1 产物类型 2 主体 3 动作/状态 4 环境/背景 5 构图 6 风格 7 光照/材质 8 图中文字（用户提供才写，否则 `no text`）。

## 工作流

1. 需求洞察：确认主题/学段/知识点/`media_form`/`output_medium`/`audience_age_band`。
2. 内容策划：选知识框架、规划结构大纲、定视觉风格与色彩体系、定信息密度。
3. 视觉生成：首张定基线（无参考图先出角色基线图）→ 后续 `image-edit` 引用基线并行生成；图片文字用 `image-text-replace` 精修。
4. 系列一致性检查 + 按介质交付（含 metadata）。

## 输出规范

- 课件输出含封面/目录/内容/总结页 + 设计说明；绘本输出含角色档案、逐页 brief、风格参考、交付规格声明；所有内容标注适用学段、教学目标与难度分级。