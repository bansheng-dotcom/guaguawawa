# 渭河报告 Agent + 图表提示词库：学习与融合

> 输入：`渭河数据分析报告agent.zip`、`数据分析可视化图片提示词.zip`  
> 结论：这两个不是“模板”，是**报告生产流水线**和**48 种图的施工规范**。  
> 我当前系统缺的正是这两层：图表 spec 契约、文字/图表对抗审查。

## 1. 渭河 Agent 的六段流水线

```text
原始数据 + 业务问题
  → ReAct 分析（证据、驱动、反证）
  → Chart Spec Agent（图表规格 + claim_to_prove）
  → Report Text Controller（单元 packet + Chain of Verification）
  → Text Editor（结论句）
  → Adversarial Reviewer（独立挑战）
  → Report Assembler（图文仲裁）
  → HTML Renderer
```

关键不是“多 Agent”，是**每一步都有契约和回退**：

- 图表发现证据不足 → 退回分析层补数；
- 文字与图不一致 → 退回图表/文字；
- 没报告价值 → 直接 omitted，不硬写；
- 证据有限但有用 → 进 `bounded_modules`，可拆卸，不放进主结论。

## 2. 图表 Spec 的硬字段

每个图必须有：

| 字段 | 作用 |
|---|---|
| `claim_to_prove` | 这张图要证明哪句话 |
| `required_series` | 必须出现的完整数据域，不是只画高亮段 |
| `required_annotations` | 起止值/差值/目标线/异常点/样本量 |
| `focus_metric` | 读者 5 秒内该看什么 |
| `unit` / `time_scope` / `comparison_basis` | 口径 |
| `source_evidence` | 数据来源 |
| `fail_if_missing` | 缺什么就不许画 |
| `visual_check` | 碰撞、遮挡、可读性检查 |

这直接解释了我之前的错误：

- R15 用 dumbbell，货值 9.5 万把物流 3 千压成看不见 → 没有 `focus_metric`；
- R20 用 Gantt 画 42 分钟 → 没有 `time_scope` 适配；
- 20 份全是 current vs target → 没有 `claim_to_prove`，只是装饰。

## 3. 48 种图的施工规范

`数据分析可视化图片提示词.zip` 的 `prompts/` 是 48 张图的“怎么画/怎么检查”：

- 27 waterfall：起点 + 贡献项 = 终点；每项标正负值；加总对不上就停止作图；
- 45 contribution bridge：左桥图解释净变化，右排名条解释优先级；两图同口径；
- 24 error bar：必须明确 SD/SE/CI，不能只有均值；
- 28 pareto：排序 + 80% 线；
- 33 gantt：只适合天级任务；
- 44 target band：目标区间；
- 48 small multiples：2—6 格，共享尺度。

这些规则比“48 个图型名字”有用得多。

## 4. 文字流水线的硬规则

- 可见正文 = **完整结论句序列**，不是“证据/结论/边界”标签；
- 每个 unit 只回答一个图/表问题；
- Chain of Verification 先问“分子/分母/对比/驱动/反证/边界”，再写；
- 驱动必须做 `driver_decomposition`，时间模式不等于驱动；
- 文字与图互相支持，不互相复述；
- 证据不足 → bounded module 或 omitted，不凑字数；
- 对抗审查独立，不允许 writer 自审。

## 5. 我们要吸收 / 不吸收

### 吸收

1. `claim_to_prove` 进每张图；
2. `required_series` 完整数据域；
3. `required_annotations`：起止/差值/目标/样本量；
4. `fail_if_missing`：缺数据不画；
5. 文字只写结论句，不写“这一层要回答”；
6. 图文仲裁：图不证明文字，就退回；
7. 证据不足进 bounded module，不硬写。

### 暂不吸收

- 六 Agent 全套运行时（我们不需要为 20 份报告起 6 个模型）；
- 复杂 manifest/temperature 控制；
- 把所有验证字段暴露到可见正文。

## 6. 已落地

- R15：A→B TCO 桥，起点/终点/每项差值，加总回到 B；
- R20：42 分钟用 waterfall，不用 Gantt；
- R19：评测结论挂 p 值/失败样本，不画没有 CI 的误差线；
- [CHART_CRAFT_STUDY.md](CHART_CRAFT_STUDY.md) 增补了这些规则。

## 7. 下一步

把 `claim_to_prove / required_annotations / fail_if_missing` 写进 `report_chart_selector` 和 `report_renderer` 的图表契约；没有这三个字段的图，不允许进正式报告。
