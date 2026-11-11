---
name: dbt-unit-test
description: 数据管道建模与测试技能包。把"数据能不能信"做成可校验的三件套：模型分层与物化策略合法（staging/intermediate/mart）、每张模型有对应数据测试（唯一/非空/枚举/关联）、DAG 无环且依赖显式，并对增量策略与回填做前置校验。当需要建数据模型、加数据测试、排查管道依赖、或判断一条管道能不能上生产时使用。不负责出分析结论、不做业务口径定义、不替代数据质量审计。
license: MIT
compatibility: 通用。门禁在角色根目录 harness.py（model / test / dag 三道，Python 3.10+、零第三方依赖）；无 Python 环境时按 §8 转人工八项核对，此时不得标记「可上生产」。
metadata:
  owner: r18
  version: "2.0.0"
  kind: skill
  triggers: "数据模型,物化策略,数据测试,分层,DAG,依赖,增量"
  verify: python harness.py model --input <数据模型.json>
  entry: "python agent.py transform model"
  consumers: "r06,r19,r20"
  supersedes: README.md
---

# 数据管道建模与测试（dbt Unit Test）

> 一句话定位：**这个技能存在的意义，是防止"管道跑通了，但数据没人敢用"**。
> 数据管道最贵的失败不是跑挂，而是**静默出错**：
> 物化策略用错导致全表重算、主键不唯一导致行数翻倍、枚举多了个新值没人知道、DAG 出现环跑到一半卡死。
> 这些都不会报错，只会让下游拿到一份看起来正常、实际已经坏掉的数据。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「这张表怎么建」「该用 view 还是 table」
- 「加几个数据测试」「怎么保证主键唯一」
- 「这条管道能不能上生产」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 判断数据质量（缺失/重复率） | `r06` 的 `data-validation` | 那是数据本身的质量，不是模型定义 |
| 出业务分析结论 | `r06` 分析师 | 本技能只管建模与测试 |
| 配调度与告警 | `r20` 值守 / `r18` ops 域 | 本技能只出模型与测试定义 |
| 定义指标口径 | `r06` / `r18` 语义层 | 口径属指标语义建模 |

**最小可开工输入**：**一张模型的定义**（名字 + 来源 + 物化方式 + 粒度）。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| 模型名与粒度（一行代表什么） | 必需 | 粒度不明即无法定主键，必须问 |
| 来源表/上游模型 | 必需 | 缺则无法建依赖 |
| 物化方式（view/table/incremental/ephemeral） | 必需 | 缺则按分层默认，并标注 |
| 主键 | 必需 | 缺则测试无法定义唯一性 |
| 唯一键变更预期（增量策略） | 增量时必需 | 缺则标"未声明去重策略" |

**追问纪律**：最多一轮，只问**粒度是什么、主键是什么**。其余按分层规范默认并标注。

---

## §3 执行流水线（Workflow）

### Step 1 · 定粒度（一行代表什么）
写清"一行 = 一个订单 / 一个用户一天 / 一个 SKU 一个仓"。
**粒度写不清，主键必然错，唯一性测试也就无从谈起。**

- **产出**：粒度声明
- **过关条件**：能用一句话说清，且能据此定出主键

### Step 2 · 分层与物化策略（用错会全表重算）
```bash
python harness.py model --input <数据模型.json>
```
| 层 | 职责 | 默认物化 | 不该做的 |
|---|---|---|---|
| `staging` | 对齐上游、重命名、类型转换 | `view` | 不做聚合、不做业务逻辑 |
| `intermediate` | 中间聚合与连接 | `view` / `ephemeral` | 不直接给业务用 |
| `mart` | 面向分析/应用 | `table` | 不做跨域大 Join |

物化白名单：`view` / `table` / `incremental` / `ephemeral`。
门禁实测：物化值不合法即 FAIL（`transform.materialization`）。

- **产出**：分层 + 物化方式
- **过关条件**：`harness.py model` 退出码 0

### Step 3 · 四类数据测试（至少覆盖前三类）
| 测试 | 作用 | 必须加在哪 |
|---|---|---|
| `unique` | 主键唯一 | 每张 mart 的主键 |
| `not_null` | 关键字段非空 | 主键 + 业务必需字段 |
| `accepted_values` | 枚举受控 | 状态/渠道/类型字段 |
| `relationships` | 外键存在 | 有外键的模型 |

```bash
python harness.py test --input <数据测试.json>
```
门禁实测：枚举未声明或不在白名单即 FAIL（`test.accepted_values`）。

> **为什么 `accepted_values` 最重要**：上游悄悄新增一个状态值，
> 所有按状态分组的报表会多出一行"未知"，而没人会收到报错。

- **产出**：测试清单
- **过关条件**：`harness.py test` 退出码 0

### Step 4 · DAG 依赖与无环校验
```bash
python harness.py dag --input <DAG.json>
```
检查：依赖显式声明、**无环**、无跨层反向依赖（mart 不该被 staging 依赖）。
门禁实测：出现环即 FAIL（`dag.acyclic`）。

- **产出**：DAG 定义 + 无环结论
- **过关条件**：`harness.py dag` 退出码 0

### Step 5 · 增量与回填前置（增量模型必做）
| 检查 | 要求 |
|---|---|
| 增量策略 | 明确 `append` / `merge` / `delete+insert`，并写去重键 |
| 幂等性 | 同一批数据重跑结果一致 |
| 回填方案 | 历史数据怎么补、补多少、影响谁 |

**没有回填方案的增量模型不许上生产**——出错时无法修复。

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | 模型定义（粒度/分层/物化/主键） | `.json` | `examples/model.json` |
| 2 | 数据测试清单（四类） | `.json` | `examples/test.json` |
| 3 | DAG 依赖与无环结论 | `.json` | `examples/dag.json` |
| 4 | 增量策略与回填方案 | `.md` | `references/pipeline-modeling.md` §五 |
| 5 | 三份门禁结论 | 终端 JSON | `harness.py model/test/dag` |

- 命名：`pipeline_<域>_<模型名>_<YYYYMMDD>.json`

---

## §5 质量门（一票否决，不过不给交付）

1. **粒度一句话说清**，且与主键一致；
2. **物化方式在白名单内**（`transform.materialization`）；
3. **分层正确**（staging 不做聚合、mart 不跨域大 Join）；
4. **主键有 `unique` + `not_null` 测试**；
5. **枚举字段有 `accepted_values`**（`test.accepted_values`）；
6. **DAG 无环、依赖显式、无跨层反向依赖**（`dag.acyclic`）；
7. **增量模型必须有去重键与回填方案**。

> 验收命令：`python harness.py model|test|dag --input <json>`
> 命中任一项不过 → 回 §3 对应 Step，**不允许删掉测试让门禁变绿**。

---

## §6 交付前自检清单

- [ ] 我能一句话说清"一行代表什么"
- [ ] 主键就是这个粒度的唯一标识，不是"差不多"
- [ ] 物化方式与分层匹配（staging 用 view，mart 用 table）
- [ ] 主键有 unique + not_null 两个测试，不是只加一个
- [ ] 所有枚举字段都有 accepted_values，且列全了合法值
- [ ] 有外键的地方加了 relationships 测试
- [ ] DAG 没有环，也没有 mart 被 staging 依赖这类反向依赖
- [ ] 增量模型写了去重键，重跑结果一致
- [ ] 增量模型有回填方案（怎么补、补多少、影响谁）
- [ ] 没有把业务逻辑写在 staging 层
- [ ] 三道门禁均退出码 0

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 粒度写"大概是一行一个订单" | 必须精确："一行 = 一个 order_id" |
| EX-02 | 主键加 `unique` 不加 `not_null` | 两者都要；`unique` 允许一个 NULL 通过 |
| EX-03 | 枚举字段不加 `accepted_values` | 上游加新值时会静默污染所有分组报表 |
| EX-04 | staging 层写聚合与业务逻辑 | staging 只做对齐与重命名，聚合放 intermediate |
| EX-05 | mart 层跨域大 Join | mart 面向消费，跨域 Join 放 intermediate |
| EX-06 | 物化全用 `table` | staging 用 `view`；全 table 会让构建时间指数增长 |
| EX-07 | 增量模型不写去重键 | 必须写 merge 键，否则重跑会产生重复行 |
| EX-08 | 增量模型没有回填方案 | 出错无法修复；回填方案必须与模型一起交付 |
| EX-09 | DAG 依赖靠"代码里恰好先跑" | 依赖必须显式声明，隐式依赖迟早出环 |
| EX-10 | mart 被 staging 依赖 | 跨层反向依赖，会导致循环 |
| EX-11 | 测试只写"数据应该没问题" | 测试必须是可执行断言（unique/not_null/…） |
| EX-12 | 模型改动不通知下游 | 主键或粒度变更必须通知 `r06`/`r19`，否则下游静默出错 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `harness.py` 跑不了 | 按 §6 人工逐项核对，标注「未跑门禁」；**不得标记"可上生产"** |
| 粒度不明 | 停下问，不许先建表后补粒度 |
| 只有一个来源表 | 仍要建 staging，不要直接从源表出 mart |
| 增量策略不明 | 先用全量 `table` 跑通，再优化为增量；不要一开始就上增量 |
| 上游不可控（第三方 API） | 增加 schema 快照测试，上游字段变更时提前失败 |
| 主键有重复（历史脏数据） | 先去重并记录剔除条数，再上 unique 测试 |
| 用户要求"先别加测试，后面补" | 拒绝；先加测试再上线，`r06` 的教训是补测试永远排在后面 |

**明确不做**
- 不出分析结论（归 `r06`）；
- 不定义业务指标口径（归语义层）；
- 不做调度与告警配置（归 `r20`）；
- 不保证上游数据质量（只能加校验，不能替上游修）。

---

## §9 资源地图（按需读取，禁止全量加载）

| 什么时候需要 | 读哪个文件 |
|---|---|
| 分层规范、物化选择、四类测试写法、增量与回填 | `references/pipeline-modeling.md` |
| 门禁是否还有效（正/反例 fixture） | `scripts/gate_selftest.py --self-test` |
| 负向用例（哪些错法必须被拦） | `tests/misuse.md` |
| 模型骨架 | `../../../examples/model.json` |
| 测试清单骨架 | `../../../examples/test.json` |
| DAG 骨架 | `../../../examples/dag.json` |
| 增量策略骨架 | `../../../examples/incremental_strategy.json` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言三道门禁对正/反例的退出码 | `--self-test` / `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 新增技能包（此前 r18 无任何能力卡）。
  含 §1–§10 十节骨架、`references/pipeline-modeling.md`、`scripts/gate_selftest.py`、`tests/misuse.md`。
  门禁复用 `harness.py` 三道（model / test / dag）。
- 参考对标：`dbt-labs/dbt-agent-skills`（技能目录本身即 dbt 项目、双宿主清单）。
  本包采纳其"分层 + 测试"结构，并补上"粒度必须先定""增量必须有回填方案"两条。
