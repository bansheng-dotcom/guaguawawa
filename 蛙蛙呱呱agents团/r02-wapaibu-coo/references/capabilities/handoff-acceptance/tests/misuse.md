# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/handoff-acceptance/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 7/7`（含 2 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 交接包 `repro_commands: []` | `repro: 复现命令 0 条（交接包必须可复现，≥1）` | ✅ exit=1（`tests/handoff-missing.json`） |
| MU-02 | 交接包 `downstream_fields: []` | `downstream: 下游字段 0 个` | ✅ exit=1（同上） |
| MU-03 | 交接包 `acceptance_criteria: []` | `acceptance: 验收标准 0 条` | ✅ exit=1（同上） |
| MU-04 | `passed: true` 但 `evidence: ""` | `evidence: 第 1 条「…」无证据（口头通过不算过）` | ✅ exit=1（`tests/accept-no-evidence.json`） |
| MU-05 | `passed: true` 且完全没有 `evidence` 字段 | 同上 | ✅ exit=1（同上） |
| MU-06 | 全部验收项都无证据 | `verdict: 验收 0/2 通过` | ✅ exit=1（同上） |

## 二、调用方式假绿（2026-11-11 已修复）

| # | 错误做法 | 后果 | 正确做法 |
|---|---|---|---|
| MU-07 | ~~`python harness.py package --input x.json` 假绿~~ **已修复** | `harness.py` 已补 `__main__` + CLI，直跑退出码 0/1/2 正确 | 两种调用均可，退出码一致 |
| MU-08 | 看见 exit 0 就签收 | 同上，0 不代表通过 | 同上；并核对输出的 `ok` 字段 |

> 实测证据（修复后）：`harness.py package --input tests/handoff-missing.json` → exit 1；此前同一命令无输出、exit 0。
> 而 `harness.py package --input tests/handoff-missing.json` → 无输出、exit 0。
> **同一个门禁，两种调用方式，两种结论。**

## 三、门禁抓不到，必须靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-09 | 复现命令写「按文档操作」 | 不可直接执行 | §6 自检（照着跑一遍） |
| MU-10 | 验证据写「我看了没问题」 | 不可定位 | §6 + R04 抽检 |
| MU-11 | 替上交方补缺失字段再验收 | 替人背书，丢失现场 | §7 EX-06 + 治理 |
| MU-12 | 结论写「基本可以，先上着」 | 不是三选一 | §6 结论检查 |
| MU-13 | 审计轨迹事后补写、`ts` 倒序 | 轨迹不可信 | `trace` 门禁抓时间单调 + §6 |
| MU-14 | 把验收当质量评审 | 越界（质量结论归 R04） | §1 转交表 |
| MU-15 | 签收后不记录签收人与时间 | 无法追溯 | §6 留痕检查 |
| MU-16 | 交接方与接收方同一人 | 自交接 | §8 降级（标注并建议换人） |

---

## 四、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 所有门禁命令都写成 `agent.py harness`，没有一处直调 `harness.py`
- [ ] 新增交接字段时，先加 fixture 再改 `skills/s03_handoff.py`
- [ ] 每次改 r02 `harness.py` 或 `s03_handoff.py` 后重跑 `--self-test`
- [ ] 结论永远是三选一，没有第四种表述

> **纪律**：`exit 0` 只有在**确认门禁真的执行了**之后才有意义。
> 一个不执行的脚本和一个通过的门禁，退出码是一样的——这是最危险的一类假绿。
