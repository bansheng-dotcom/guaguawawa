# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/dbt-unit-test/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 6/6`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 物化值不在白名单（如 `materialized_view`） | `transform.materialization` | ✅ exit=1（`examples/model_dirty.json`） |
| MU-02 | 枚举测试未声明 values | `test.accepted_values` | ✅ exit=1（`examples/test_dirty.json`） |
| MU-03 | 枚举值不在白名单 | `test.accepted_values` | ✅ exit=1（同上） |
| MU-04 | DAG 出现环 | `dag.acyclic` | ✅ exit=1（`examples/dag_dirty.json`） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-05 | 粒度写"大概一行一个订单" | 主键必然错 | §6 粒度检查 |
| MU-06 | 主键只加 unique 不加 not_null | unique 允许多个 NULL | §6 双测试检查 |
| MU-07 | staging 层写聚合与业务逻辑 | 分层越界 | §6 分层检查 |
| MU-08 | 全量用 table 物化 | 构建时间爆炸 | §6 物化选择 |
| MU-09 | 增量模型不写去重键 | 重跑产生重复行 | §6 + `incremental_strategy` 部分覆盖 |
| MU-10 | 增量模型无回填方案 | 出错无法修复 | §6 |
| MU-11 | 依赖靠"恰好先跑" | 隐式依赖迟早出环 | §6 + `dag` 部分覆盖 |
| MU-12 | mart 被 staging 依赖 | 跨层反向依赖 | §6 |
| MU-13 | 模型改动不通知下游 | 下游静默出错 | §7 EX-12 + 治理 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 每次改 `harness.py model/test/dag` 或 `skills/` 后重跑 `--self-test`
- [ ] 人工项（粒度/分层/回填/通知）都有显式记录
- [ ] 每张 mart 主键都有 unique + not_null 双测试
- [ ] 所有枚举字段都有 accepted_values 且值列全

> **纪律**：管道"跑通了"和"数据可信"是两件事。
> 门禁只管后者的一部分，剩下的靠建模纪律。
