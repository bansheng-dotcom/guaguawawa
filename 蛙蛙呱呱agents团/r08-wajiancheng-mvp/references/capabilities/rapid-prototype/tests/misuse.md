# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/rapid-prototype/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 6/6`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | MVP 缺成功标准或杀死标准 | `mvp.criteria` | ✅ exit=1（`examples/mvp_dirty.json`） |
| MU-02 | 落地页无可核验的社会证明 | `landing.proof` | ✅ exit=1（`examples/landing_dirty.json`） |
| MU-03 | 缺类型检查 | `qa.typecheck` | ✅ exit=1（`examples/qa_dirty.json`） |
| MU-04 | 缺截图证据 | `qa.screenshot` | ✅ exit=1（同上） |
| MU-05 | 缺设计自检 | `qa.design_qa` | ✅ exit=1（同上） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-06 | 不写"要验证什么假设" | 原型变玩具 | §6 假设检查 |
| MU-07 | mock 数据不标注 | 被当成真实现 | §6 + 治理 |
| MU-08 | 无鉴权还配公网地址 | 安全事故 | §7 EX-04 |
| MU-09 | 超时间盒继续加功能 | 范围失控 | §6 时间盒 |
| MU-10 | 编造用户数/评价 | 虚假宣传 | §6 + `landing.proof` 部分覆盖 |
| MU-11 | 没截图就报完成 | 没真跑过 | `qa.screenshot` 覆盖 |
| MU-12 | 把原型当成品交出去 | 责任错位 | §6 README 检查 |
| MU-13 | 捷径不登记 | 接手者把 mock 当实现 | §6 捷径账本 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 每次改 `harness.py mvp/landing/qa` 后重跑 `--self-test`
- [ ] 捷径账本已交付，每条含"上线前必须补什么"
- [ ] 产物 README 首行写了"这是原型，不是成品"

> **纪律**：原型最大的风险不是粗糙，是**被当成成品**。
> 捷径账本就是那道防线。
