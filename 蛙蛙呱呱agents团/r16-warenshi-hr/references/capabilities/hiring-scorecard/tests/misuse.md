# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/hiring-scorecard/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 6/6`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 必选项超 5 条 / 招聘人数非法 / 缺必填 | `opening.required` / `opening.vacancies` | ✅ exit=1（`examples/opening_dirty.json`） |
| MU-02 | 候选人 email 格式非法 | `applicant.email` | ✅ exit=1（`examples/applicant_dirty.json`） |
| MU-03 | status 不在白名单 | `applicant.status` | ✅ exit=1（同上） |
| MU-04 | 评估未推进就发 Offer | `offer.prior`（前置状态链不合法） | ✅ exit=1（`examples/offer_dirty.json`） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-05 | 必选项写"沟通能力强" | 不可验证，无法打分 | §6 可验证性检查 |
| MU-06 | 见完人再调权重 | 给印象配分 | §6 权重留痕 |
| MU-07 | 未验证维度打 3 分 | 和稀泥分 | §6 |
| MU-08 | 打分不带证据 | 不可复核 | §6 证据要求 |
| MU-09 | 结论写"综合感觉不合适" | 不是三选一 | §6 |
| MU-10 | 给候选人排名 | 评分卡禁止排名 | §7 EX-07 + 治理 |
| MU-11 | 评估含年龄/婚育/籍贯 | 违法 | §8 明确拒绝 |
| MU-12 | 用"文化匹配"当否决项 | 偏见外衣 | §6 行为证据 |
| MU-13 | 面试题与维度不对应 | 题白问了 | §6 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 每次改 `harness.py opening/applicant/offer` 后重跑 `--self-test`
- [ ] 权重改动有留痕（谁改、为什么、什么时候）
- [ ] 交付物里没有任何排名或综合印象分
- [ ] 全部评估维度均无歧视性字段

> **纪律**：门禁保证"流程不跳步"，保证不了"判断没偏见"。
> 评分卡的价值在于**把判断摊开成可复核的条目**，而不是把它包装得更精致。
