# R08 前端与原型技术规格账本 (TECH_SPEC.md v1.0)
# 对标标杆：Style Dictionary / Design Token Community Group (DTCG) / awesome-design-md

## 一、 全局设计令牌基准 (Unified Design Tokens)

### 1. 调色板 (Color Tokens)
- **Primary (主色)**: `#3355FF` (用于核心 CTA、强调交互)
- **Primary Hover**: `#2544E0`
- **Secondary (辅色)**: `#FF5533` (用于次要行动、高亮标签)
- **Background (背景)**: `#F8FAFC` (低刺激浅灰背景，杜绝生硬纯白刺眼)
- **Surface (卡片表面)**: `#FFFFFF`
- **Text Main (主文本)**: `#0F172A` (高对比度深蓝黑，确保 A11y 对比度 >= 4.5:1)
- **Text Muted (次文本)**: `#64748B`
- **Border Default**: `#E2E8F0`
- **Success**: `#10B981`
- **Warning**: `#F59E0B`
- **Danger**: `#EF4444`

### 2. 排版系统 (Typography Scale)
- **font_family**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
- **h1**: `32px / line-height: 1.25 / font-weight: 700`
- **h2**: `24px / line-height: 1.3 / font-weight: 600`
- **h3**: `18px / line-height: 1.4 / font-weight: 600`
- **body**: `15px / line-height: 1.6 / font-weight: 400`
- **caption**: `12px / line-height: 1.5 / font-weight: 400`

### 3. 空间与网格 (Spacing & Layout Grid)
- **space_unit**: `4px`
- **gap_sm**: `8px`
- **gap_md**: `16px`
- **gap_lg**: `24px`
- **gap_xl**: `32px`
- **radius_sm**: `4px`
- **radius_md**: `8px`
- **radius_lg**: `12px`
- **radius_full**: `9999px`

---

## 二、 响应式视口断点规范 (Responsive Breakpoints)
- **mobile**: `375px` (iPhone/主流移动视口基准)
- **tablet**: `768px` (iPad/平板纵向基准)
- **desktop**: `1280px` (桌面端宽屏基准)
- **max_content_width**: `1200px`

---

## 三、 A11y 可达性与性能硬门禁 (Accessibility & Performance Gates)
- **对比度底线**: 正文与背景对比度必须 `>= 4.5:1`，大字与图标必须 `>= 3.0:1`；
- **交互热区底线**: 移动端可点击按钮/链接最小尺寸必须 `>= 44px * 44px`；
- **首屏资源约束**: 原型页面严禁引入重量级外部未锁定 CDN，总 JS+CSS 体积建议 `< 150KB`；
- **语义化标签**: 必须包含 `<main>`、`<nav>`、`<header>`、`<footer>`，表单控件必须具备 `<label>` 或 `aria-label`。

---

## 四、 跨平台映射规范 (Cross-Platform Alignment)
- **Flutter**: 映射为 `ThemeData`，主色对应 `ColorScheme.primary`，字体对应 `TextTheme`；
- **Tailwind / CSS**: 映射为 CSS Variables (`--color-primary`, `--space-md`) 或 `tailwind.config.js`；
- **Vue / React**: 导出为 TS Token 字典 `const tokens = {...}`。
