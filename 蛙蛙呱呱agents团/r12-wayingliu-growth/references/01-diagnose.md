# s01 增长诊断与基线（diagnose / unit）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/marketing/performance-report/SKILL.md
>


来源沉淀：`coreyhaines31__marketingskills`（marketing-plan 的基线设定、analytics 的指标口径、
revops 的单位经济）+ `retieedra-profound__skills-marketing-library`（营销指标库，去重后不重复计数）。

## 一、方法论（什么时候用、核心口径）

增长诊断是增长系统最便宜的纠错点。本角色的立场：**诊断不能靠感觉，要能复算**。两个动作：
- `diagnose`：校验一份增长诊断是否可执行——北极星指标（northstar）一主一辅齐备、
  漏斗五阶段在枚举内、PMF 信号在枚举内。
- `unit`：校验单位经济是否健康——LTV、CAC、回收期三个数字实算，LTV:CAC≥3.0、
  回收期≤18 个月才健康。

边界：本角色只做可复算的单位经济与基线口径，不做统计显著性（交 R06 蛙深远）；
北极星只要求一主一辅可陈述，不替读者拍经营决策。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`diagnose.northstar_required`（primary/secondary）、`diagnose.funnel_stages`
（获客/激活/留存/推荐/营收）、`diagnose.pmf_signals`（留存率/复购率/净推荐值/自然增长占比）。

**算术实算**：
- `LTV = ARPA × gross_margin / churn_rate`（`safe_div` 除零返回 0）。
- `CAC = spend / new_customers`。
- `回收期 = CAC / (ARPA × gross_margin)`，单位月。
- `LTV:CAC = LTV / CAC`，健康阈值 `ltv_cac_healthy=3.0`。

**diagnose 校验规则**：
- `northstar.primary/secondary` 任一为空 → BLOCKER。
- `funnel` 非列表或为空 → BLOCKER；任一阶段不在 `funnel_stages` → BLOCKER。
- `pmf_signals` 非列表或为空 → BLOCKER；任一信号不在 `pmf_signals` → BLOCKER。

**unit 校验规则**：
- `arpa/gross_margin/churn_rate/spend/new_customers` 任一缺或非数字 → BLOCKER。
- `churn_rate≤0` → BLOCKER；`new_customers≤0` → BLOCKER。
- `LTV:CAC<3.0` → BLOCKER；回收期>18 月 → BLOCKER。

**输出键**：diagnose → `funnel_count/signal_count`；unit → `ltv/cac/payback_months/ltv_cac`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/diagnose.json`：北极星=付费用户数/自然增长占比、五阶段闭环、四类 PMF 信号 → ok=true。
- `examples/unit.json`：ARPA=100、GM=0.8、churn=0.05、spend=30000、new=200 →
  LTV=1600、CAC=150、LTV:CAC=10.7、回收期≈1.9 月 → ok=true。
- 脏夹具 `diagnose_dirty.json`：北极星只写主指标 + 漏斗/PMF 越界 → ok=false / exit 1。
- 脏夹具 `unit_dirty.json`：new_customers=0（CAC 除零）→ ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **除零要 safe_div**：new_customers=0 或 churn=0 时 LTV/CAC 会除零崩溃，必须用
  `safe_div` 返回 0 并让后续健康判断自然 FAIL，而不是抛异常。
- **枚举要外置**：漏斗阶段、PMF 信号会被业务反复调整（比如加「转介绍」），硬编码
  在技能里就要改代码；外置到 thresholds 后只改 JSON。
- **诊断与显著性分开**：诊断只判断「指标全不全、口径对不对」，不判断「差异是否显著」，
  后者交 R06，避免本角色越权下统计结论。
