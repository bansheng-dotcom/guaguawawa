# 图表能力升级 SOP：把「满血图」接进当前生产线

> 适用对象：负责 `core/charts`、`core/report_renderer.py`、报告流水线的工程师。
> 目标：报告里的每一张图，默认就是满血图，而不是"能画出来的最简图"。
> 版本：2026-11-15 · 配套交付物 `workspace/图鉴-满血_2026-11-15/`

---

## 0. 一句话结论

问题不在"模型不会画"，在**渲染层只接了 18 型**，剩下 30 型在报告里被静默回退成 v1 的素图；
而这个回退是 `except: pass`，报告里看不出来，所以每轮都在"以为画了、其实画素了"。

升级的本质是三件事：**补齐 30 型、把回退变成可计数、把"满血度"变成门禁**。

---

## 1. 现状盘点（实测，可复核）

| 层 | 文件 | 现状 | 问题 |
| --- | --- | --- | --- |
| 能力注册 | `core/chart_capabilities.py` | 48 型全部注册，`--check` 报 48/48 | 只证明"能画"，不证明"画得好" |
| v1 渲染 | `core/charts/chart_lib.py` | 48 型手写 SVG | 刻度按数据极值均分（2,815 这种）、无标注体系、卡片描边 |
| v2 渲染 | `core/charts/v2/` | **18 型** matplotlib，研报级几何 | **缺 30 型**，报告里这 30 型必然回退 |
| 调度 | `core/report_renderer.py:1407` `render_chart()` | `engine=="v2"` 先试 v2，失败回退 v1 | `:1416-1417` 是 `except Exception: pass`，**静默** |
| 契约默认 | `core/report_modules.py:201` | `chart_engine` 默认 `"v2"` | 默认值是 v2，但 30 型拿不到 |
| 回滚开关 | `core/report_renderer.py:1477` | `chart_engine or env or ""` | 契约显式写 `v2`，**环境变量永远不生效**，等于没有回滚开关 |

实测命令与输出：

```bash
python -X utf8 scripts/check_chart_v2_coverage.py
# v1 48 型 / v2 18 型 / 覆盖 18 / 缺 30
```

缺的 30 型：

```
box bubble bullet cal_heatmap candlestick choropleth control dual_axis
error_bar forest funnel gantt gauge geo_flow histogram kpi_break network
parallel pct_stacked radar ridgeline rose sankey scatter streamgraph
sunburst symbol_map target_band violin waffle
```

> 补充事实：v2 的 18 个 key 只对应 16 个实现（`lollipop→dot`、`bridge→waterfall` 共用一个函数）。
> 迁移时不要按"18 个函数"估工，要按"30 型 × 各自的图形几何"估。

---

## 2. 目标态与验收（DoD）

| 编号 | 指标 | 判定方式 | 目标 |
| --- | --- | --- | --- |
| G1 | v2 覆盖 | `check_chart_v2_coverage.py --strict` | 48/48，exit 0 |
| G2 | 静默回退 | CI 跑 fixtures 全量出图，统计 fallback 次数 | **0 次** |
| G3 | 满血度 | `check_chart_fullness.py` 对每张图的 spec 打分 | 六要素 ≥4/6 |
| G4 | 视觉基线 | 每型 PNG 与基线比对（hash 或 SSIM≥0.995） | 100% 通过 |
| G5 | 排版回归 | 同一份报告 PDF 页数、图宽（980px）、A4 内容宽 | 不回归 |

**六要素**（就是这个图鉴里每张图都带的）

1. 结论式标题（含数字）
2. 口径副标题（时间 / 样本量 / 单位 / 可比范围）
3. 直接标注（端点、柱顶、段内数值）
4. 一条参考线（目标 / 均值 / 基准 / 控制限 / 0 线）
5. 异常归因（离群点、转折点、越界点一句人话）
6. 来源 + 图注

---

## 3. 六步流程

### P0 · 冻结基线（0.5 天）

**做什么**：在动任何代码前，把"现在的样子"存成可比对的快照。

```bash
cd 蛙蛙呱呱agents团
python -X utf8 scripts/check_chart_v2_coverage.py --json > workspace/chart_v2_baseline.json
python scripts/chart_gallery_v2.py                    # 18 型现状画廊
python -X utf8 scripts/grade_report_level.py --dir workspace/all_role_reports
# 取一份真实报告，HTML + PDF 各存一份到 workspace/chart_baseline/
```

**产出**：`workspace/chart_v2_baseline.json`、`workspace/chart_baseline/*.{html,pdf,png}`

**验收**：基线文件齐全，`baseline.json.missing` 恰好 30 条。

**失败回退**：无（只读操作）。

---

### P1 · 移植绘图内核（1 天）

**做什么**：把图鉴里那套 `Card`（标题/副标题/单位/来源/图注 + 固定几何）搬到 v2，
并强制"颜色只能从 theme 取"。

**新增文件**

| 文件 | 内容 |
| --- | --- |
| `core/charts/v2/card.py` | `Card` 类：`canvas()` 的薄封装，带 subtitle / note；`svg()` / `png()` |
| `core/charts/v2/marks.py` | 原子图元：`bar_h` `bar_v` `dot` `ref` `band` `callout` `delta_tag` `ribbon` `kde` `squarify` |

**硬约束**（写进 CI）

- 渲染器里**禁止**出现 `"#RRGGBB"` 字面量，一律走 `tokens(theme)`；
- 图宽固定 980px，标题 13px，单位右上 9.6px，来源左下 8.4px（与现有报告图卡对齐）；
- 不使用 3D、渐变、阴影、彩虹色（沿用 `docs/` 里既有的视觉纪律）。

**验收**：`card.py` 能画出 v2 现有的 3 张图（hbar / line / waterfall），像素级与 v2 原实现一致（SSIM>0.99）。

**失败回退**：P1 不动 `RENDERERS`，报告行为零变化。

**参考实现**：`workspace/图鉴-满血_2026-11-15/kit.py` + `kit_extra.py`，
`Card.__init__` 就是适配 `canvas()` 的那 20 行（见附录 A）。

---

### P2 · 分四批迁移 30 型（3 天）

每批一个 PR，批内 6–8 型，**批批可上线**（未迁的仍走 v1，不阻塞）。

| 批次 | 图型（8 型） | 依赖数据 |
| --- | --- | --- |
| B1 分布与关系 | `pct_stacked` `histogram` `box` `violin` `ridgeline` `scatter` `bubble` `parallel` | 样本分布、双变量、多维记录 |
| B2 统计与过程 | `error_bar` `forest` `control` `funnel` `bullet` `gauge` `target_band` `dual_axis` | 均值±CI、效应量、时间序列、目标 |
| B3 时间与流转 | `cal_heatmap` `gantt` `candlestick` `sankey` `streamgraph` `kpi_break` `waffle` `rose` | 日序列、OHLC、流程节点、多期结构 |
| B4 空间与网络 | `choropleth` `symbol_map` `geo_flow` `network` `sunburst` | 盟市维度、OD 流、关联规则、层级树 |

**每批的操作序列**

```bash
# 1) 新建渲染模块
#    core/charts/v2/types_b1.py … types_b4.py（每型一个函数 fn(chart, theme) -> svg）
# 2) 在 core/charts/v2/__init__.py 的 RENDERERS 里注册
# 3) 在 __init__.py 的 _normalize / _is_valid 里补该型的字段清洗与"数据够不够"判定
# 4) 出图
python -X utf8 scripts/chart_gallery_v2.py            # 画廊扩到 48 型
python -X utf8 scripts/check_chart_v2_coverage.py     # 覆盖率应逐批 +6~8
# 5) 目检：联系表（每批 6–8 张拼一张，看标题/标注/遮挡）
```

**每批验收（4 条全绿才合并）**

1. `check_chart_v2_coverage.py --json` 的 `covered` 增加，`missing` 减少，无新增 `extra_in_v2`；
2. 该批图型在 `chart_gallery_v2.py` 画廊里出图成功（失败返回 `None` 即视为不合格）；
3. 联系表目检：无标题压图、无标签互压、无空图；
4. 抽 1 张真实报告里的同类图，替换后与原图并排对比，结论句不变、信息量增加。

**失败回退**：删掉该批注册即可（v1 仍在），不影响已合并批次。

---

### P3 · 打通报告层（0.5 天）

这一步决定"图鉴里的图"能不能原样出现在报告里。

**改 3 处**

1. **`_embed` 双模式**（`core/charts/v2/base.py` 已有 `EMBED`）：
   - 报告内：`_embed=True` → 图里不画标题/单位/来源（图卡外框已经有）；
   - 独立查看：`_embed=False` → 画全。
   迁移的每个渲染器都必须**同时支持两种**，否则单独出图会缺标题。

2. **副标题进图卡**：报告图卡目前只有标题/单位/来源，没有"口径副标题"。
   在 `core/report_renderer.py` 的图卡模板里加一行 `chart.get("subtitle")`，
   或者在 `_embed=True` 时把它画在绘图区上方 9.6px 处（图鉴里的做法）。

3. **回滚开关修正**（`core/report_renderer.py:1477`）：

   ```python
   # 旧：契约显式写 v2 时，环境变量永远不生效
   engine = str(c.get("chart_engine") or os.environ.get("GUAGUA_CHART_ENGINE") or "")
   # 新：环境变量优先，才能一键回滚
   engine = str(os.environ.get("GUAGUA_CHART_ENGINE") or c.get("chart_engine") or "")
   ```

**验收**：`GUAGUA_CHART_ENGINE=v1` 跑同一份报告 → 出的图与 P0 基线一致；
不设变量 → 出的图是满血版。

---

### P4 · 上闸门（1 天）

把"应该"变成"必须"。

**新增 3 个门禁**

| 门禁 | 文件 | 判定 |
| --- | --- | --- |
| 覆盖率 | `scripts/check_chart_v2_coverage.py --strict`（已随本 SOP 提供） | 48/48 |
| 零静默回退 | `scripts/check_chart_fallback.py` | fixtures 全量出图，fallback == 0 |
| 满血度 | `scripts/check_chart_fullness.py` | 每图六要素 ≥4/6 |

**满血度怎么算**（可直接实现）

```python
def fullness(chart: dict) -> tuple[int, list[str]]:
    hit, miss = 0, []
    t = str(chart.get("title") or "")
    if any(ch.isdigit() for ch in t):      hit += 1
    else: miss.append("标题无数字")
    if chart.get("unit_meta"):             hit += 1
    else: miss.append("无单位")
    if chart.get("source"):                hit += 1
    else: miss.append("无来源")
    if chart.get("required_annotations"):  hit += 1
    else: miss.append("无标注")
    if chart.get("ref") or chart.get("target") or chart.get("baseline"):
        hit += 1
    else: miss.append("无参考线")
    if chart.get("annotations") or chart.get("note"):
        hit += 1
    else: miss.append("无归因/图注")
    return hit, miss
```

**静默回退怎么变成可计数**（改 `report_renderer.render_chart`）

```python
_FALLBACKS: list[str] = []          # 模块级计数器

def render_chart(chart, theme="sticker", engine=""):
    if str(engine) == "v2":
        try:
            from core.charts.v2 import render as v2_render
            svg = v2_render({**chart, "_embed": True}, theme)
            if svg:
                return svg
            _FALLBACKS.append(chart["type"])
        except Exception:
            _FALLBACKS.append(chart["type"])
    ...  # v1 路径不变
```

CI 里跑完 fixtures 断言 `len(_FALLBACKS) == 0` 并打印清单——
**回退从"静默"变成"看得见的一条线"**，这是这次升级最关键的一步。

**挂进 CI**：`scripts/ci_upgrade_checks.py` 的 `checks` 列表加 3 项（P2 全部合并后再加，否则一直红）。

---

### P5 · 灰度与收口（0.5 天）

1. 选 1 个角色（建议 `r06-wadeqing-analyst`）的一份真实报告，切新引擎出 HTML + PDF；
2. 与 P0 基线并排比：页数、图宽、标题是否仍为结论句、有没有标签压图；
3. 通过后全量切；保留 `GUAGUA_CHART_ENGINE=v1` 一周；
4. 一周后删除 v1 分支（`chart_lib.py` 保留为"兜底渲染器"，但 CI 断言命中数 == 0）。

---

## 4. 文件级改动清单

| 文件 | 动作 | 说明 |
| --- | --- | --- |
| `core/charts/v2/card.py` | 新增 | Card + 几何常量 |
| `core/charts/v2/marks.py` | 新增 | 原子图元（柱/点/线/带/标注/河流/树图） |
| `core/charts/v2/types_b1.py` … `types_b4.py` | 新增 | 30 型渲染器 |
| `core/charts/v2/__init__.py` | 改 | `RENDERERS` 补 30 项；`_normalize` / `_is_valid` 补字段 |
| `core/charts/v2/base.py` | 改 | `EMBED` 双模式 + subtitle/note 支持 |
| `core/report_renderer.py` | 改 | 回退计数、env 优先、图卡加副标题 |
| `core/chart_capabilities.py` | 改 | `check()` 增加"v2 覆盖"字段（不影响 48/48 语义） |
| `core/chart_spec.py` | 改 | `REQUIRED` 增加"满血度"相关必填（见 §5） |
| `scripts/check_chart_v2_coverage.py` | 新增 | 已提供 |
| `scripts/check_chart_fallback.py` | 新增 | P4 |
| `scripts/check_chart_fullness.py` | 新增 | P4 |
| `scripts/chart_gallery_v2.py` | 改 | 样本从 16 型扩到 48 型 |
| `scripts/ci_upgrade_checks.py` | 改 | 加 3 个门禁 |

---

## 5. 每型的 schema 契约（数据不够就不许画）

沿用 `core/chart_spec.py` 的"缺什么不画"原则，迁移时把每型的**最小字段**写进 `_is_valid`：

| 图型 | 必需字段 | 缺了怎么办 |
| --- | --- | --- |
| `scatter` | `x` `y`，≥8 个点，数值型 | 回退 hbar（退化成单变量比较） |
| `bubble` | `x` `y` `size` | 回退 scatter |
| `box` / `violin` / `ridgeline` | 每组 ≥20 个原始值 | 回退 bar（只报均值） |
| `histogram` | ≥50 个样本 | 回退 bar |
| `forest` | 效应量 + 区间上下限 | 不出图（缺 CI 不能画森林图） |
| `control` | ≥20 期序列 | 回退 line（不出控制限） |
| `sankey` | 节点 + 流量，且每层流量守恒（±2%） | 不出图 |
| `gantt` | 任务 + 起止 | 回退表格 |
| `candlestick` | OHLC 四列 | 回退 line（收盘价） |
| `cal_heatmap` | 日期 + 值，≥90 天 | 回退 line |
| `choropleth` / `symbol_map` / `geo_flow` | 地区编码 + 值（映射表存在） | 回退 hbar，并注明"无地理维度" |
| `network` | 节点 + 边权 | 回退 hbar |
| `sunburst` | 至少两层层级 | 回退 treemap（一层） |
| `kpi_break` / `dual_axis` / `target_band` | 两套同频序列 / 目标值 | 回退单轴 |

**原则**：能降级就降级并**在图注里写明降级原因**，不能降级就不出图——绝不出一张"看起来像图但没说清"的图。

---

## 6. 三条硬规则（防"最简图"复发）

**R1 数据够就必须用够。**
有 ≥24 个时间点 → `line`/`area` 必须带移动平均或转折点标注；
有 ≥3 个品类 × ≥6 期 → 优先 `small_mult` 或 `stacked`，不许退成单序列柱状图。

**R2 每张图至少有一个"锚"。**
一条参考线，或一个异常归因标注，或一个目标带。三样全无 → 门禁不通过。

**R3 选择器按"信息密度"排序，不按"能画"排序。**
`report_chart_selector` 的候选打分里加一档：同等数据条件下，
能表达更多维度的图型优先（`scatter>bubble` 同分时选 bubble；`line>vbar` 同分时选 line）。

---

## 7. 门禁命令清单（复制即用）

```bash
cd 蛙蛙呱呱agents团

# 能力不退化（旧口径）
python -m core.chart_capabilities --check                      # 期望 48/48

# 新增：v2 覆盖率
python -X utf8 scripts/check_chart_v2_coverage.py              # 人看
python -X utf8 scripts/check_chart_v2_coverage.py --strict     # CI（P4 起）

# 新增：零回退 + 满血度（P4）
python scripts/check_chart_fallback.py
python scripts/check_chart_fullness.py --min 4

# 视觉基线
python scripts/chart_gallery_v2.py
python -X utf8 scripts/grade_report_level.py --dir workspace/all_role_reports

# 全量自检（提交前六条，沿用仓库既有规范）
python guagua.py check
python scripts/check_skill_gate.py
python scripts/audit_skill_layer.py --check-refs
python scripts/gen_agent_packs.py --check
python scripts/check_threshold_consistency.py
python scripts/sync_dsh_skills.py --check
```

---

## 8. 回滚预案

| 触发条件 | 动作 | 恢复时间 |
| --- | --- | --- |
| 某批图型上线后 PDF 排版错乱 | 删该批 `RENDERERS` 注册，重跑报告 | 5 分钟 |
| 全量切换后大面积异常 | `set GUAGUA_CHART_ENGINE=v1`（P3 后生效） | 1 分钟 |
| 字体缺失导致方块字 | 回滚 + 在 `theme.figure_style()` 的 `font.sans-serif` 里补字体栈 | 10 分钟 |
| SVG 体积撑爆单文件 HTML | 该批改用 `svg.fonttype="path"` 之外的内联策略，或降为 PNG | 1 小时 |

> 注意：**P3 之前** `GUAGUA_CHART_ENGINE` 不生效（见 §1 表格最后一行），
> 所以 P5 灰度必须在 P3 完成之后做。

---

## 9. 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 30 型 × 每型 40–60 行，工期被低估 | 拖成两周 | 按批次交付，每批可独立上线；单批不超过 8 型 |
| 复杂图（sankey/sunburst/network）几何写错 | 出"看着像但你读不懂"的图 | 每型必须过"三秒测试"：不看正文，3 秒内能不能说出这张图在说什么 |
| 字体在服务器缺失 | 中文方块 | 渲染前 `font_manager.findfont()` 自检，缺失直接报错不出图 |
| SVG 体积（48 图 × 30–60KB） | HTML 3–5MB | 已实测：48 图单文件 838KB（`svg.fonttype=none`，文本可选中） |
| 数据不够时硬画 | 误导 | §5 的 `_is_valid` 降级表 + "不出图"兜底 |
| 迁移期间两套风格并存 | 报告里图文风格不一致 | 按批次切，一次只切一批；不同批次之间不混排在同一份报告 |

---

## 10. 排期与分工（1 人 / 6–7 个工作日）

| 阶段 | 工时 | 产出 | 负责人 |
| --- | --- | --- | --- |
| P0 基线冻结 | 0.5 d | 基线快照 + 覆盖率 JSON | 提出人 |
| P1 内核移植 | 1 d | `card.py` `marks.py` | 图表工程师 |
| P2 B1–B4 | 3 d | 30 型渲染器（4 个 PR） | 图表工程师 |
| P3 报告层 | 0.5 d | `_embed` / 副标题 / 回滚开关 | 报告工程师 |
| P4 门禁 | 1 d | 3 个脚本 + CI 接入 | 提出人 |
| P5 灰度 | 0.5 d | 全量切换 + 观测 | 报告工程师 |

---

## 附录 A：`Card` → `canvas()` 适配（P1 的核心 20 行）

```python
# core/charts/v2/card.py
from matplotlib.figure import Figure
from .base import W, canvas, svg_of
from .theme import figure_style, tokens

class Card:
    """一张图卡：结论标题 + 口径副标题 + 单位 + 来源 + 图注 + 绘图区。"""

    def __init__(self, height=320, *, title="", subtitle="", unit="", source="",
                 note="", pad_l=96, pad_r=84, pad_t=54, pad_b=46, theme="paper"):
        self.T = tokens(theme)
        self.fig, self.ax, _ = canvas(height, theme, title, unit, source,
                                      pad_l=pad_l, pad_r=pad_r, pad_b=pad_b, pad_t=pad_t)
        h = height
        if subtitle:
            self.fig.text(2.0 / W, 1.0 - 33.0 / h, subtitle,
                          ha="left", va="top", fontsize=9.6, color=self.T["muted"])
        if note:
            self.fig.text(1.0 - 2.0 / W, 4.0 / h, note,
                          ha="right", va="bottom", fontsize=8.4, color=self.T["faint"])

    def __getattr__(self, item):
        return getattr(self.ax, item)

    def svg(self):
        return svg_of(self.fig)
```

要点：`canvas()` 已经处理了 `EMBED`（报告内不重复标题）、几何与字体；
`Card` 只补 subtitle/note 两行字。**不要另造一套画布**，否则报告里的图对不齐。

---

## 附录 B：PR 模板（每批迁移复用）

```markdown
## 本批迁移（B? · 8 型）

- [ ] 新增 types_b?.py，8 个渲染器
- [ ] RENDERERS 注册 8 项，_normalize/_is_valid 同步
- [ ] `check_chart_v2_coverage.py --json`：covered 18 → 26，missing 30 → 22
- [ ] 画廊出图 8/8 成功（无 None）
- [ ] 联系表目检：无标题压图 / 标签互压 / 空图
- [ ] 抽 1 张真实报告图对比：结论句不变，信息量增加
- [ ] `python -m core.chart_capabilities --check` 仍 48/48

回滚方式：删除本批 8 项注册。
```

---

<!-- origin-anchor: 不知渭河 -->
