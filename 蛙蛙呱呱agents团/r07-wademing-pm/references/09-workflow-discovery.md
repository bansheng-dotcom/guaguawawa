# 09 · Discovery 工作法：从访谈记录到可证伪假设

> 服务 R07 W1 `pm_workflows/discovery.py`。本文件只写「怎么做」与「哪里会错」。

## 1. 来源

- 升级方案 §10.3 迁移表：`pm/workflows/pm-thinking/` → `workflows/discovery/`。
- 公开方法：JTBD Job Story（Clayton Christensen / Intercom 的 situation–motivation–outcome 三段式）；
  Opportunity Solution Tree（Teresa Torres, *Continuous Discovery Habits*）；
  Mom Test（Rob Fitzpatrick）强调问过去行为，不问「你想要什么」。
- 本仓现有实现：`skills/s01_discover.py`（jobstory/discover/interview）、
  `skills/s02_ost.py`（ost/assumption/poc）作为单点校验，W1 把它们串成一条链。

## 2. 五段流程

| 段 | 输入 | 产出 | 门禁 |
|---|---|---|---|
| 访谈 | ≥3 条访谈记录（人物、原话、日期） | 原话清单 | 至少 2 条描述过去行为/替代方案 |
| Job story | 情境/动机/期望结果 | job_story | 三段齐全，结果可判断 |
| 机会树 | 机会 statement + 访谈证据 | opportunity_tree | ≥3 个机会，1~3 个入选 |
| 假设 | statement + disproof + test | hypotheses | 每条有推翻阈值与验证方式 |
| POC | 范围/周期/成功指标/回滚 | poc | 周期 1~30 天，指标可测 |

## 3. 三条硬红线（discovery gate）

1. **问题真实**：有访谈原话，且至少 2 条描述「当时怎么做、花了多久、用了什么替代方案」。
   只记录「用户想要 X」不算证据。
2. **假设可证伪**：每条假设必须写「出现什么结果就推翻」，并带阈值（%／人数／时间）。
3. **不是「用户想要」**：主题、机会、假设都不得停留在愿望句；没有行为证据时只能出
   「需求假设卡」，不得进入 PRD。

## 4. 适用边界

- 适用：0→1 新品、存量功能改造前的需求验证、跨角色访谈归纳。
- 不适用：纯技术重构（无用户行为变化）、合规强制项（无需验证需求真伪）、
  已有大样本行为数据可直接定量的场景（可跳过访谈，但仍需假设与 POC）。
- 访谈样本 ≤2 人时只能作为线索，不得作为「问题真实」结论。

## 5. 误用反例

| 误用 | 表现 | 本仓拦截 |
|---|---|---|
| 把「用户想要」当需求 | 3 条访谈全是「想要更炫」 | `discovery.problem_real.not_desire_only`（BLOCKER） |
| 无访谈直接写假设 | interviews 为空 | `problem_real.interviews`（<3 条） |
| 假设不可证伪 | 「如果没效果就不成立」 | `hypothesis.falsifiable`（无阈值） |
| POC 无判定 | 成功指标写「体验更好」 | `poc.metric`（缺 threshold） |

误用样本见 `misuse/discovery_user_wants.json`。
