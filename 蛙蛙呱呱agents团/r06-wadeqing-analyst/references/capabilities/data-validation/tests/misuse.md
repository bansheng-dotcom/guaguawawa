# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/data-validation/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 5/5`（含 2 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 度量 `agg: "sum_of"`（自创） | `measure[total_amount] agg 非法` | ✅ exit=1（`tests/semantic-bad.json`） |
| MU-02 | 维度 `type: "timex"`（自创） | `dimension[created_date] type 非法` | ✅ exit=1（同上） |
| MU-03 | 指标 `type: "simplex"`（自创） | `metric[monthly_revenue] type 非法` | ✅ exit=1（同上） |
| MU-04 | 脏 CSV：id 缺失 25% + 整行重复 + 日期 `not-a-date` + 金额 `abc` | 4 条 HIGH finding | ✅ exit=1（`tests/dirty.csv` 经 `gate_wrap.py`） |

## 二、既有门禁的边界（2026-11-11 已修一条）

| # | 局限 | 实测证据 | 补偿手段 |
|---|---|---|---|
| MU-05 | ~~`harness semantic` 不校验非空~~ **已修复** | 现要求每个 model ≥1 entities 且 ≥1 measures；全空返回 FAIL | ✅ exit=1（见 `semantic-empty` 用例） |
| MU-06 | `agent.py quality audit` **原生恒 exit 0** | 4 条 HIGH 且 `overall_score` 8.2 → 原生 exit 0 | 必须经 `scripts/gate_wrap.py` 包装 |
| MU-07 | 总分可能"看起来还行" | `overall_score` 8.2 仍判"可用-仅小问题" | 判据看 findings 有没有 HIGH/CRITICAL，不看总分 |

> 这三条不是"以后再说"，是**当前的真实边界**。写进 misuse 是为了让下一个人知道：
> 门禁过了不代表数据干净。

## 三、纯人工项（无门禁，靠 §6 自检）

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-08 | 无差别 `dropna()` | 删行=隐藏信息 | §6 + R04 |
| MU-09 | 数字写"约 1200" | 伪精确 | §6 来源标注 |
| MU-10 | 分母剔除流失用户还算留存 | 幸存者偏差 | §6 三问 |
| MU-11 | 与后台差 14% 仍继续分析 | 口径未对 | §6 交叉核对 |
| MU-12 | 缺失 25% 仍算均值 | 非随机缺失时均值不可信 | §6 |
| MU-13 | 时区不统一直接算趋势 | 日界错位 | §6 |
| MU-14 | 重复行未去重就统计 | 计数类指标被放大 | §6 + quality audit 部分覆盖 |

---

## 四、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] MU-05/06/07 三条局限已写进 SKILL.md §9，没有假装覆盖
- [ ] 每次改 `harness.py semantic` 或 `quality audit` 后重跑 `--self-test`
- [ ] 交付前逐条看了 findings，不只看 `overall_score`
- [ ] 人工项（来源/偏差/核对）都有显式记录

> **纪律**：数据校验是唯一一个"门禁通过率很高但事故率也很高"的环节——
> 因为真正的错在口径和偏差里，不在字段格式里。
