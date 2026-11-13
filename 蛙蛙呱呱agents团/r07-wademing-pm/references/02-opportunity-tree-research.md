# 模块B · 机会树与用户研究（S02）
> 蒸馏自: 补充技能/product-manager/SKILL.md 及相关 workflow
>


## 一、方法论

什么时候用：产品方向已定，要把「模糊的机会」拆成「可验证的假设」时。OST
（Opportunity Solution Tree）把「用户想要的最终结果」逐层拆到「具体实验」。

- **OST 四层**：Desired Outcome → Opportunities → Solutions → Experiments。
  每一层都比上一层更可执行，最后一层是能跑的实验，而非「做个小程序」这种方案。
- **POC 打分**：把方案按 Feasibility / Impact / Market Fit 三项 1-5 打分，
  总分达推荐阈值才进 POC，避免「想做的都做」。
- **假设优先级**：Risk = (1 − Confidence) × Effort；再按 Impact × Risk 落四象限，
  决定哪条假设最值得先做实验验证。

## 二、可执行口径（与 skills/s02_ost.py 逐字对齐）

阈值一律以 `experience/thresholds.json` 为准，键名如下：

| 校验 | 读 thresholds.json 键 | 判读 |
|---|---|---|
| 机会数 | `ost.opportunities_min` / `ost.opportunities_max` | 3-7 之间，否则 BLOCKER |
| 聚焦数 | `ost.top_focus` | 0 < focus ≤ 3 |
| 每聚焦机会方案数 | `ost.solutions_min` | ≥3；代码按 `op.selected or i<n_focus` 判定 |
| 实验 | `ost.experiments_min` | 至少 1 方案含 hypothesis+method |
| POC 打分 | `ost.poc_scale_min/max` + `ost.poc_recommend_min` | 分数 clamp 到 1-5，总分 ≥12 推荐 |
| 假设风险 | 代码内固定 `Risk=(1-Confidence)×Effort`，effort 下限 0.1 | 见下四象限 |

四象限判读（代码内固定，非阈值）：impact≥0.5 且 risk≥0.5 → experiment；impact≥0.5
→ proceed；risk≥0.5 → reject；否则 → defer。

输出键（contracts.py `ost` 契约）：`ok`、`checks` + 动作专属：
- `ost` → `opportunity_count`、`focus_count`
- `poc` → `recommended_poc`、`solutions`、`recommend_threshold`
- `assumption` → `quadrants`、`assumptions`、`risk_formula`
- `research` → `note_fields`、`feature_request_count`

## 三、已验证算例（只写 run_tests.py 真实跑过的数字）

| 算例 | 输入 | 结果 |
|---|---|---|
| OST 四层 | `examples/ost.json`（3 机会，前 2 聚焦各 3 方案，含实验） | ok=true |
| OST 机会数不足 | `{"desired_outcome":"x","opportunities":[]}` | ok=false（拦下） |
| POC 推荐 | A(5,5,5) + B(2,2,2) | ok=true，`recommended_poc=["A"]`，B 不推荐 |
| POC 全低分 | B(1,1,1) | ok=false（无达标方案） |
| 假设四象限 | impact=0.9, confidence=0.2, effort=1.0 | Risk=0.8，quadrant=experiment |

## 四、实战踩坑

1. **OST 的「聚焦机会方案数」是按聚焦数遍历，不是按 selected**：`_validate_ost` 用
   `i < n_focus` 判定，`n_focus` 来自 `focus` 列表长度。若 focus 写 2 但只给 1 个机会
   配足方案，第二个聚焦机会会被判「方案数 0」——夹具要按 focus 长度配足方案，别只配
   `selected:true` 那一个。
2. **POC 分数要 clamp**：`feasibility` 写 99 或负数不会报错，会被 clamp 到 1-5 再算，
   判读时别被「看起来超高总分」误导——总分上限恒为 15。
3. **假设的 confidence 语义是「置信度」**：`Risk=(1-Confidence)×Effort`，confidence 越高
   风险越低；方向写反会把「高置信」误判成「高风险」，四象限结果全错。
4. **research 的 feature_requests 是「可空但若给则须完整」**：`source`/`frequency`
   缺失才 BLOCKER；空数组不报错，但 `interview_notes` 的 7 字段是硬门禁，缺一个就 FAIL。
