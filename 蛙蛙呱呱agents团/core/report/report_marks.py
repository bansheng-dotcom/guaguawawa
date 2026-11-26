# -*- coding: utf-8 -*-
"""core.report.report_marks —— 报告产线的**标记契约**（单一出处）。

2026-11-20 事故复盘：渲染器和门禁各自在源码里写死了标记字面量，
默认 flow 主题输出 `ex-src` / `class` 在前 / 附录排在口径之后，
而门禁只认 `fig-src` / `<section id="summary">` / 口径必须是末节——
于是**默认产线的产物永远过不了自己的门禁**，执行者只能要么走 paper 回退，
要么改门禁。两边都不该发生。

规则：任何判据标记只允许在这里定义一次；渲染器与门禁都必须 `import` 本模块，
禁止再写字面量。新增标记 = 改本文件 + 同步改判据 + 更新回归快照。
"""
from __future__ import annotations

# ---- 图表来源 -------------------------------------------------------------
# 判据只认规范类名。
FIGURE_SRC_CLASS = "fig-src"
# 旧主题（core/report_theme）用 ex-src 做样式；渲染时两个类一起挂，
# 这样 CSS 不用改、判据也不用放宽。**不要把 ex-src 写进判据。**
FIGURE_SRC_CSS_ALIAS = "ex-src"
FIGURE_SRC_CLASSES = f"{FIGURE_SRC_CSS_ALIAS} {FIGURE_SRC_CLASS}"

# ---- 边界 ----------------------------------------------------------------
BOUNDARY_ATTR = "data-label"
BOUNDARY_LABEL = "本节边界"

# ---- 结构 ----------------------------------------------------------------
SUMMARY_SECTION_ID = "summary"
CALIBER_TITLE = "口径与分数"
APPENDIX_TITLE = "记录层"

# 判据要求：每节都要有一条**非空**边界；图上来源文字至少这么长（去掉「来源：」后）
MIN_BOUNDARY_CHARS = 8
MIN_FIGURE_SOURCE_CHARS = 6
MIN_CALIBER_CHARS = 60


def figure_src_attr() -> str:
    """渲染器挂 class 用：`class="ex-src fig-src"`。"""
    return f'class="{FIGURE_SRC_CLASSES}"'


def boundary_attr() -> str:
    return f'{BOUNDARY_ATTR}="{BOUNDARY_LABEL}"'
