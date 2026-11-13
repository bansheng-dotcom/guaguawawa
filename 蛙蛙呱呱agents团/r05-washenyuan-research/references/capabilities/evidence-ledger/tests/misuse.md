# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/evidence-ledger/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 6/6`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 结论缺 `findings` 结构 | `harness:findings` | ✅ exit=1（`examples/verdict_bad.json`） |
| MU-02 | 结论无任何证据链 | `harness:evidence_chain` | ✅ exit=1（同上） |
| MU-03 | 材料缺失但未在清单中声明 | `materials:missing` | ✅ exit=1（`examples/materials_bad.json`） |
| MU-04 | 计划缺 `question` | `plan:question` | ✅ exit=1（`examples/plan_bad.json`） |
| MU-05 | 计划缺 `analytical_step` | `plan:analytical_step` | ✅ exit=1（同上） |
| MU-06 | 计划缺 `query_spec` | `plan:query_spec` | ✅ exit=1（同上） |

> 另外 `examples/review_no_evidence.json` / `review_unsourced.json` / `review_hedge.json`
> 三份夹具覆盖"无证据 / 无来源 / 猜测措辞"，可用于 `agent.py review` 的人工抽检。

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-07 | 研究问题太大（"研究下 AI 行业"） | 收窄不足 | §6 + 判定口径检查 |
| MU-08 | 把缺口藏起来让报告显得完整 | 不可复核 | §6 缺口检查 |
| MU-09 | 来源只写"网上查到" | 缺 level/source/date/locator | §6 四要素 |
| MU-10 | C 级来源支撑"可以确认" | 措辞越界 | §6 强度对照 |
| MU-11 | 写"业内普遍认为" | 无来源句式 | §6 |
| MU-12 | B 级报道不追原始出处 | 未降级为 C | §6 降级规则 |
| MU-13 | 数据不写采集日期 | 无法判时效 | §6 |
| MU-14 | 把 AI 生成结果当来源 | 来源不成立 | §6 + 治理 |
| MU-15 | 只列支持证据，不列反证 | 是论证不是研究 | §6 反证要求 |
| MU-16 | 用户要求删不利证据就删 | 失信 | §8 拒绝 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 每次改 `harness.py verdict/materials/plan` 后重跑 `--self-test`
- [ ] 人工项（问题收窄/缺口诚实/来源分级正确/反证）都有显式记录
- [ ] 报告里至少有 1 个"不利证据"段落
- [ ] 全篇搜索过"普遍认为/大家都知道/显而易见"，已全部改写

> **纪律**：门禁能保证"没瞎说"，保证不了"研究得对"。
> 一份没有缺口的报告，通常不是研究做全了，而是缺口被藏了。
