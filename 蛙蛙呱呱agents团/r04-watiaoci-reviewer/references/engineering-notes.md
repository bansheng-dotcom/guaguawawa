# R04 蛙挑刺（独立评审官 / Reviewer）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/code-review/SKILL.md
>


> 七能力域：成品盘点 / 硬门禁执行与强度审计 / 外置验收判据 / 工作质量批判 /
> 事实核查 / 优点标记与复检 / 人工评审收尾。
> 红线：只评**已存在的成品**，不参与生产、不修复只报告（生产归 R08、修复归 R09）；
> 完成声明必须有本会话新鲜证据（Iron Law）；reviewer==producer 即 FAIL（身份红线）；
> 报告禁 hedge 词（should / probably / seems to / I believe），只写 verified: / not verified:。

## 运行

```bash
python agent.py <skill> <action> --input <json>
```

输出：stdout 单行 `__AGENT_RESULT__ {json}`（含 ok / verdict / checks / next）。

## 技能总览（7 技能 × 15 动作）

| 技能 | 动作 | 干什么 |
|---|---|---|
| artifact | inventory | 交付物料盘点：required 缺失即 FAIL，可选缺失只 INFO（不阻断） |
| artifact | verify | 三级证据链 L1_EXISTS → L2_SUBSTANTIVE → L3_WIRED + stub 反模式扫描 |
| gate | run | 逐命令 subprocess 真实执行：0=PASS / 非0=FAIL / NONE=SKIPPED，超时=FAIL"TIMEOUT" |
| gate | audit | 门禁强度审计 STRENGTH-001..007，评分 0-100（solid / at-risk / theatre 三档） |
| criteria | review | 外置验收判据三态评审 pass/warn/fail，PASS 仅当 0 fail，证据须 file:line 或字段级 |
| criteria | delta | 两轮评审对照：fixed / new / remaining（按判据 id 逐条对拍） |
| quality | critique | 完成声明三查：hedge 词→error、无证据→error、绝对词无证据→error |
| quality | converge | 迭代收敛判定：两轮 findings 总数不再下降即 converged，否则 ITERATING |
| facts | check | 数字五维核查：可追溯 / 来源质量 / 引用完整 / 精度一致 / 覆盖 |
| facts | trace | 单数字回溯：raw 命中→verified；压缩后命中→precision_drift；未命中→hallucinated |
| strengths | mark | 优点标记 keep_list（每项必带 why_keep + evidence） |
| strengths | recheck | 复检三查：降级须理由 / 新 FAIL 须落 change 区 / resolved 不重报 |
| human | package | 人工评审打包：reviewer==producer 即 FAIL（身份红线） |
| human | ingest | 人工批次回灌：comment/edit 契约校验 + applied_plan 逐字回填 |
| human | ack | 归档确认：staged_assets 全部 copied:true 才放行，否则 BLOCKED |

## 边界（这个角色不做什么）

- **只评已存在成品**：物料缺失（required）直接 BLOCKED，R04 不负责把东西做出来；
- **不参与生产**：生产归 R08（建成 MVP），R04 只验收；
- **不修复只报告**：修复归 R09，R04 的产出是 findings / verdict / 评审包，
  绝不在报告里替生产方把问题改掉；
- **评审身份独立**：human/package 时 reviewer==producer 直接 FAIL，
  自评不算评审；
- **结论只写确定性语言**：verified: / not verified:，禁 hedge 词与无证据绝对词
  （quality/critique 会把这类表述打成 error）。

## 输入契约

`python agent.py contract list` 打印 15 个动作的 JSON Schema；
`examples/` 下有全部动作的干净样例 + 脏数据负例（*_dirty）。

## 测试与验收

```bash
python run_tests.py     # 全量断言（目标全绿）
python verify_loop.py   # 15 动作「跑到绿」循环（契约×执行×结构×评审门）
```

## 阈值外置（T9）

所有禁词 / 枚举 / 模式清单 / 评分口径在 `experience/thresholds.json`：
`artifact.stub_markers`、`gate.timeout_s`、`strength.patterns`（001-007）、
`criteria.statuses`、`quality.hedge_words`、`facts.source_type_whitelist`、
`strengths.keep_required_fields`、`human.comment_kinds`、`review.evidence_keys` 等。
**改口径不改代码。**

## 意图路由

`agent.route(text)` 关键词路由：盘点/物料→artifact，门禁/命令/强度→gate，
判据/验收/差异→criteria，质量/禁词/收敛→quality，事实/数字/来源→facts，
优点/保留→strengths，人工/批次/打包/归档→human。

## 案例（T8）

- `cases/landing-acceptance/` 落地页独立验收：判据三态 → 完成声明三查 →
  评审包（身份红线）→ 修复后复评 → 收敛判定 → 优点复检，六步闭环
- `cases/harness-audit/` 门禁强度审计：v1 脏证据 001+007 双触发落 at-risk，
  v2 修复回到 solid，两轮对照

## 参考

- `references/s01-artifact.md` … `references/s07-human.md`（各能力域方法论）

## 来源

- petergyang__human-review（human-review 批次契约：comment / edit / anchor /
  applied_plan / staged_assets；外置判据）
- Intense-Visions__harness-engineering（三级证据链 evidence、硬门禁 verify、
  harness-audit STRENGTH-001..007、quality 批判与收敛）
