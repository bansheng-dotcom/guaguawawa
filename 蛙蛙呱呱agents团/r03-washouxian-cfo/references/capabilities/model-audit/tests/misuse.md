# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/model-audit/scripts/audit_gate.py --self-test` → 必须 `PASS 6/6`（含 3 个反例）。
> 版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 期末现金申报 60000，推算 59500 | `cash_flow` 现金勾稽不等 | ✅ exit=1（`examples/cfo_healthcheck.json`） |
| MU-02 | 资产 ≠ 负债 + 权益 | `balance_sheet` 勾稽断 | ✅ 由 `cfo healthcheck` 覆盖 |
| MU-03 | 毛利直接填 ≠ 收入 − 成本 | `income_statement` 勾稽断 | ✅ 同上 |
| MU-04 | 总账与子账匹配率 50%（6 笔里 3 条破差） | `matched_pct ≥ 95%` | ✅ exit=1（`examples/financial_recon.json`） |
| MU-05 | 破差 3 条（子账 only 1 / 金额 1 / 时点 1） | `breaks = 0` | ✅ exit=1（同上） |
| MU-06 | 审计证据缺 `collector`（CM-02） | `evidence_field` + `evidence` 完整率 | ✅ exit=1（`examples/audit_evidence.json`） |
| MU-07 | 超阈差异无 driver 或只复述数字 | `variance_note` | ✅ 由 `financial variance` 覆盖（未入 selftest，见下） |

> **MU-07 的诚实说明**：`financial variance` 门禁可用，但本包 selftest 未纳入，
> 因为需要额外构造 driver 缺失的对照 fixture。**代码有、测试无**，已在此标注。

## 二、最高危的一条：直接调 harness 会假绿（本项目实测）

| # | 错误做法 | 后果 | 正确做法 |
|---|---|---|---|
| MU-08 | 直接跑 `python harness.py financial recon --input x.json`，看它 exit 0 就当通过 | **该文件在 `ok=false` 时仍 exit 0**，即使 `matched_pct:50%`。CI 完全拦不住 | 走 `python scripts/audit_gate.py financial recon --input x.json`，它把 `ok` 映射成退出码 |
| MU-09 | 只看 harness 打印的 `ok:false`，人工判断 | 人能看，CI 不能；批量后必然漏 | 同上 |

> 实测证据：`audit_gate.py --self-test` 的输出里，反例行会同时打印
> 「包装后 exit=1」与「原生 harness exit=0」——**这个对比就是缺陷的证明**。
>
> **补充事实**（避免误伤）：`python agent.py cfo healthcheck --input <坏输入>` → exit 1，
> 即 `agent.py` 路径是正常的，**只有直接调 `harness.py` 时丢失退出码**。
> 20 个角色里仅 r02 / r03 的 `harness.py` 有此问题。

## 三、门禁抓不到，必须靠 §6 自检与人工

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-10 | 差额 500 判"差异很小可接受" | 勾稽必须为 0 | §6 自检 + R04 |
| MU-11 | 期末现金手填凑平 | 破坏了勾稽的意义 | §6 + 原始凭证核验 |
| MU-12 | 审计者顺手把模型改对 | 只读红线，原始证据消失 | §6 + 治理（不可复核即无效） |
| MU-13 | 问题日志只写"数据有问题" | 不可定位、不可整改 | §6 六列检查 |
| MU-14 | 含税对不含税，差异当问题报 | 口径噪声 | §3 Step 1 范围卡 |
| MU-15 | 把内部核验说成"审计意见已出" | 越界（持牌） | §1 转交表 + R04 |
| MU-16 | 上期未闭环项不再列出 | "提过了"≠修好了 | §6 + `model-audit-checklist.md` §四 |

---

## 四、自检

- [ ] 第一节每条"✅"都能在 `audit_gate.py --self-test` 找到 fixture
- [ ] 标"代码有、测试无"的条目（MU-07）已明确记录，没有假装覆盖
- [ ] 每次改 `harness.py` 的相关检查项后，重跑 `--self-test`
- [ ] 若将来修好 r03 的 harness 退出码，本包可改为直接调 harness（届时删掉 MU-08/09）
- [ ] 交付结论统一表述为「内部核验结果」，从不称"审计意见"

> **纪律**：门禁打印 `ok:false` 却 exit 0，是比没有门禁更危险的状态——
> 因为它会让人以为"已经检查过了"。
