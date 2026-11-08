# 模块A · 产品发现与 JTBD（S01）
> 蒸馏自: 补充技能/product-manager/SKILL.md 及相关 workflow
>


## 一、方法论

什么时候用：拿到一个模糊的「用户想要 X」时，先把**症状**和**根因**分开，再决定要不要
做功能。核心工具是 JTBD（Jobs To Be Done）——用户「雇佣」产品去完成的真实任务，而不是
功能清单。

- **Job story 句式**：`When [情境], I want [动机], so I can [结果]`——三段缺一不可，
  把「谁、在什么触发下、要达成什么」钉死，杜绝「我要一个导出按钮」这种无情境的功能请求。
- **Mom Test 访谈**：只问过去发生的具体行为，不问「你会不会用」；访谈者听多问少，
  推销/引导是访谈污染。
- **8 类风险假设**：value / usability / viability / feasibility / ethics / gtm /
  strategy / team——每条发现计划的假设必须落在其中一类。

## 二、可执行口径（与 skills/s01_discover.py 逐字对齐）

阈值一律以 `experience/thresholds.json` 为准，键名如下，**不手抄数值**：

| 校验 | 读 thresholds.json 键 | 判读 |
|---|---|---|
| Job story 三段 | `discovery.job_story_keys`（situation/motivation/outcome） | 三段俱全 → ok；接受 `fields` 或 `job_story` 文本两种形态 |
| 发现计划 | 无阈值（固定必填 problem/segment/why_now） | 缺任一 → BLOCKER |
| 假设 | `assumption.risk_types`（8 类枚举） | risk_type 不在枚举 → BLOCKER；≥1 条 |
| 验证计划 | 无阈值 | ≥1 项，每项须 hypothesis/method/metric 俱全 |
| 访谈四段 | 代码内固定 band：opening 2-3 / warmup 5 / core 15-20 / wrapup 3-5（分钟） | 超出区间 → BLOCKER |
| Mom Test 规则 | 无阈值 | no_pitching / listen_ratio_80_20 / ask_why_deep 缺失 → BLOCKER |
| 笔记字段 | 代码内固定 4 字段 | participant / biggest_pain / desired_outcome / willingness_to_pay |

输出键（contracts.py `discover` 契约）：`ok`、`checks` + 动作专属：
- `jobstory` → `mode`（fields/text/unknown）
- `discover` → `risk_types`、`assumption_count`、`validation_count`
- `interview` → `sections_band`

## 三、已验证算例（只写 run_tests.py 真实跑过的数字）

| 算例 | 输入 | 结果 |
|---|---|---|
| jobstory 三段 | `examples/jobstory.json`（situation/motivation/outcome 三字段） | ok=true，mode=fields |
| jobstory 缺 outcome | `{"situation":"x","motivation":"y"}` | ok=false（拦下） |
| discover 计划 | problem/segment/why_now + 1 条 value 假设 + 1 项 A/B 验证 | ok=true |
| discover 缺验证计划 | 只有 problem/segment/why_now | ok=false（拦下） |
| 完整闭环 | `examples/discover.json` → verify_loop | 契约+评审 PASS，exit=0 |

## 四、实战踩坑

1. **intent 路由会误路由到 discover**：`run_task` 的 `_INTENT_ROUTES` 里「调研/访谈/发现/
   research/voc/挖掘/报告」关键词，历史上「需求 PRD 分析」曾先命中泛化词被误路由到
   discover（已修：把「prd/需求文档」等具体词排在 discover 之前）。新增路由规则时，
   **具体关键词靠前 + 不区分大小写**，否则泛化词吞掉具体意图。
2. **jobstory 两种形态都要认**：上游可能给 `fields`（situation/motivation/outcome 三键）
   也可能给 `job_story` 文本句式，校验器两条路径都要接，只认一种会误杀合法输入。
3. **风险假设分类是封闭枚举**：risk_type 写成中文或缩写（如「价值」「市场」）会被判非法，
   必须用 8 个英文枚举值之一；这不是苛刻，是对齐上游 phuryn identify-assumptions 的白名单。
