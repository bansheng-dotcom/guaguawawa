# 模块D · 优先级与 Backlog（S04）
> 蒸馏自: 补充技能/product-manager/SKILL.md 及相关 workflow
>


## 一、方法论

什么时候用：需求多于产能、要排出「先做哪个」时。优先级不是拍脑袋，是**确定性算术**——
同样的输入永远得出同样的排序，可复算、可质疑、可对拍。

- **Opportunity Score**：衡量「未被满足的重要程度」= Importance × (1 − Satisfaction)，
  重要性高且当前满意度低 = 机会大。
- **ICE**：Impact × Confidence × Ease，快速粗排用。
- **RICE**：(Reach × Impact × Confidence) / Effort，把「影响多少人」纳入，更重证据。
- **Backlog**：结构校验（每条有 title + 验收标准）+ 按 score 降序排序。

## 二、可执行口径（与 skills/s04_priority.py 逐字对齐）

阈值一律以 `experience/thresholds.json` 为准，键名如下：

| 校验 | 读 thresholds.json 键 | 判读 |
|---|---|---|
| RICE effort 下限 | `prioritize.effort_min`（0.1） | effort 过小会放大分数，强制下限防除零 |
| RICE confidence 上限 | `prioritize.confidence_max`（100.0） | clamp 0-100 |
| ICE 各项 | 无阈值（固定 clamp 1-10） | confidence/ease clamp 到 1-10 |
| Opportunity 公式 | 代码内固定 | `Importance×(1−Satisfaction)`，value_created=`Importance×(S2−S1)` |
| Backlog 结构 | 无阈值 | title 非空 + 有 acceptance_criteria/ac |

输出键（contracts.py `priority` 契约）：`ok`、`checks` + 动作专属：
- `opportunity` / `ice` / `rice` → `formula`、`ranked`（按分数降序）
- `backlog` → `item_count`、`ordered`（按 score 降序）

## 三、已验证算例（只写 run_tests.py 真实跑过的数字）

| 算例 | 输入 | 结果 |
|---|---|---|
| RICE | reach=100, impact=0.8, confidence=70, effort=2 | score=28.0 |
| Opportunity | importance=8, satisfaction=0.3 | opportunity_score=5.6 |
| Backlog 排序 | `examples/backlog.json`（3 项） | 首项标题以「分步」开头（score 5 最高） |
| 空 items | `{"items":[]}` | ok=false（无项可排） |

## 四、实战踩坑

1. **`×` 与 `−` 是不同字符**：`formula` 字段含 U+2212（−）在 Windows GBK 控制台会
   抛 `UnicodeEncodeError` 让整个 emit 崩溃。已修（`_common.emit` 重配 stdout 为 UTF-8）。
   这是本角色 `verify_loop` 闭环抓出的真 bug：`priority opportunity` 之前**一运行就崩**，
   smoke 只断言「能跑」时永远暴露不了。
2. **effort 下限是防除零/防放大的硬口径**：effort=0 时 RICE 会除零，代码强制 max(effort,
   effort_min)；判读时要知道「effort 被抬到 0.1」是故意的，不是数据被篡改。
3. **排序是「降序且稳定可复现」**：同分项按原始顺序稳定（`sort(key=-score)`），
   不引入随机 tiebreak；对拍时别假设同分项会乱序。
4. **backlog 的 score 缺省是 0**：`_num(it.get("score"))` 缺省 0，缺 score 的项会沉底，
   不会报错——但这可能掩盖「忘了打分」，review 的 value_utility 会看 `ordered` 是否有
   量化价值。
