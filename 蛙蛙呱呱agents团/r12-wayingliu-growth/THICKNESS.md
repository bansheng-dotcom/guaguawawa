# R12 蛙引流 · 厚度自述（增长链版）

> 按升级方案 §5 / §16 / §21 自述，只写能被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 15 篇 / 约 45.2KB；本轮新增 3 篇（10–12，约 10KB） |
| 新增来源 | AARRR（McClure 2007）、*Hacking Growth*（Ellis & Brown 2017）；多触归因（Shao & Li, KDD 2011）、地理实验（Vaver & Koehler 2011）、两比例样本量（Fleiss）；adstock（Broadbent）、贝叶斯 MMM（Jin et al. 2017）、Hill 饱和、ridge（Hoerl & Kennard 1970） |
| 适用边界 | 每篇单列「适用边界」 |
| 误用反例 | 每篇单列「误用反例」，并写明本仓哪个门禁拦截（缺数据不补零 / 禁止把相关当因果 / 样本量不足不得下结论 / 留出验证不过即失败） |

## 2. 生产层

`growth_chain run` 一条命令串起 7 段：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `growth_chain/diagnose.py` | 指标 CSV/JSON | `diagnose.json`（指标树 + 漏斗 + z/环比异常） |
| 2 | `growth_chain/experiment.py` | 预注册 spec | `experiment.json`（每臂样本量 + MDE + 停止条件 + 指纹） |
| 3 | `growth_chain/attribution.py` | 触点 CSV | `attribution.json`（首触/末触/线性/位置 + 增量） |
| 4 | `growth_chain/retention.py` | 队列 CSV | `retention.json`（队列矩阵 + 留存曲线 + 激活/推荐） |
| 5 | `growth_chain/paid.py` | 渠道花费 CSV | `paid.json`（CAC/LTV/回收月/贡献毛利） |
| 6 | `growth_chain/selfmedia.py` | 平台导出 CSV | `selfmedia.json`（规范化 + 静态看板 + 三态日报） |
| 7 | `growth_chain/mmm.py` | 周度媒体 CSV | `mmm.json`（adstock + 饱和 + ridge + 留出 + CI） |

技能入口：`skills/s12_growth_chain.py`（diagnose/experiment/attribution/retention/paid/selfmedia/mmm/run/audit），已注册进 `skills/__init__.py`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 指标数据 | `fixtures/metrics_daily.csv`（90 行） | 第 59 天预埋流量异常，可被 z/环比规则命中 |
| 归因旅程 | `fixtures/attribution_touches.csv` | 转化用户数 = 指标 `orders`（690） |
| 增量证据 | `fixtures/increment_evidence.json` | 14 天地理实验：lift 6.2%，CI [1.8%, 10.6%] |
| 队列留存 | `fixtures/retention_cohort.csv` | 6 个队列，规模合计 = 指标 `signups`（2432） |
| 付费渠道 | `fixtures/paid_channels.csv` | 新客数 = 归因末触转化（各 115） |
| 自媒体导出 | `fixtures/selfmedia_90d.csv` | 中文原始列，90 天抖音数据 |
| MMM | `fixtures/mmm_weekly.csv` | 104 周，4 渠道，留出 R²=0.983 |
| 生成器 | `fixtures/build_fixtures.py` | 固定公式、无随机、可复算 |
| 黄金 | `golden/*.html`（3 份） | 由 `golden/build_golden.py` 真跑链后保存 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 指标树可拆到驱动 / 漏斗单调 / 异常有规则 | `diagnose` | FAIL 不出诊断 |
| 有假设 / 有停止条件 / 样本量可复算 / 样本量不足不得下结论 | `experiment` | FAIL 不上线 |
| 归因分母=模型合计 / 禁止把相关当因果 | `attribution` | FAIL 不出预算建议 |
| 分母固定 / 留存单调 / 流失可解释 | `retention` | FAIL |
| 回收月≤阈值 / 分母为正 / 贡献毛利为正 | `paid` | FAIL 不扩量 |
| 缺数据不补零 / 三态合法 / 平台白名单 | `selfmedia` | FAIL 不出日报 |
| 留出验证不过即失败 / 贡献 CI 可算 / 训练留出不重叠 | `mmm` | FAIL 不分配预算 |
| 归因分母=diagnose orders、CAC 可复算、支付新客=末触、留存队列=signups | `runner` + `audit` | FAIL 全链不通过 |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 各段门禁 + 三态 | `tests/test_growth_chain.py` | 7 条 + 1 条三态 |
| 端到端 | 同上 | 3 条（run / audit+篡改 / CLI 确定性） |
| 误用拦截 | `misuse/*.json` + 参数化测试 | 3 个（补零 / 相关当因果 / 样本不足） |
| 角色验收 | `run_tests.py` §T16 | run + audit + 跨段一致 + 黄金/误用计数 |
| 任务接入 | `agent.py growth_chain ...` | 子命令全量注册 |

## 6. 最近真实运行

- 时间：2026-11-27
- `python r12-wayingliu-growth/run_tests.py` → PASS 105 / 105
- `python -m pytest r12-wayingliu-growth/tests -q -p no:cacheprovider` → 32 passed
- `python scripts/validate_profiles.py --role r12` → PASS（declared=20）
- `python scripts/check_role_thickness.py --check` → 问题 0；golden 3 / misuse 3
- 链结果：diagnose orders=690、attribution 分母=690、retention 队列=2432=signups、
  paid CAC=91.67（可复算）、MMM holdout R²=0.983、selfmedia=normal

已知边界：MMM 为解析线性模型，不含节假日/竞争项；归因仅覆盖可追踪触点；
自媒体只做规范化与看板，不直连平台 API；真实数据接入需用户配置。
