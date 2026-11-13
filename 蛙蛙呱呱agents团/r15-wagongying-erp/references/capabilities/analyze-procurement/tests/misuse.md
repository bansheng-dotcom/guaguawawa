# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/analyze-procurement/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 2/2`（含 1 个反例）。版本：v2.0.0

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 报价同时含 CNY 与 USD | `tco.currency`（混币种 BLOCKER） | ✅ exit=1（`tests/tco-fail.json`） |
| MU-02 | `unit_price` 为 0 | `tco.unit_price` | ✅ exit=1（同上） |
| MU-03 | 资金年化 45%（上限 30%） | `tco.rate` | ✅ exit=1（同上） |
| MU-04 | 没有任何 quotes | `tco.quotes` | ✅ exit=1（实测空输入） |

## 二、门禁抓不到，靠 §6 自检

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-05 | 只比单价 | 漏物流/关税/资金/质量 | §6 五项折算 |
| MU-06 | 账期当免费 | 90 天账期有真实资金成本 | §6 资金占用 |
| MU-07 | 只算头程运费 | 漏尾程与仓储 | §6 |
| MU-08 | 关税按 0 算 | 低估到岸成本 | §6 |
| MU-09 | 忽略 MOQ | 下单量不足起订量 | §6 |
| MU-10 | 比首单不比全周期 | 漏维护/备件/处置 | §6 三年总成本 |
| MU-11 | 结论只说"B 便宜" | 汇率一变就反 | §6 前提检查 |
| MU-12 | 便宜货不留质量成本 | 隐性返工 | §7 EX-10 |

> **纪律**：单项最便宜的报价，常常是总成本最贵的那个。
