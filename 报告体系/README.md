# reportkit · 保真交付工具链

> 报告 = 数据的投影。一条命令重渲，晚到数据自动进报告；签发版带内容哈希，改数据不影响已签发版本。

## 快速开始

```bash
cd D:\蛙蛙呱呱\报告体系

python -m reportkit.cli init nmg_protein_2026Q4          # 建 case
python -m reportkit.cli add-obs nmg_protein_2026Q4 --preset nmg   # 灌观测
python -m reportkit.cli build nmg_protein_2026Q4         # 渲染（draft）
python -m reportkit.cli seal  nmg_protein_2026Q4 --build <id> --by 张三
python -m reportkit.cli diff  nmg_protein_2026Q4 --from <id1> --to <id2>
python -m reportkit.cli audit nmg_protein_2026Q4 --build <id>
python -m reportkit.cli annotate nmg_protein_2026Q4 --anchor s2-1 --text "人的判断……"
python -m reportkit.cli affected nmg_protein_2026Q4          # 改了源→列出受影响章节/结论/批注
python -m reportkit.cli backfill nmg_protein_2026Q4          # 重新灌数 + 只重算变化月份 + 重建
```

产物：`cases/<case>/out/report.html`、`builds/<id>/{report.html, manifest.json, diff.json, diff.html}`、`sealed/<id>-<hash>/`。

## 目录

```
reportkit/
  core.py    观测库 / 指标 / 快照 / 审计 / 差异
  render.py  三层结构渲染（摘要 / 分析 / 记录）+ 覆盖热力图
  cli.py     命令入口
cases/<case>/
  case.yaml      一页纸规格（品类/窗口/别名/维度阈值）
  store.sqlite   唯一事实源
  builds/        每次构建（含 manifest 与 diff）
  sealed/        签发版（内容哈希命名，取证用）
baselines/       历史交付的保留率基线
templates/       case 模板
```

## 三个核心指标

| 指标 | 算法 | 目标 | 当前 |
|---|---|---|---|
| 保留率 | 进报告的观测 ÷ 总观测 | ≥95% | **98.2%** |
| 溯源率 | 有 obs 锚点的结论 ÷ 总结论 | 100% | **100%** |
| 弃置率 | 未进任何章节的观测 ÷ 总观测 | ≤5% 且有清单 | **1.8%**（22 条，已列 owner/due） |

规格覆盖率（热力图）当前 34%——**这是故意让它亮的**：鸭/鹅/虾与"成本与上游"维度确实没数据，红格就是待办。

## 八条规矩

1. 数字不进正文，只进 store；正文用 `{{key|fmt}}` 槽位。
2. 没有 obs 锚点的结论，不算结论。
3. 失败尝试必须单列（试过什么、为什么没拿到、下一步）。
4. 口径冲突必须单列（谁 vs 谁、差多少、怎么判）。
5. 弃置的观测要列清单，写 owner/due/method。
6. 同输入必同输出（确定性哈希）；改数据不影响 sealed。
7. 门禁不阻断，只亮灯（红格进热力图）。
8. 补数据只跑 `add-obs` + `build`，不许重写章节。

## 还没做的（诚实标注）

- ~~批注层~~ **已实现**：`annotations.md` 按 `## s2-x` 挂载，每条带 8 位数据指纹；数据变了标 ⚠ 但不丢（见验收报告附件）。
- **`affected` 命令**（改一个源→列出受影响章节）未实现；目前靠 `diff` + 批注 ⚠ 人工定位。
- **分区/回填**未实现，补历史数据目前是全量重算（1,192 条，秒级，可接受）。
- 热力图阈值对 B/C 级品类偏严（鸭/虾/鹅天然达不到 A 级的 30 个观测），下一版按 grade 分档。
