# R06 报告流水线（pipelines/）

本目录放**报告生成流水线**，与 `engines/`（L01~L10 演进元模型引擎）职责分离：

- `engines/` = 确定性分析/治理引擎，由 `agent.py evolve` 调度；
- `pipelines/` = 分析 → 组装 → 渲染的报告流水线，由 `agent.py deep` / `agent.py depth` 调度。

## 模块

| 模块 | 角色 | 入口 |
|---|---|---|
| `deep_analysis.py` | 七步深度分析链（质量→趋势→时序→拆解→下钻→分布→显著性） | 库，无 CLI |
| `deep_report.py` | 把七步链装配成 REP-001 深度决策报告（HTML + MD） | `agent.py depth`<br>`python pipelines/deep_report.py` |
| `consulting_analysis.py` | 商业咨询五支分析（损益杜邦/利润率结构/统计转译/情景/打法） | 库，无 CLI |
| `consulting_report.py` | 麦肯锡级咨询研报装配（12 栅格 + 10-0 质量审计） | `agent.py deep`<br>`python pipelines/consulting_report.py` |

## 依赖方向

```
pipelines/*  →  skills/（确定性技能） + agents/shared/（报告引擎） + core/charts（48 型 SVG）
agent.py     →  pipelines/（仅 deep / depth 两个子命令，懒加载）
```

`engines/` **不依赖** `pipelines/`；`pipelines/` **不依赖** `engines/`。两条链路互不缠绕。

## 约定

- 产物一律落 `workspace/`（`workspace/deep_report/`、`workspace/consulting_report/`），不写源码目录。
- 图表走 `shared/report_depth.py` → `core/charts`，角色内不保留私有图表库副本。
- 新增流水线模块请放本目录，并在 `agent.py` 注册一个子命令，避免出现「有代码没入口」的孤儿模块。
