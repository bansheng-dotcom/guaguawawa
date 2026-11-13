# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/campaign-plan/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 7/7`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 计划缺 `experiments` | `plan:experiments` | ✅ exit=1（`examples/plan_bad.json`） |
| MU-02 | 计划缺 `stop_condition` | `plan:stop_condition` | ✅ exit=1（同上） |
| MU-03 | 计划缺 `growth_stage` | `plan:growth_stage` | ✅ exit=1（同上） |
| MU-04 | 计划缺 `metrics` | `plan:metrics` | ✅ exit=1（同上） |
| MU-05 | 投放缺四要素（audience/creative/budget） | `paid.media_fields` | ✅ exit=1（`examples/media_dirty.json`） |
| MU-06 | 渠道不在白名单 | `paid.channel` | ✅ exit=1（同上） |
| MU-07 | 实验缺显著性门槛 | `paid.significance` | ✅ exit=1（`examples/cro_dirty.json`） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-08 | 预算 100% 投一个渠道 | 单渠道依赖 | §6 自检（`plan` 不含比例校验） |
| MU-09 | 停止条件写"效果不好就停" | 无阈值无时间窗 | §6 三件套检查 |
| MU-10 | 一次实验挂三个主指标 | 事后总能挑出一个好看 | §6 主指标唯一 |
| MU-11 | 开跑后补实验设计 | 不是预注册 | §6 + 治理 |
| MU-12 | 样本量空着或差一个数量级 | 实验做不出来 | §6 + 交 `r06` 功效分析 |
| MU-13 | 承诺"投了就有 ROI 3.0" | 越界承诺 | §1 转交表 |
| MU-14 | 护栏指标缺合规红线 | 灰产风险 | §6 |
| MU-15 | 成长期全开新渠道 | 阶段与打法不符 | §6 阶段判据 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 注意：`plan` 门禁**不校验预算比例**，"无单渠道 100%"必须人工核
- [ ] 每次改 `harness.py plan/media/cro` 后重跑 `--self-test`
- [ ] 预注册表与计划同时交付，不是事后补
- [ ] 样本量要么有数，要么明确"待 r06 估算"

> **纪律**：门禁能保证"方案写全了"，保证不了"方案会成功"。
> 停止条件是唯一能在失败时救你的东西，必须写死。
