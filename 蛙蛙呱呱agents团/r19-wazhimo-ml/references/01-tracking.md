# 01 · 实验与运行追踪口径（tracking）
> 蒸馏自: 补充技能/01-当前能力域/mlflow__mlflow/mlflow/assistant/skills/mlflow-agent/SKILL.md
>


> 技能：`tracking` ｜ 动作：`experiment`（实验记录）、`run`（单次运行记录）
> 来源：mlflow__mlflow（`mlflow/assistant/skills/mlflow-onboarding` 的实验/用例类型判定、MLflow Tracking 的参数/指标/工件/运行环境口径、`mlflow.experimentKind` 标签）

## 第一层：方法论

实验追踪的第一件事是**「把这次跑的是什么、用什么配置、得到什么结果」钉死**。
参数、指标、环境、追踪后端——这四样构成「结果能不能被复现」的地基。把这段做成
确定性校验的价值，不在于「记得更全」，而在于**让不可复现的实验在登记层就发不出来**。

三条方法论：

1. **实验类型与用例类型是两个正交维度**。`use_case`（genai / traditional_ml）
   说的是「这条链路服务什么场景」，`experiment_kind`（genai_development /
   custom_model_development）说的是「这次开发活动是什么性质」。两者都不是自由
   文本，必须落在白名单内——写错任一，后续的评估、监控口径都会错配。
2. **指标必须记、且必须是数值**。至少记录一个指标，且值为数值——字符串指标无法
   比较、无法排序、无法画趋势。空指标表不是「还没记」，而是「这次运行没有可比较
   的产出」。
3. **环境与追踪后端是可复现的两条腿**。`environment`（框架/版本）说明「在什么
   环境跑的」，`tracking_uri` 说明「结果存在哪个后端」。缺任一，别人拿到 run_id
   也复现不出来。

**本角色绝对不做的事**：**绝不把实验追踪等同于生产部署**。登记一次 run 只说明
"这个配置跑出了这个结果"，不说明"这个模型已经上线"。上线是 s05 release 的发布
候选裁决 + R09 的部署动作。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| experiment.experiment_id | 非空 | MLflow Tracking |
| experiment.name | 非空 | MLflow Tracking |
| experiment.use_case | ∈ `tracking.use_cases` = `[genai, traditional_ml]` | mlflow-onboarding |
| experiment.experiment_kind | ∈ `tracking.experiment_kinds` = `[genai_development, custom_model_development]` | mlflow.experimentKind |
| experiment.tracking_uri | 非空（可复现后端） | MLflow Tracking |
| run.run_id | 非空 | MLflow Tracking |
| run.experiment_id | 非空（归属实验） | MLflow Tracking |
| run.metrics | 字典且 ≥ 1 键 | MLflow Tracking |
| run.metric_numeric | 每个指标值为数值（排除 bool） | 可比较性要求 |
| run.params | 字典且 ≥ 1 键 | MLflow Tracking |
| run.environment | 非空 | 复现要求 |

**阈值单一真源**：`tracking.use_cases` / `tracking.experiment_kinds` 以
`experience/thresholds.json` 的 `tracking` 段为准。

## 第三层：已验证的算例

**算例 A（干净实验）**：`examples/tracking_experiment.json`
```
exp-2041 / 客服问答助手评估 / use_case=genai / kind=genai_development
```
两个维度都在白名单、tracking_uri 非空 → `ok=true`，`verdict=PASS`。

**算例 B（脏实验）**：`examples/tracking_experiment_dirty.json`
```
exp-2041 / use_case=code_review / kind=genai_development
```
BLOCKER ×1：`use_case='code_review'` 不在白名单 `[genai, traditional_ml]`。

**算例 C（干净运行）**：`examples/tracking_run.json`
```
run-88213 / 3 指标 / 3 参数 / environment=staging
```
指标全为数值、参数非空、环境已声明 → `ok=true`。

**算例 D（脏运行）**：`examples/tracking_run_dirty.json`
```
run-88214 / metrics={} / params={} / environment=""
```
BLOCKER ×3：指标表为空、参数为空、环境未声明。

## 第四层：实战踩坑

1. **bool 不是数值**。Python 里 `True` 是 `int` 的子类，`isinstance(True, int)`
   为 True。指标校验必须显式排除 bool，否则 `{"passed": true}` 会被当成合法数值
   指标混进来。

2. **`use_case` 与 `experiment_kind` 常被填反**。有人把 `genai` 填进
   `experiment_kind`、把 `genai_development` 填进 `use_case`——两个维度名字相似，
   校验必须各自走各自的白名单，不能用「任一命中即可」偷懒。

3. **tracking_uri 不要在结论里写具体地址**。写 `http://user:pass@host:5000`
   会把凭据带进工件（触发 review 的 credential_gate）。正确写法是声明"追踪后端
   已配置（密钥管理）"，地址本身走环境变量。

4. **空指标 ≠ 指标为零**。`metrics={}` 是"没记录"，`metrics={"accuracy": 0.0}`
   是"记录了且值为零"。前者 BLOCKER，后者合法。

5. **environment 的口径是字符串非空**。`staging` / `production` / 框架版本串
   （`pytorch-2.1`）皆可，空串或缺失一律 BLOCKER——没有环境声明的 run 是不可
   复现的。

6. **run 必须归属实验**。只给 `run_id` 不给 `experiment_id`，run 就成了孤儿，
   在实验列表里找不到。归属非空是硬要求。
