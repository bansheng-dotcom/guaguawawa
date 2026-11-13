# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/qbr-health/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 7/7`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 客户 `name` 为空 | `health.name` BLOCKER | ✅ exit=1（`examples/health_dirty.json`） |
| MU-02 | `at_risk` 客户无 `risk_reason` | `health.risk_reason` BLOCKER | ✅ exit=1（同上） |
| MU-03 | 区间与分数矛盾（80 分标成 at_risk） | `risk.band_consistency` | ✅ exit=1（`examples/risk_dirty.json`） |
| MU-04 | 升级缺路由 | `knowledge.route` | ✅ exit=1（`examples/escalation_dirty.json`） |
| MU-05 | 升级缺证据 | `knowledge.evidence` | ✅ exit=1（同上） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-06 | 四维简单平均当健康分 | 权重被抹平（30/25/25/20 才对） | §6 自检（`health` 只校验字段与区间） |
| MU-07 | 用登录次数当 `usage` | 刷出来的活跃不算 | §6 依据检查 |
| MU-08 | 没依据打个 60 分 | 分数凭空来 | §6 依据检查 |
| MU-09 | 只看绝对分不看 delta | 掉 15 分的高分客户更危险 | §6 delta 检查 |
| MU-10 | 只看分数不看续约日期 | 90 天内到期是独立信号 | §6 临期检查 |
| MU-11 | 为让老板放心把红调黄 | 分数只降不升 | §6 + 治理 |
| MU-12 | 所有客户一起升级 | 钝化紧急通道 | §6 升级分级 |
| MU-13 | 升级只写"需要支持" | 没说要什么（investigate/fix/decide/approve） | §6 + `escalation` 部分覆盖 |
| MU-14 | QBR 只讲成绩不提风险 | 汇报而非经营 | §6 QBR 结构 |
| MU-15 | 承诺"照这个做就能续约" | 越界承诺 | §1 转交表 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 注意：`health` 门禁**不校验加权算法**，"30/25/25/20"必须人工核
- [ ] 每次改 `harness.py health/risk/escalation` 后重跑 `--self-test`
- [ ] 每个维度分都能指到依据（截图/工单号/访谈记录）
- [ ] 临期客户全部单独列出，不只看分数

> **纪律**：健康分最大的价值不是打分，而是**把"感觉有点冷"变成可复核的数字与行动**。
> 分数往上调一格，团队就少一次预警。
