# R19 蛙智模 · 模型工程与 AI 评估官
> 蒸馏自: 补充技能/01-当前能力域/mlflow__mlflow/mlflow/assistant/skills/mlflow-agent/SKILL.md
>


把「从实验追踪到发布证据的模型工程链」做成**本地可运行、可确定性校验**的角色 Agent。
不真连 MLflow / 不真跑评估 / 不真注册模型 / 不真部署，而是把「该追踪什么、该评什么、
什么证据、什么边界」落成白名单 + 确定性算术 + 门禁。

来源仓库：`mlflow__mlflow`（`mlflow/assistant/skills/` 子模块的 10 个技能：
mlflow-agent / mlflow-onboarding / mlflow-docs / mlflow-sagemaker /
mlflow-trace-instrumentation / mlflow-trace-retrieval / mlflow-trace-analysis /
mlflow-trace-metrics / mlflow-evaluation / mlflow-agent-improvement）。

## 能力域 → 技能子命令

| 能力域 | 技能 | 子命令 | 确定性口径 |
|---|---|---|---|
| 实验与运行追踪 | `tracking` | `experiment` / `run` | 用例 2 枚举 + 实验类型 2 枚举 + **tracking_uri 非空**；run 归属实验 + **指标≥1 且皆为数值** + 参数≥1 + 环境非空 |
| 模型注册与版本 | `registry` | `register` / `version` | 阶段 4 枚举 + 来源 4 枚举 + **run_id 关联**；版本号唯一 + **production ≤1** |
| 评估数据与评分器 | `evaluation` | `dataset` / `scorer` | 记录带 **inputs + expectations（ground truth）**；scorer 类型 3 枚举 + target/criteria 非空 + 来源 4 枚举 |
| Agent Trace 与调试 | `trace` | `analyze` / `retrieval` | 状态 4 枚举 + span 类型白名单 + **parent 引用完整** + **ERROR 须定位错误 span**；检索条件非空 + **时间窗有序** + max_results>0 |
| 回归与发布候选 | `release` | `regression` / `candidate` | 诊断层 6 枚举 + **fail-before/pass-after/existing_green 皆 true**；裁决 3 枚举 + 证据≥1 + **PASS 必挂回归** |
| 模型监控接口 | `monitor` | `metrics` / `drift` | 指标名 4 白名单 + 视图 3 枚举 + 聚合 4 枚举 + 时间窗；漂移四要素 + **阈值可量化** + owner=R20 |
| 模型卡与资产证据 | `modelcard` | `card` / `asset` | 五要素（用途/限制/风险分层/许可/已知偏差）+ 风险 3 枚举 + 许可 3 枚举；**资产 path 非空 + run_id 绑定 + 类型合法** |

共 **7 技能 / 14 动作**（14 个门禁）。

## 协作契约

- **inputs**：`dataset` + `model`（消费 R18 数据集、R07 AI 产品需求、R09 服务集成、R03 AI 治理）
- **outputs**：`experiment_log` + `evaluation`（可复现实验 / 评估报告 / 模型版本 / 发布证据）
- 意图路由（`agent.py run --task`）：发布/上线/放行/裁决/回归/阻断 → release/candidate；
  回归测试/fail-before/根因/诊断层 → release/regression；评估/评测/评分/打分/scorer/judge →
  evaluation/scorer；评估集/ground truth/expectations/标注集 → evaluation/dataset；
  追踪/实验/运行记录/参数/指标记录/run → tracking/run；实验登记/实验创建/tracking_uri →
  tracking/experiment；注册/模型版本/模型入库/阶段/registry → registry/register；
  版本清单/版本列表/多版本 → registry/version；trace/跨度/span/链路/错误定位/调试 →
  trace/analyze；检索/过滤/搜索trace/filter → trace/retrieval；监控/指标查询/聚合/趋势 →
  monitor/metrics；漂移/告警阈值/drift → monitor/drift；模型卡/用途/限制/风险分层/许可 →
  modelcard/card；资产/产物/artifact/模型文件 → modelcard/asset；
  兜底 → `evaluation/scorer`。

## 运行

```bash
python agent.py manifest                                          # 契约 + 7 技能清单
python agent.py demo                                              # 生成示例工件
python agent.py tracking experiment  --input examples/tracking_experiment.json
python agent.py registry register    --input examples/registry_register.json
python agent.py evaluation dataset   --input examples/evaluation_dataset.json
python agent.py trace analyze        --input examples/trace_analyze.json
python agent.py release candidate    --input examples/release_candidate.json
python agent.py monitor metrics      --input examples/monitor_metrics.json
python agent.py modelcard card       --input examples/modelcard_card.json
python agent.py harness tracking_run --input examples/tracking_run.json
python agent.py contract list
python agent.py case list
python verify_loop.py                                             # 28 行闭环矩阵
python run_tests.py                                               # 一键验收，期望 ALL GREEN
```

## 边界（角色分工与红线）

- **统计结论 / 相关性分析 / 显著性检验 / 业务归因 / 决策建议**归 R06 蛙得清。
- **生产部署 / 灰度发布 / 流量切分 / 模型分发**归 R09 蛙联调；**持续监控与告警
  执行**归 R20 蛙值守；**模型风险与许可的法律判定**归 R03 AI 治理。
- 本角色只产出**模型工程工件**（实验记录、运行记录、模型注册、版本清单、评估集、
  评分器、Trace 报告、回归报告、发布候选、监控需求、模型卡、资产证据），
  不解释数字、不做业务决策、不执行部署动作。
- **红线（不可越）**：
  1. **不携带凭据**：api_key / secret / password / token / 私钥 / 密钥 / 密码 /
     连接串等凭据一律不出现在产出（凭据走环境变量 / 密钥管理）。
  2. **不许「效果看起来不错」直接上线**：任何上线结论必须有评估证据 + 回归报告
     （fail-before/pass-after），凭主观感受（"效果不错""应该没问题"）绕过评估一律拦下。
  3. **不做统计结论 / 业务归因 / 决策建议**：相关性、显著性、归因、增长建议等
     一律移交 R06。

## Honest capability status and safe local execution

`manifest` marks local evaluation/model-card generation `real` and model publication `blocked`. `python agent.py local --input <evaluation.json>` scores expected/predicted records locally; it does not publish any model. External unavailable services are blocked.


- 干净数据 → `ok=true` / exit 0；脏数据（枚举越界 / 缺 ground truth / 悬空引用 /
  ERROR 未定位 / 回归证据缺失 / 裁决越界 / 资产不可溯源）→ `ok=false` / exit 1。
- 对抗评审五检查：`contract` / `credential_gate` / `fake_pass_gate` /
  `scope_boundary` / `concrete_artifact`；失败按类别 route 回 writer
  （凭据入工件 / 主观放行 / 越界统计）或 controller（无工件 / 无价值），
  类别为 `credential_gate` / `fake_pass` / `scope_overlap` /
  `artifact_not_concrete` / `no_report_value`。
- 阈值全部外置在 `experience/thresholds.json`，改口径不改代码；案例可再覆盖
  （如 `regression-gate` 补充主观放行词表，`model-release` 补充资产类型白名单）。
- Windows GBK 控制台：所有输出经 UTF-8 重配置，verify_loop 使用 `[OK]` / `[XX]` ASCII 标记。

## 「可复现实验 vs 业务结论」的分工哲学（本角色新经验）

模型工程角色最易踩的坑是**把"实验/评估是否可复现、证据是否齐全"和"这个模型好不好、
该不该上线"混为一谈**。本角色的核心设计：

1. **边界是职责**：R19 判「实验是否可复现、评估是否有标可对、回归是否证明改进、
   证据是否齐全」，R06 判「模型好不好、该不该上、业务上值不值」。前者是工程确定性
   （枚举/阈值/证据链），后者是业务语义（效果/收益/风险）。
2. **「效果看起来不错」是头号红线**：与 R18 拦「擅自回填」类似，R19 拦「凭主观
   感受放行」。硬证据（评估结果 + fail-before/pass-after 回归 + 证据链）是上线的
   唯一通行证。
3. **不可逆动作聚集区**：生产部署 / 灰度 / 流量切分 / 模型分发 / 监控告警执行全部
   挡在执行面之外，只产出**工件 + handoff 声明**（同 R14 拦退款、R15 拦付款、
   R16 拦发薪、R18 拦回填）。
4. **宁可拦错，不可放过**：评估误报只是多一步人工确认；放过"无回归的 PASS"
   或"无溯源的资产"，会把未验证的模型或来源不明的产物漏进生产。
