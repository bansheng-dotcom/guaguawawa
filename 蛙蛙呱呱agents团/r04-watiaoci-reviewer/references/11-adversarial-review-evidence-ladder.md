# 对抗评审与证据链分级（adversarial review / evidence ladder）

> 定位：本文件补 R04 的「对抗评审 + 三级证据链」方法底座，解释为什么评审不是
> 「看一眼觉得没问题」，而是「用可定位证据把结论逼到不可反驳」。
> 可执行落点：`skills/s01_artifact.py`（L1/L2/L3）、`skills/s02_gate.py`
> （STRENGTH-001..007）、`skills/s05_facts.py`（五维事实核查）、
> `skills/s07_human.py`（独立 reviewer 身份红线）。

## 一、来源（公开标准与方法）

1. **IEEE 1012（System, Software, and Hardware Verification and Validation）**：
   把 V&V 分为「验证（建得对不对）」与「确认（建的是不是要的）」两类活动，
   并要求每项活动产出可审查的证据记录。对应本仓：判据审查（criteria）与
   事实核查（facts）分工，二者都不替代对方。
2. **NASA IV&V 独立性要求**：独立验证与确认（IV&V）组织不得与被评对象存在
   开发责任关系。对应本仓：`human.package` 的 `reviewer != producer` 身份红线；
   同体自评直接 CRITICAL。
3. **CMMI 同行评审（Peer Review）实践**：评审以「缺陷发现效率」为目标，
   要求准备、检查、记录、返工四阶段留痕，且缺陷必须分级。对应本仓：
   `quality.critique` 的 findings schema（error/warning/info）与
   `strengths.recheck` 的「只复评本轮修改」。
4. **对抗式评审（red team / adversarial reviewer）**：主动构造反例与攻击路径，
   而不是顺着作者的叙事找补充。ad/dar 的 adversarial reviewer 口径要求
   先写「这份产物在什么条件下会错」，再验证条件是否成立。
5. **证据分级（evidence hierarchy）**：医学与政策评估常用的证据强度分级
   （系统综述 > 随机对照 > 观察 > 专家意见 > 轶事）。工程评审的等价物是
   「可执行门禁 > 可定位文件行 > 可复算数据 > 口头声明」。
6. **Daubert 标准中的可证伪性/错误率**：专家结论需说明方法与已知错误率。
   对应本仓：每条判据必须带 `file:line` / 字段名 / `verified:` 前缀，
   否则按 `no_evidence` 判 fail。

## 二、三级证据链（L1 → L2 → L3）

R04 把「成品是否存在」拆成串行三级，前一级不过就停，避免用「文件存在」
冒充「工作完成」：

| 级别 | 问题 | 判据 | 失败语义 |
|---|---|---|---|
| L1 EXISTS | 东西在不在？ | 路径非空、文件存在、字节数 ≥ 下限 | BLOCKED，后续不再评 |
| L2 SUBSTANTIVE | 是不是空壳？ | 扫描 stub 标记、`raise NotImplementedError`、空函数体、测试跳过标记 | INCOMPLETE |
| L3 WIRED | 有没有接线？ | 被引用 / 被测试 / 是入口点，三者有其一 | 孤岛工件，INCOMPLETE |

这一分级的意义：**L1 通过率很高，却最容易被当成完成**。只报「文件已生成」
的评审，等于只做了 L1；必须继续问 L2「有没有实质内容」与 L3「有没有人用它」。

## 三、门禁强度 7 模式（STRENGTH-001..007）

门禁本身也会造假。R04 用 7 条模式审计「门禁是不是摆设」：

| 编号 | 反模式 | 识别信号 |
|---|---|---|
| STRENGTH-001 | 门禁永不阻断 | 文档/钩子出现 never blocks / always exits 0 |
| STRENGTH-002 | 回归自动改基线 | baseline.auto_update 为自动模式 |
| STRENGTH-003 | 跳过类别无理由 | skip_categories 超过阈值且缺 justification |
| STRENGTH-004 | 有分层无阈值 | layers 存在但 thresholds 为空 |
| STRENGTH-005 | 默认最低档 | default_tier 落在最低档 |
| STRENGTH-006 | 基线 PR 自动批 | auto_approve=true 或无独立 reviewer |
| STRENGTH-007 | 快照报 passed 但检查没跑 | snapshot.checks 在 signals 里无运行记录 |

评分口径：起始 100，error 扣分、warning 扣分，clamp 到 0–100；
error 存活即 FAIL，不允许用「总体还行」抵消单条 error。

## 四、对抗评审的操作顺序

1. **先定判据，再看成品**：判据必须外置（criteria_ref），避免看完成品再改标准；
2. **先找反例，再找优点**：先问「什么情况下会错」，把可证伪条件写下来；
3. **证据定位到行**：`file:line`、字段名、`verified:` 前缀三选一，否则不算证据；
4. **分级而非一锅端**：critical/high 阻断，medium/low 记录；不许把 high 降成
   「建议」绕过；
5. **复核只评本轮修改**：`strengths.recheck` 防止「旧问题重复报」与「新问题漏报」；
6. **身份独立**：reviewer 与 producer 不得同体；人工批次由 R04 登记，不代改。

## 五、适用边界

- 本方法评的是**已存在的成品/报告/门禁**，不评「尚未实现的设计意图」；
- L1–L3 是结构证据，不证明业务正确；业务正确由判据（criteria）与事实链
  （facts）分别承担，二者都过才叫评审通过；
- STRENGTH 审计针对门禁配置与证据，不评估门禁背后的业务阈值是否合理；
- 人工评审环节只校验批次契约与回填计划，不替代人类判断；
- 评审结论不等于对外发布许可，发布仍由 R01 签发。

## 六、误用反例（对应本仓门禁）

| 误用 | 为什么错 | 本仓拦截 |
|---|---|---|
| 只报「文件已生成」就判完成 | 只做了 L1，空壳/孤岛未检 | `artifact.verify` L2/L3 |
| 用「看起来没问题」当证据 | 不可定位，无法复核 | `criteria.review` 的 `no_evidence` / `evidence_not_specific` |
| 编造一个来源里没有的数字 | 幻觉数字，最重级 | `facts.check` 的 `hallucinated`（critical） |
| 把 12345.6 写成 12,345.60 还说过 | 精度漂移不是原文命中 | `facts.check` 的 `precision_drift`（high） |
| 实现者自己评审自己 | 独立性失效 | `human.package` 的 `self_review`（critical） |
| 门禁写着 never blocks 还算通过 | 门禁是摆设 | `gate.audit` STRENGTH-001 |
| 快照报 passed 但检查从未运行 | 证据链断裂 | `gate.audit` STRENGTH-007 |
| 人工批注 after 被改写后回填 | 丢失用户原话 | `human.ingest` 的 `apply_verbatim` / `after_missing` |

## 七、与本仓测试的对应

- `examples/gate_audit.json` → 7 模式 0 命中，score 100 / solid / PASS；
- `examples/gate_audit_dirty.json` → STRENGTH-001 + 007 → 2 error → FAIL；
- `examples/facts_check.json` → 五维 0 违例；
- `examples/facts_check_dirty.json` → 五维各 1 违例；
- `misuse/facts_missing_source.json` → 断言 `citation_missing` 拦截；
- `misuse/human_self_review.json` → 断言 `self_review` 拦截。

结论：对抗评审的质量不取决于评审者语气多严厉，而取决于**证据能不能被下一个人
在五分钟内复核**。凡是不能被定位、不能被复算、不能被证伪的结论，都应降级为
「未验证」而不是「通过」。
