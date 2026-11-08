# S05 事实核查（check / trace）
> 蒸馏自: 补充技能/01-当前能力域/open-gsd__gsd-core/skills/fact-check/SKILL.md
>


## 方法论（来源 harness-engineering / facts）

评审报告里的每个数字都要能回答：**从哪来？**两粒度：

- **check**：整份报告五维体检；
- **trace**：单个数字逐字回溯到来源文本。

五维：数字可追溯（每个数有 source）/ 来源质量（primary 优先）/
引用完整性（引用能对上）/ 精度一致（没四舍五入漂移）/ 覆盖
（关键指标没漏）。

## 可执行口径

- check 五维违例枚举与 severity 映射外置在 `facts.severities`：
  hallucinated=critical / unsourced=high / invalid_source_type=high /
  citation_missing=high / precision_drift=high / coverage_gap=medium；
  `facts.blocking_severities` 内的 severity 出现即整体 FAIL；
  来源类型白名单：`facts.source_type_whitelist`（primary / secondary / unsourced）。
- trace 单数字三态：
  - **verified**：raw 原文命中来源；
  - **precision_drift**：压缩后（去空格 / 去千分位逗号）才命中——
    数字对但精度变了，仍算违例（high）；
  - **hallucinated**：怎么都找不到——最重（critical）。

## 已验证算例

- `examples/facts_check.json`：干净件五维全过；
- `examples/facts_check_dirty.json`：五维各 1 违例——
  一个编造数、一个无来源、一个非法来源类型、一个引用缺失、一个覆盖缺口，
  critical+high 在 `facts.blocking_severities` 内 → FAIL；
- `examples/facts_trace.json` + `facts_trace_source.txt`：
  同一来源文件里三种数字（原样 / 千分位 / 根本没有）分别落
  verified / precision_drift / hallucinated。

## 实战踩坑

- **precision_drift 不是 hallucinated**：12345.6 写成 12,345.60 是精度漂移，
  编个来源里没有的数才是幻觉——两者 severity 不同，别合并；
- 回溯匹配先试 raw 原文、再试压缩形——顺序反了会把所有千分位数字
  误判成 verified；
- unsourced 数字哪怕看着合理也是 high：评审报告里「没有来源」
  本身就是违例。
