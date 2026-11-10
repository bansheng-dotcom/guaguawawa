# 一 人公司 · 报告「厚度 + 深度」标准（DSH-SOP-DEPTH-001）

> 适用范围：全量 20 个角色智能体
> 触发背景：能力执行很全面，但出报告只有三段文字 + 一张小表，**看得懂、但不足以支撑决策**
> 现行样板：R06 蛙得清（`deep_analysis.py` + `deep_report.py`）

---

## 一、问题定性（先承认，不粉饰）

| 症状 | 具体表现 | 根因 |
| :--- | :--- | :--- |
| **厚度不足** | 一份 MD 只有几百字；HTML 没有一张图；没有附录、没有明细表 | 报告只取「一个技能的一次结果」，没有把同一次执行里的多维证据用起来 |
| **深度不足** | 只给「是什么」，不给「为什么」；没有下钻、没有显著性、没有边界声明 | 分析链路只走了一步，没有串成 体检→趋势→拆解→下钻→分布→检验 的链条 |

**判定口径（可量化，避免自说自话）**

* 厚度：HTML ≥ 25KB 且内嵌 ≥ 3 张 SVG；MD ≥ 6KB。
* 深度：分析小节 ≥ 5 节；三级归因 L1/L2/L3 齐备；附录至少 1 份原始明细。

---

## 二、解决方案：把「一次技能」升级为「一条分析链」

### 2.1 六步深度链（R06 已落地）

```text
① 质量体检  quality.audit         → L1 真实性门禁（缺失/重复/离群六维打分）
② 时间趋势  explore.trend         → 折线图 + 首末变化 + 极值期
③ 时序诊断  explore.time_series   → 斜率 / 季节强度 / 异常点（3×MAD 带）
④ 结构拆解  rootcause.decompose   → 瀑布图 + 贡献度表（谁在拉动总变化）
⑤ 集中度    rootcause.drilldown   → 帕累托图 + 80/20 结论
⑥ 分布形态  describe              → 直方图 + 偏度 / 分位（均值能不能代表）
⑦ 显著性    anova                 → F 值 / η²，区分「真实差异」与「噪声」
```

每一步都必须调**角色自己的技能模块**，不复制计算逻辑；任一步失败只降级该节并写明原因，**绝不编数字**。

### 2.2 共享层三件套（一次改造，全角色复用）

| 模块 | 职责 | 关键 API |
| :--- | :--- | :--- |
| `agents/shared/report_depth.py` | result → 图表 spec 的确定性投影，复用 `core/charts` 48 型 SVG | `line_from_series` / `waterfall_from_segments` / `pareto_from_items` / `grouped_bar_from_groups` / `histogram_from_values` / `scatter_from_pairs` / `slope_from_two_periods` |
| `agents/shared/report_generator.py` | 新增 `figures`（图表区）与 `appendix`（附录）两个入参 | `generate_professional_report(..., figures=[...], appendix=[...])` |
| 角色侧 `deep_*.py` | 串分析链 + 装配 REP-001 规格 | R06：`deep_analysis.analyze()` + `deep_report.build()` |

**降级纪律**：图表渲染失败 → 自动落回同源表格 + 一条 ⚠️ 说明；报告整体照常出具，不因一张图炸掉。

---

## 三、R06 落地效果（真实数字）

| 指标 | 改造前 | 改造后 |
| :--- | ---: | ---: |
| Markdown 字节 | 868 B | **9,544 B** |
| HTML 字节 | 19 KB（无图） | **32,120 B** |
| 内嵌 SVG 图表 | 0 | **3**（趋势折线 / 归因瀑布 / 帕累托） |
| 分析小节 | 1 | **6** |
| 附录（审计明细） | 0 | **1**（质量六维原始读数） |
| MD 章节 | 3 | **9**（连续编号，无断号） |

**一个真实结论示例**（可直接复算）：
2025-09 → 2025-10 利润总变化 −44,000，按园区拆解后 **C 区贡献 97.73%（−43,000）**，其余三类为 minor（< 3%）可停止下钻——这句话以前写不出来，因为没有跑 decompose。

---

## 四、复现命令

```powershell
cd <repo>/r06-wadeqing-analyst
$env:PYTHONPATH = "<repo>"
python deep_report.py --input workspace\parking_profit_12m.csv `
  --decompose-input workspace\parking_profit.csv `
  --value profit --date month --dim zone --period month `
  --before 2025-09 --after 2025-10 `
  --intent "停车场 12 个月利润结构诊断"
```

产物：`workspace/deep_report/deep_report.html` + `.md`
回归：`python -m pytest tests -q`（含 `test_deep_report.py` 四条断言，防报告变薄）

---

## 五、其余 18 个角色怎么复制（三句话）

1. **选链**：按角色能力域选 5~7 个技能串成「体检 → 主分析 → 下钻 → 检验 → 边界」链条。
2. **投影**：用 `report_depth` 把每步结果转成图 spec + 表格 + 一句可复算结论。
3. **门禁**：照抄 `tests/test_deep_report.py`，把「图表数 ≥ 3、小节 ≥ 5、附录非空、无乱码」写成断言，防止后续改回薄报告。

---

## 六、红线（与 REP-001 一致，不得突破）

1. ❌ 图表坐标、表格数字**只能来自技能真实输出**，不得编造示意数据。
2. ❌ 不得用「大幅提升 / 表现良好」等无锚定形容词填充厚度。
3. ❌ 不得为了凑图表把失败项藏起来——失败项必须单独成节并给出补证动作。
4. ❌ 不得跳过 L1 真实性门禁直接做归因（先证明是真实异动，再谈原因）。
