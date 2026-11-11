# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/eval-report/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 6/6`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 评测用例缺 `inputs` | `dataset.inputs` | ✅ exit=1（`examples/evaluation_dataset_dirty.json`） |
| MU-02 | 评测用例缺 `expectations` | `dataset.expectations` | ✅ exit=1（同上） |
| MU-03 | 评分器缺 type/target/criteria | `scorer.type` / `scorer.target` / `scorer.criteria` | ✅ exit=1（`examples/evaluation_scorer_dirty.json`） |
| MU-04 | 回归缺旧绿集 | `regression.existing_green` | ✅ exit=1（`examples/release_regression_dirty.json`） |
| MU-05 | 回归缺归因层次 | `regression.diagnosis_layer` | ✅ exit=1（同上） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-06 | 用例全是自己编的"应该能过" | 评测分虚高 | §6 用例来源检查 |
| MU-07 | 没有难例与近邻负例 | 测不出进步也测不出过拟合 | §6 |
| MU-08 | LLM 判定不给 criteria | 等同拍脑袋 | §6 + `scorer.criteria` 部分覆盖 |
| MU-09 | 评分器对错误答案也通过 | **假绿灯**，最危险 | §6"用错误样本校准评分器" |
| MU-10 | 只报总体通过率 | 掩盖某类场景全挂 | §6 分布检查 |
| MU-11 | 报告不列失败样本 | 无法改进 | §6 |
| MU-12 | 改评测集后与旧基线对比 | 跨版本不可比 | §6 + §7 EX-08 |
| MU-13 | 用平均分提升掩盖单项暴跌 | 发布事故 | §7 EX-09 |
| MU-14 | 模型卡只写优点 | 误导使用者 | §6 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 每次改 `harness.py evaluation_*` / `release_regression` 后重跑 `--self-test`
- [ ] 评分器做过"错误样本校准"（喂 2 条明显错误答案，必须挂）
- [ ] 报告有分层分布 + ≥5 条失败样本 + 局限说明
- [ ] 回归跑了旧绿集并逐一交代变差项

> **纪律**：评测最大的风险不是模型差，是**评分器骗你**。
> 一个只会查格式的评分器会稳定给出 90%，直到用户投诉。
