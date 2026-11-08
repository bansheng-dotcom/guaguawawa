# 模块F · 产品愿景与指标（S06）
> 蒸馏自: 补充技能/product-manager/SKILL.md 及相关 workflow
>


## 一、方法论

什么时候用：要回答「这个产品长期为什么存在、怎么判断它变好了」时。愿景回答「往哪走」，
指标回答「怎么量」；北极星指标是把「交付价值」压缩成一个可追踪数字，护栏指标防止
「为冲数字牺牲体验」。

- **北极星指标（NSM）7 标准**：表达价值 / 可衡量 / 有输入指标 / 有护栏 / 可行动 /
  有时窗 / 非虚荣。
- **指标分层**：北极星 / 输入 / 护栏 / 商业——每层一个用途，别混。
- **OKR**：3 套 × 3 KR，信心 60-70%。
- **愿景 3 标准**：Inspiring / Achievable / Emotional，3-5 个变体。
- **Lean Canvas 九段**：problem/solution/uvp/unfair_advantage/segments/channels/
  revenue/cost/key_metrics。

## 二、可执行口径（与 skills/s06_metrics.py 逐字对齐）

阈值一律以 `experience/thresholds.json` 为准，键名如下：

| 校验 | 读 thresholds.json 键 | 判读 |
|---|---|---|
| NSM 输入指标 | `metrics.input_metrics_min/max`（3-5） | 超出区间 → BLOCKER |
| NSM 护栏 | 无阈值（固定） | ≥1 个护栏指标 |
| NSM 非虚荣 | 无阈值（固定） | 含「提升用户体验/提高效率/满意度/好评」→ BLOCKER |
| 指标分层 | 无阈值（固定 4 层枚举） | 至少 1 北极星 + 1 护栏；每指标有 definition + data_source |
| OKR 套数 | `metrics.okr_sets`（3） | 不等于 3 → BLOCKER |
| OKR 每套 KR | `metrics.okr_kr_per_set`（3） | 不等于 3 → BLOCKER |
| OKR 信心 | `metrics.okr_confidence_min/max`（60-70） | 超出区间 → BLOCKER |
| 愿景变体 | 无阈值（固定 3-5） | 超出区间 → BLOCKER |
| 画布九段 | 无阈值（固定 9 段） | 缺一段 → BLOCKER |

输出键（contracts.py `metrics` 契约）：`ok`、`checks` + 动作专属：
- `northstar` → `nsm_criteria`、`input_metric_count`
- `metrics` → `layers`、`metric_count`
- `okr` → `okr_sets`、`confidence`
- `vision` → `variant_count`
- `canvas` → `canvas_sections`

## 三、已验证算例（只写 run_tests.py 真实跑过的数字）

| 算例 | 输入 | 结果 |
|---|---|---|
| NSM | `examples/northstar.json`（7 日激活率 + 3 输入指标 + 2 护栏） | ok=true |
| NSM 虚荣 | `north_star="提升用户体验", input_metrics=["a"]` | ok=false（虚荣 + 输入数不足） |
| 指标分层 | 3 指标（北极星/输入/护栏，各带 definition+data_source） | ok=true |
| OKR 3×3 | 3 套 × 3 KR + confidence=65 | ok=true |
| 愿景 | vision + 3 标准 + 3 变体 | ok=true |
| 画布九段 | 9 段俱全 | ok=true |

## 四、实战踩坑

1. **早退路径要保契约字段（同 S05）**：`_metrics` 空数组、`_okr` 空 sets 的早退路径
   最初漏 `layers`/`okr_sets` 输出字段，verify_loop 抓出「脏行输出缺必填字段」。
   （已修：早退补 `layers={k:0}` / `okr_sets=0`。）任何 `return {ok:false}` 的早退，
   都要带上契约要求的专属字段。
2. **虚荣指标是「子串匹配」**：`_northstar` 用 `any(v in str(data) for v in (...))`，
   整个 data 序列化后匹配——连「满意度」出现在任意字段都会被判虚荣。写北极星别用
   「满意度/好评」这类词，用「7 日激活率」「周均完成项目数」这种可量词。
3. **OKR 信心是整数区间**：`int(data.get("confidence", 65))`，confidence 写成 65.5 会
   被截断；且默认 65，缺 confidence 不报错但落默认值——判读时留意「没写信心」静默
   通过。
4. **指标分层的 layer 是封闭枚举**：`north_star/input/guardrail/business` 之外的值
   直接 BLOCKER，且「至少 1 北极星 + 1 护栏」是硬门槛，只写 input 层不行。
