# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/incident-response/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 8/8`（含 4 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 时间线时间倒序（事后美化） | `incident.monotonic` | ✅ exit=1（`examples/incident_dirty.json`） |
| MU-02 | 升级记录时间倒序 | `escalation.monotonic` | ✅ exit=1（`examples/escalation_dirty.json`） |
| MU-03 | 复盘缺严重度 | `postmortem.severity` | ✅ exit=1（`examples/postmortem_dirty.json`） |
| MU-04 | 复盘缺必备章节 | `postmortem.sections` | ✅ exit=1（同上） |
| MU-05 | 复盘缺根因 | `postmortem.root_cause` | ✅ exit=1（同上） |
| MU-06 | 未验证恢复（只重启） | `drill.restored` | ✅ exit=1（`examples/drill_dirty.json`） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-07 | 根因写"人为失误" | 等于没找到根因 | §6 三层根因法 |
| MU-08 | 只记开始时间不记发现时间 | 发现延迟不可度量 | §6 |
| MU-09 | 升级靠感觉叫人 | 要么太早要么太晚 | §6 + `escalation` 部分覆盖 |
| MU-10 | RPO/RTO 写估算值 | 自欺 | §6 实测要求 |
| MU-11 | 复盘没有"未解决项" | 假装已解决 | §6 六章检查 |
| MU-12 | 改进项无 owner 与到期 | 等于没提 | §6 |
| MU-13 | 安全事件按 P1 处理 | 延误处置 | §6 分级 + §8 |
| MU-14 | 一份复盘覆盖多次事故 | 无法归因 | §7 EX-12 |
| MU-15 | 时间线写"手忙脚乱" | 评价而非事实 | §6 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 每次改 `harness.py incident/escalation/postmortem/drill` 后重跑 `--self-test`
- [ ] 根因至少追到"中层"（流程/工具），不是止步于"人"
- [ ] 恢复演练验证了数据行数与校验和，不只是服务起来了
- [ ] RPO/RTO 标了测量方式与测量时间

> **纪律**：事故复盘的价值在于**让下一次不再以同样方式发生**。
> 而"人为失误"这四个字，从来没有阻止过任何一次复发。
