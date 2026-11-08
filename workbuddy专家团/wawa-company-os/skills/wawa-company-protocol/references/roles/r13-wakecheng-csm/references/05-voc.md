# s05 客户反馈与 VOC（survey / voc）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/customer-voice/SKILL.md
>


来源沉淀：`formbricks__formbricks` —— `Survey`（type: link/app、status:
draft/inProgress/paused/completed）、`Response`（finished/data/contact）、
`TSurveyElementTypeEnum`（openText/nps/rating/csat/ces/matrix/ranking 等 17 种题型）。
NPS 三桶切分取自 formbricks 的 NPS 题型标准口径，不是本角色自创。

## 一、方法论（什么时候用、核心口径）

VOC 的价值不是「收集了一堆分数」，而是**能用标准公式复算、并在样本不足时克制地下结论**。
所以本能力域做两件事：

- `survey`：校验问卷结构——类型/状态白名单、题目非空、题型白名单。
- `voc`：校验回收数据并实算 NPS——三桶切分、0-10 越界、样本量、响应率、主题提炼。

**NPS 口径（真源）**：`NPS = (promoter% − detractor%) × 100`，
`promoter ≥ 9`、`detractor ≤ 6`（0-10 分制），7-8 为 passive 不进分子也不进分母的调整。

立场：**样本量不足只报告不作结论**——10 份以内的 NPS 波动极大，用它做战略决策是
自欺。所以 `min_responses=10`，低于它仍在输出里，但明确标注「仅报告」。

边界：统计显著性、因果归因交 R06；VOC 结论转成需求交 R07；不替 R12 做口碑投放。

## 二、可执行口径（与实现逐字对齐）

阈值外置在 `voc` 节：

- `survey_types`：`link / app`
- `survey_status`：`draft / inProgress / paused / completed`
- `element_types`：17 种官方题型（fileUpload/openText/multipleChoiceSingle/multipleChoiceMulti/
  nps/cta/rating/consent/pictureSelection/cal/date/matrix/address/ranking/contactInfo/csat/ces）
- `nps_promoter_min`：9；`nps_detractor_max`：6；`nps_good`：30
- `response_rate_min`：0.1；`min_responses`：10；`theme_min_mentions`：3

**survey 校验规则**：类型/状态越界、名称空、题目为空、题型越界、题目无标题 → BLOCKER。

**voc 校验规则**：
- 任一 `nps_score` 不在 0-10 → BLOCKER。
- 有 `sent_count` 时 `响应数/发出数 < 0.1` → BLOCKER；未提供则跳过。
- 样本量 < 10 → 只报告不作结论（不 FAIL）。
- 主题提炼：开放文本二元组词频 ≥ 3 次才成为主题，输出前 10 个。

**输出键**：survey → `element_count`；voc → `response_count / nps_score /
promoter_count / detractor_count / theme_count / themes`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿）

`examples/voc.json`（50 发 10 回收）：

| 分数 | 9 | 10 | 8 | 6 | 4 | 3 | 9 | 10 | 7 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 桶 | P | P | P/A | D | D | D | P | P | P/A | P |

推荐者 5、贬损者 3、被动 2 → NPS = (5−3)/10×100 = **20.0**；
响应率 10/50 = 0.2 ≥ 0.1；主题 7 个（「响应」「应速」「速度」等）→ ok=true。
`examples/survey.json`：3 题（csat/nps/openText）→ `element_count=3`。
`examples/voc_dirty.json`：nps_score=99 越界 + 10/50 变成 1/50 响应率 → 两条 BLOCKER。
`examples/survey_dirty.json`：名称空、type=`email`、status=`archived`、题型 `vote` 全越界。

## 四、实战踩坑（真拦下来的教训）

- **把 0-10 当成 1-10**：少一个 0 分档会让 detractor 少算，NPS 虚高。
- **分子分母口径错**：passive（7-8）既不是推荐者也不是贬损者，不能塞进任何一桶；
  正确做法是都计入分母、都不计入分子——本实现即如此。
- **响应率用「回收/发出」不是「完成/打开」**：后者会被自动打开率稀释，看起来很好。
- **小样本结论**：3 个人打 10 分就得出「NPS=100」是常见误导，必须挂样本量标注。
- **中文分词用二元组是近似**：主题词会出现「应速」「应速」这类切碎结果，所以
  `theme_count` 只做「是否有集中反馈」的信号，具体归类仍要人看一眼原文。
