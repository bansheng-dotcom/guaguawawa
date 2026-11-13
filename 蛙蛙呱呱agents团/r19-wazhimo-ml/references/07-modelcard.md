# 07 · 模型卡与资产证据口径（modelcard）
> 蒸馏自: 补充技能/01-当前能力域/mlflow__mlflow/mlflow/assistant/skills/mlflow-docs/SKILL.md
>


> 技能：`modelcard` ｜ 动作：`card`（模型卡）、`asset`（资产证据）
> 来源：mlflow__mlflow（模型元数据/模型卡：用途、限制、风险、许可；Tracking 的 artifact：运行产物路径与 run_id 绑定）

## 第一层：方法论

模型卡与资产是 R19 的**交付说明书**。用途、限制、风险分层、许可、已知偏差，
以及能追溯的资产——这几样构成「交付给下游的是什么、不能用来干什么」的地基。
把这段做成确定性校验的价值，不在于「写得更漂亮」，而在于**让不可追溯、说不清
边界的东西在交付层就发不出来**。

三条方法论：

1. **模型卡是说明书不是营销页**。必须写清「不能用来干什么」（limitations）与
   「已知会出什么偏差」（known_bias）。只写"什么都能答"的模型卡是危险的——它
   让下游误以为没有边界。
2. **风险分层与许可必须走白名单**。`risk_tier`（low/medium/high）与 `license`
   （proprietary/open_source/research_only）是合规登记的固定档位，不是自由文本。
3. **资产必须能追溯到 run_id**。每个 artifact（模型文件/评估报告/图表）都要绑定
   产生它的运行 ID。没有 run_id 的资产是"来源不明的产物"，不予接收。

**本角色绝对不做的事**：**绝不打包分发模型**。R19 只产出模型卡与资产证据工件；
打包、分发、部署归 R09 服务集成。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| card.model_name | 非空 | Model Registry |
| card.intended_use | 非空（预期用途） | model card 口径 |
| card.limitations | 非空（限制，"不能干什么"） | model card 口径 |
| card.risk_tier | ∈ `modelcard.risk_tiers` = `[low, medium, high]` | R19 模型卡口径 |
| card.license | ∈ `modelcard.license_types` = `[proprietary, open_source, research_only]` | R19 模型卡口径 |
| card.known_bias | 非空（已知偏差） | model card 口径 |
| asset.assets | ≥ 1 项 | mlflow artifact |
| asset.path | 每项 path 非空 | mlflow artifact |
| asset.run_binding | 每项 run_id 非空 | mlflow tracking |
| asset.type | 每项 type 合法 | R19 资产口径 |

**阈值单一真源**：`modelcard.risk_tiers` / `modelcard.license_types` 以
`experience/thresholds.json` 的 `modelcard` 段为准。资产类型白名单：
`[model_file, eval_report, chart, dataset_snapshot, config]`。

## 第三层：已验证的算例

**算例 A（干净模型卡）**：`examples/modelcard_card.json`
```
support-qa-assistant / 用途明确 / 限制明确 / medium / proprietary / 有已知偏差
```
五要素齐备 → `ok=true`，`verdict=PASS`。

**算例 B（脏模型卡）**：`examples/modelcard_card_dirty.json`
```
用途="什么都能答" / limitations="" / risk_tier=none / license="免费随便用" / bias=""
```
BLOCKER ×4：限制为空；风险分层越界；许可越界；已知偏差为空。

**算例 C（干净资产）**：`examples/modelcard_asset.json`
```
3 项 / 全绑 run-88213 / type ∈ {model_file, eval_report, chart}
```
路径非空、run 绑定、类型合法 → `ok=true`。

**算例 D（脏资产）**：`examples/modelcard_asset_dirty.json`
```
path="" / run_id="" / type=binary_blob / type=misc
```
BLOCKER ×5：路径为空、run_id 为空、类型越界。

## 第四层：实战踩坑

1. **limitations 留空是最常见的违规**。很多人觉得"写限制显得模型弱"，于是留空。
   但模型卡的contract恰恰是写清边界——留空即 BLOCKER。

2. **risk_tier 没有 "none"**。不是"没风险"，而是要显式给出 low/medium/high。
   填 `none` 会被拦——它不在白名单内。

3. **license 白名单是集体的固定档**。写 `MIT` / `Apache-2.0` / `免费随便用` 都
   不在白名单内。R19 只认 `[proprietary, open_source, research_only]` 这三种
   口径；具体 SPDX 标识在 R03 做合规判定时展开。

4. **资产路径可以是本地路径或 runs:/ 形式**。校验只查 path 非空（不解析实际
   文件是否存在，因为校验时文件可能还没落盘），但口径上要求能定位。

5. **run_id 是资产的溯源锚点**。没有 run_id 的资产无法回答"这个模型文件是哪次
   实验产出的、用的什么参数"——等于来源不明的产物。

6. **known_bias 是伦理/合规的必填项**。哪怕结论是"目前未发现明显偏差"，也要写
   出来（显式声明），而不是留空。留空无法区分"没测"和"没问题"。

7. **不要在结论里写"我把模型打包发给下游了"**。这是越权（分发归 R09）。正确
   写法："产出模型卡 support-qa-assistant 与 3 项可溯源资产，实际分发交 R09。"
