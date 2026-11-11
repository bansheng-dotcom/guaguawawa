# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/industry-panorama-research/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 8/8`（含 4 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 格局图没有分层，只列公司名 | `industry.landscape` 结构 | ✅ exit=1（`industry_landscape_dirty.json`） |
| MU-02 | 集中度只写"很集中"，无 CR 数值 | `industry.concentration` | ✅ exit=1（`industry_concentration_dirty.json`） |
| MU-03 | 集中度没有口径（营收/用户/出货量） | `industry.concentration` | ✅ exit=1（同上） |
| MU-04 | 规模测算缺计算路径或假设 | `sizing.size` | ✅ exit=1（`sizing_size_dirty.json`） |
| MU-05 | 敏感性分析结构缺失 | `sizing.sensitivity` | ✅ exit=1（`sizing_sensitivity_dirty.json`） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-06 | 行业边界不定义就开始数 | 数字不可比 | §6 边界三问 |
| MU-07 | 规模给单点"约 97.3 亿" | 伪精确，精度超过输入 | §6 区间检查 |
| MU-08 | 用一份来源就下结论 | 未交叉验证 | §6 + `evidence-ledger` |
| MU-09 | 不做敏感性分析 | 不知道哪个假设最要命 | `sizing.sensitivity` 覆盖结构 + §6 |
| MU-10 | 数据缺口藏起来 | 读者无法判断可信边界 | §6 缺口检查 |
| MU-11 | 把"大盘增长"当"我们能增长" | 忽略份额变化 | §7 EX-11 |
| MU-12 | 结论写"行业肯定…" | 越界当决策者 | §7 EX-12 |
| MU-13 | 海外数据直接外推中国大陆 | 口径不可比 | §8 降级规则 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 行业边界能列出 3 家在、2 家不在
- [ ] 集中度有数、有口径、有年份、有来源
- [ ] 规模是区间，精度不超过输入精度
- [ ] 敏感性标出了"最敏感假设"
- [ ] 数据缺口与影响面都写了

> **纪律**：行业研究最容易"看起来很有说服力"——因为全是宏观数字。
> 真正决定可信度的是**边界、口径、缺口**这三件最不性感的事。
