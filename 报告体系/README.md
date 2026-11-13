# reportkit · 保真交付工具链

> ⚠️ **本目录已归档（2026-11-12）**：这是报告内核的**原型 / 样例 / 验收证据**，不是生产入口。
> 生产内核在 `蛙蛙呱呱agents团/core/report_kernel`（入口 `python guagua.py report build/audit/seal/diff`）。
> 归档原因、保留内容与删除条件见 [归档说明.md](归档说明.md)。本目录的代码**不被任何地方 import**（全仓命中 0 处）。

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
  extras.py  三个补强：affected / 分区缓存 / 分级阈值
  cli.py     命令入口
cases/<case>/
  case.yaml      一页纸规格（品类/窗口/别名/维度阈值）
  store.sqlite   唯一事实源
  annotations.md 人写判断（按锚点挂载，带数据指纹）
  cache/         分区聚合缓存（按 YYYY-MM 分片）
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
| 弃置率 | 未进任何章节的观测 ÷ 总观测 | ≤5% 且有清单 | **1.85%**（22 条，已列 owner/due） |

规格覆盖率（热力图）当前 **37.5%**——**这是故意让它亮的**：鸭/鹅/虾与"成本与上游"维度确实没数据，红格就是待办。
阈值已按证据级分档（A 级 30 / B 级 4 / C 级 2），同一个数据用符合它证据级别的尺子量，红格只出现在"真的没有"的格子上。

## 八条规矩

1. 数字不进正文，只进 store；正文用 `{{key|fmt}}` 槽位。
2. 没有 obs 锚点的结论，不算结论。
3. 失败尝试必须单列（试过什么、为什么没拿到、下一步）。
4. 口径冲突必须单列（谁 vs 谁、差多少、怎么判）。
5. 弃置的观测要列清单，写 owner/due/method。
6. 同输入必同输出（确定性哈希）；改数据不影响 sealed。
7. 门禁不阻断，只亮灯（红格进热力图）。
8. 补数据只跑 `add-obs` + `build`，不许重写章节。

## 现状：已落地 vs 真缺口

**已落地**（原"还没做的"三条已全部补上，实证见《升级验收报告》附件一、二）

- **批注层**：`annotations.md` 按 `## s2-x` 挂载，每条带 8 位数据指纹；数据变了标 ⚠ 但不丢，改回原值后状态复原。
- **`affected` 命令**：改一个源 → 精确列出受影响的章节 / 结论 / 批注（未改数据时输出空，不产生噪声）。
- **分区 / 回填**：日度观测按 `YYYY-MM` 分片缓存，`backfill` = `add-obs` + `build`，只重算变化月份。1,192 条下价值在机制而非速度，上万条才体现收益。
- **分级阈值**：热力图按 grade 分档（A 30 / B 4 / C 2），覆盖率从 34.4% 升到 37.5%（含别名补全：育肥牛→牛肉、鲜蛋装车→蛋类、羔羊→羊肉）。

**真缺口**（诚实标注，别当成已完成）

- **结论仍是程序生成的规则句**：槽位机制已验证，但 5 条结论未接入人工撰写；批注区（4 条）是目前唯一的人写判断。
- **冲突 / 失败条目硬编码在 `add-obs`**：应由研究台账（R05 ledger）生成。
- **保留率的口径**：分母是"进了 store 的观测"。研究阶段根本没采到的数据不在分母里——它衡量"采到的有没有全用上"，不衡量"该采的是否采全"；后者靠覆盖率/热力图暴露（37.5%，即还差得远）。
- **剩余 20 个红/黄格是真实缺口**：区域只有 3 个市场（缺赤峰/包头/通辽周报，7 格）、上游报价仅 11 条产地（7 格）、鸭/鹅/虾无序列（6 格，需自建双周采价）。

> 定位提醒：本目录是**原型 / 样例 / 验收证据**，不是生产入口。报告内核已下沉到 `蛙蛙呱呱agents团/core/report_kernel`，正式入口是 `guagua.py report`；本包独立 CLI 按 v2 方案预留删除（退出条件：全仓 `grep "import reportkit"` 命中数为 0）。
