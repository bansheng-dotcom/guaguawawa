# 负向测试集（misuse cases）

> **用途**：把"什么算假评审"变成可断言的事实。
> 运行方式：`python references/capabilities/review-anti-collusion/scripts/gate_selftest.py`
> → 必须 `PASS 6/6`（含 4 个反例被正确拦下）。
> 版本：v2.0.0

---

## 一、已被门禁拦住（机器可验，见 `tests/packet-*.json`）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | `reviewer == producer`（自己评自己） | `review:self_review_gate` CRITICAL | ✅ exit=1（`packet-self-review.json`） |
| MU-02 | 评审结果含 `applied_fixes`（"我已改好"） | `review:never_fixes` CRITICAL | ✅ exit=1（`packet-applied-fixes.json`） |
| MU-03 | `verdict=PASS` 且 `criteria_results` 为空 | `review:evidence_gate` CRITICAL | ✅ exit=1（`packet-no-evidence.json`） |
| MU-04 | flat 结果 `PASS` 无任何证据链 | `harness:evidence_chain` CRITICAL | ✅ exit=1（`review_result_dirty.json`） |
| MU-05 | `keep_list` 项被降级为 FAIL 且无 `resolution_reason` | `review:keep_list_integrity` | ⬜ 未入 fixture（见下方说明） |
| MU-06 | 结论文本含 `should` / `应该` / `我认为` | `review:hedge_words` → 路由 `writer` | ⬜ 未入 fixture（见下方说明） |

> MU-05 / MU-06 暂未入 fixture 的原因：两项需要构造 `keep_list` / `conclusion_keys` 的嵌套结构，
> 而当前 `packet-no-evidence.json` 已同时触发 `hedge_words`（summary 含"应该"），
> 会在同一次运行里被覆盖，无法单独断言。**补 fixture 是下一步**，在此之前这两项属"代码有、测试无"。

## 二、schema 假绿（本项目实测到的真实缺陷）

| # | 错误做法 | 后果 | 正确做法 |
|---|---|---|---|
| MU-07 | 把 flat `review_result_*.json` 直接传给 `review.py --packet` | `result` 为空 → **0 条检查** → `ok:true` 假绿 | 传 `{skill, action, result}` 包装形状 |
| MU-08 | 只看 `review.py` 的 `ok` 字段 | 同上，0 条检查也返回 true | 同时断言 `checks` 条数 > 0 |

> 这两条不是理论风险——本包开发时**真踩到了**：
> 第一版 selftest 用 flat 结果喂 `review.py`，四个反例全部 exit 0，看起来"门禁坏了"。
> 实际是喂错了形状。反过来也说明：**门禁不校验输入形状**，这是它自身的弱点。

## 三、门禁抓不到，必须靠 §6 自检与第二评审

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-09 | 判据是评审者自己拟的 | 判据被有意放松 | §6 自检 + 要求对方给判据 |
| MU-10 | 严重度全是 MINOR，没有可落地整改项 | 分级失真 | §6 自检 + 严重度校准表 |
| MU-11 | 有 BLOCKER 却判 PASS | 结论自相矛盾 | §6 自检 + `harness` 的 verdict/findings 一致性 |
| MU-12 | 证据写"见附件" | 不可定位 | §6 自检 + 抽检 |
| MU-13 | 与生产者协商"能不能算过" | 合谋 | R01 治理介入 |
| MU-14 | 顺手改掉问题后写"已修复" | 职责坍塌 | MU-02 已可机验（同一条红线） |

---

## 四、自检

- [ ] 第一节每一条"实测 ✅"都能在 `gate_selftest.py` 里找到对应 fixture
- [ ] 标 ⬜ 的条目已明确记录"代码有、测试无"，没有假装已覆盖
- [ ] 新增红线时，先加 fixture 再改 `review.py`
- [ ] 每次改 `review.py` 或 `thresholds.json` 的 `review.*` 后重跑 `gate_selftest.py`
- [ ] 每份评审只允许差一级严重度（双人交叉校验），差两级先修判据

> **纪律**：`ok:true` 不等于通过。**0 条检查的 `ok:true` 是最危险的假绿。**
