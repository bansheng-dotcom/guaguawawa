# 02 · 模型注册与版本口径（registry）
> 蒸馏自: 补充技能/01-当前能力域/mlflow__mlflow/mlflow/assistant/skills/mlflow-agent/SKILL.md
>


> 技能：`registry` ｜ 动作：`register`（模型注册记录）、`version`（版本清单）
> 来源：mlflow__mlflow（Model Registry：候选模型、版本、stage 阶段白名单、source 来源、run_id 关联）

## 第一层：方法论

模型注册的核心是**「候选模型入库」而不是「模型上线」**。名字、版本、阶段、来源、
关联运行——这五样构成「这个候选是谁、从哪来、处于生命周期的哪一步」的地基。把这段
做成确定性校验的价值，不在于「登记得更全」，而在于**让不可追溯的候选在入库层就
发不出来**。

三条方法论：

1. **注册 ≠ 部署**。`stage=production` 只说明这个版本被标定为"生产候选"，不代表
   它已经在跑生产流量。把注册当成部署是 R19 最危险的误读——生产流量的切换是
   R09 的部署动作。
2. **来源必须可枚举**。`source`（mlflow / dspy / litellm / custom）说明模型从
   哪个框架或方式产出的。来源不明 → 后续的复现、回滚、依赖审计都无从谈起。
3. **run_id 是候选与实验之间唯一的线**。没有 run_id 的注册记录，你不知道这个
   模型是哪次运行产出的，也不知道它的指标和参数——一条断掉的溯源链。

**本角色绝对不做的事**：**绝不把注册等同于生产部署**。registry 只维护候选与
版本的生命周期元数据；模型权重、推理服务、GPU 资源另行准备（R09 + 人工）。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| register.model_name | 非空 | Model Registry |
| register.version | 非空 | Model Registry |
| register.stage | ∈ `registry.stages` = `[none, staging, production, archived]` | Model Registry |
| register.source | ∈ `registry.model_sources` = `[mlflow, dspy, litellm, custom]` | R19 来源口径 |
| register.run_id | 非空（可追溯到实验运行） | MLflow Tracking 关联 |
| version.model_name | 非空 | Model Registry |
| version.versions | ≥ 1 项 | Model Registry |
| version.valid | 每项 version 非空且 stage 在白名单 | Model Registry |
| version.unique | 版本号唯一 | 版本语义 |
| version.single_prod | production 阶段 ≤ 1 | 单一生产版本原则 |

**阈值单一真源**：`registry.stages` / `registry.model_sources` 以
`experience/thresholds.json` 的 `registry` 段为准。

## 第三层：已验证的算例

**算例 A（干净注册）**：`examples/registry_register.json`
```
support-qa-assistant / v3 / stage=staging / source=mlflow / run-88213
```
阶段与来源都在白名单、run_id 关联 → `ok=true`，`verdict=PASS`。

**算例 B（脏注册）**：`examples/registry_register_dirty.json`
```
support-qa-assistant / v3 / stage=live / source=huggingface_hub
```
BLOCKER ×2：`stage='live'` 不在白名单；`source='huggingface_hub'` 不在白名单。

**算例 C（干净版本清单）**：`examples/registry_version.json`
```
v1=archived / v2=archived / v3=production
```
阶段全合法、版本号唯一、production 恰 1 个 → `ok=true`。

**算例 D（脏版本清单）**：`examples/registry_version_dirty.json`
```
v3=production / v4=production / v5=shadow
```
BLOCKER ×2：两个 production（违反 single_prod）；`stage='shadow'` 不在白名单。

## 第四层：实战踩坑

1. **`single_prod` 是"至多一个"不是"恰好一个"**。`≤ 1` 允许零个 production
   （比如所有版本都还在 staging），但绝不允许两个——两个生产版本会让流量切分
   变成掷骰子。

2. **版本号是字符串不是数值**。`"3"` 与 `"3.0"` 与 `"v3"` 是不同的版本号，
   唯一性检查按字符串精确匹配，不做数值归一化——归一化会把 `1.0` 和 `1` 误判为
   同一个版本。

3. **`stage=none` 是合法态**。不是所有候选都要立刻进 staging，`none` 表示
   "刚入库、未指定阶段"，属于白名单内的合法值，不要误拦。

4. **source 白名单是封闭的**。写 `openai` / `huggingface_hub` / `ollama` 都不
   在白名单内——R19 只认 `[mlflow, dspy, litellm, custom]` 这四种来源口径。不是
   这些来源的模型，归 `custom` 并说明。

5. **不要在结论里写"我已把 v3 切到生产"**。这是越权措辞，会触发 review 的
   scope_boundary。正确写法："v3 标定为 production 阶段的发布候选，实际流量切换
   交 R09，本工件仅登记阶段元数据。"

6. **run_id 关联是溯源不是装饰**。有人把 `run_id` 填成模型文件名或随便一个 ID，
   校验只查非空查不出真假。口径上应说明：run_id 必须是 MLflow 运行 ID，能反查
   到参数与指标。
