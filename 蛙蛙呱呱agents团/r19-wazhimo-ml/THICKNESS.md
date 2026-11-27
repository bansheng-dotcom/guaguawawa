# R19 蛙之模 · 厚度自述（T11 / L2）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写可被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | `references/` 10 篇 / 约 52.2KB（`check_role_thickness --report` 可复核） |
| 来源 | MLflow（tracking/registry/evaluation/model card）公开口径 |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列误用反例，并对应本仓门禁 |

## 2. 生产层

`skills/` 8 个能力域：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `tracking` | 实验/运行 | 指标、参数、环境可复现 |
| 2 | `registry` | 注册/版本 | 阶段白名单、run_id 绑定、单一 production |
| 3 | `evaluation` | 数据集/评分器 | inputs+expectations、评分器四要素 |
| 4 | `trace` | 轨迹 | 检索/分析 |
| 5 | `release` | 回归/候选 | fail-before/pass-after、三裁决 |
| 6 | `monitor` | 指标/漂移 | 阈值、渠道、owner |
| 7 | `modelcard` | 模型卡/资产 | 用途/限制/风险/许可/偏差、资产溯源 |
| 8 | `eval-ci` | 评测回归 | CI 门槛 |

黄金链：`tracking.run → evaluation.dataset → registry.register → modelcard.card`；
`evaluation.scorer → release.regression → candidate → monitor.drift`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 干净/脏夹具 | `examples/*.json`（29 个） | 每动作配对，脏件断言被拦 |
| 案例包 | `cases/`（18 个文件） | SOP 与经验 |
| 黄金成品 | `golden/experiment-and-modelcard.html`、`golden/release-and-eval.html` | 含夹具 sha256 与 41 条门禁 |
| 规格 | `ML_SPEC.md` | 8 门禁 + 5 KPI |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 指标/参数/环境完整 | `tracking.run` → `run.*` | BLOCKER |
| 数据集须带 ground truth | `evaluation.dataset` → `dataset.expectations` | BLOCKER |
| 评分器类型/目标/判据/来源 | `evaluation.scorer` → `scorer.*` | BLOCKER |
| 版本阶段白名单/唯一 | `registry.version` → `version.*` | BLOCKER |
| 至多一个 production | `registry.version` → `version.single_prod` | BLOCKER |
| fail-before/pass-after | `release.regression` → `regression.*` | BLOCKER |
| PASS 须挂回归报告 | `release.candidate` → `candidate.regression_required` | BLOCKER |
| 模型卡五要素 | `modelcard.card` → `card.*` | BLOCKER |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 技能与契约 | `tests/test_skills.py`、`tests/test_contracts.py` | 覆盖全部动作 |
| 黄金成品 | `tests/test_thickness_samples.py::ThicknessSamples` | 2 份 |
| 误用反例 | `misuse/*.json` + 同测试 | 2 个（无评测集、双 production） |
| 端到端 | `run_tests.py` T01–T16 | 全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r19-wazhimo-ml/golden/build_golden.py`
- 产物：`experiment-and-modelcard.html`（21 条门禁，0 未过）、
  `release-and-eval.html`（20 条门禁，0 未过）
- 命令：`python r19-wazhimo-ml/run_tests.py`
- 结果：全绿（含厚度样本 T16）

## 7. 已知边界

- 注册 ≠ 部署；发布候选 ≠ 生产部署；上线/回滚由 R09/R20 执行；
- 只产评测/候选工件，不产出「模型好不好」的结论；
- 模型权重/推理服务/GPU 另行准备，分发归 R09。
