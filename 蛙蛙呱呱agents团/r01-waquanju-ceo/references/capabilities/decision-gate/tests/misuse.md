# 负向测试集（misuse cases）

> **用途**：把"什么算错"变成可断言的事实。每条给一份**故意做错**的决策卡片段，
> 以及**应当拦住它的门禁**。
> 运行方式：`python references/capabilities/decision-gate/scripts/gate_selftest.py` → 必须 `PASS 4/4`。
> 版本：v2.0.0

---

## 一、已被门禁拦住（机器可验，见 `tests/*.json`）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 不可逆决策，无 `rollback_plan` | `card.rollback` CRITICAL | ✅ exit=1（`tests/fail-missing-rollback.json`） |
| MU-02 | `options` 只有 1 项，且没有"什么都不做" | `card.options` BLOCKER | ✅ exit=1（同上） |
| MU-03 | `success_criteria.threshold` 写「更快」 | 阈值不可判定 | ✅ exit=1（`tests/fail-vague-thresholds.json`） |
| MU-04 | `kill_criteria` 为空数组 | 缺杀死标准 | ✅ exit=1（同上） |
| MU-05 | `owner` 写「团队」 | 一 owner 一责任，共同负责=没人负责 | ✅ exit=1（同上） |
| MU-06 | `deadline` 写「尽快」 | 无到期日 | ✅ exit=1（同上） |
| MU-07 | 缺 `announcement_draft` | 预公告测试未通过 | ✅ exit=1（由 `card.preannouncement` BLOCKER 覆盖） |
| MU-08 | `reversibility` 填非法值（如「看情况」） | 可逆性分级不合规 | ⚠ 门禁判 `card.reversibility` 失败 |

## 二、门禁抓不到，必须靠 §6 自检与评审官（R04）

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-09 | 五问写成「已考虑风险」一句概括 | 未逐条作答 | `harness.py reversibility` 会拦 → 归入可机验 |
| MU-10 | `rationale` 只夸推荐项，不说"相对其它选项为什么是它" | 无法比较，等于没论证 | §6 自检 + R04 |
| MU-11 | `rollback_plan` 写「如有问题及时回滚」 | 无阈值无时限，等于没有回滚 | §6 自检 + R04 |
| MU-12 | 先拍板，事后补 success/kill 标准（聊天记录可证） | 标准必须决策前写死 | R04 查时序 |
| MU-13 | 不可逆决策 `human_signoff_required=false` | 越权执行 | `harness.py escalate` 会判违规 → 可机验 |
| MU-14 | 把可逆决策当不可逆反复上会 | 第 5 问的"逃避"情形 | §6 自检 |
| MU-15 | 结论被推翻就删掉旧决策日志条目 | 决策日志不可覆盖 | R01 `decisionlog conflict` |
| MU-16 | 用户说「听着不错」即视为批准并执行不可逆动作 | 沉默/评价 ≠ 批准 | `references/hard-gate.md` §二 + R04 |

---

## 三、自检

- [ ] 第一条"已被门禁拦住"的每一条，都能在 `gate_selftest.py` 里找到对应 fixture 或明确标 ⚠
- [ ] 新增错误类型时，先加进本表，再决定加 fixture 还是加自检项
- [ ] 每次改 `harness.py` 的 `card/escalate/reversibility` 检查项后，重跑 `gate_selftest.py`
- [ ] 本表里"门禁抓不到"的条目都有明确的人类负责人（R04 或 §6），不存在无人负责的条目

> **纪律**：一条错误若既抓不到也无人负责，就不该写进本表——它会产生虚假的安全感。
