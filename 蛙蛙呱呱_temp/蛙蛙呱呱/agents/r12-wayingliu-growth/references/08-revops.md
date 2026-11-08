# s08 归因与 RevOps（attribution / roi）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/forecast/SKILL.md
>


来源沉淀：`coreyhaines31__marketingskills`（attribution 的归因模型、revops 的 ROI 复盘）+
`retieedra-profound__skills-marketing-library`（归因口径，去重后不重复计数）。

## 一、方法论（什么时候用、核心口径）

归因是增长的度量衡，RevOps 是增长的钱袋子。本角色的立场：**归因不能靠拍脑袋，要能
选模型；ROI 不能靠报表，要能复算**。两个动作：
- `attribution`：校验归因方案——模型在枚举内、去重口径声明单一真源、埋点字段在白名单。
- `roi`：校验 ROI 复盘——CAC/LTV/回收期/ROI 四数字实算、LTV:CAC≥3.0、ROI≥0。

边界：本角色只校验归因口径与 ROI 复盘，不真采集埋点数据（数据口径交 R06）；
归因不跨平台求和，这是本角色的硬口径。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`revops.attribution_models`（first_touch/last_touch/last_non_direct/linear/
time_decay/position_based/data_driven）、`revops.tracking_fields`（event_name/utm_source/
utm_medium/utm_campaign/user_id/timestamp）、`revops.ltv_cac_healthy`（3.0）、
`revops.payback_months_max`（18）。

**算术实算**：
- `LTV = ARPA × gross_margin / churn_rate`。
- `CAC = spend / new_customers`。
- `回收期 = CAC / (ARPA × gross_margin)`。
- `ROI = (LTV - CAC) / CAC`。

**attribution 校验规则**：
- `model` 不在 `attribution_models` → BLOCKER（短路返回）。
- `dedup_source` 为空 → BLOCKER（必须声明单一真源，不跨平台求和）。
- `tracking_fields` 非列表或为空 → BLOCKER；任一字段不在 `tracking_fields` → BLOCKER。

**roi 校验规则**：
- 五数字字段缺或非数字 → BLOCKER。
- `churn_rate≤0` → BLOCKER；`new_customers≤0` → BLOCKER。
- `LTV:CAC<3.0` → BLOCKER；`ROI<0` → BLOCKER。

**输出键**：attribution → `model/field_count`；roi → `ltv/cac/payback_months/roi/ltv_cac`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/attribution.json`：model=last_non_direct + 单一真源 + 6 字段 → ok=true。
- `examples/roi.json`：ARPA=100、GM=0.8、churn=0.05、spend=30000、new=200 →
  LTV=1600、CAC=150、ROI=9.7、LTV:CAC=10.7 → ok=true。
- 脏夹具 `attribution_dirty.json`：model=gut_feeling（不在枚举）+ 无去重口径 → ok=false / exit 1。
- 脏夹具 `roi_dirty.json`：churn=0.5 → LTV=160、CAC=300、LTV:CAC=0.53（<3.0）、ROI<0
  → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **归因模型要短路**：model 非法时直接返回，别继续判埋点字段，否则白判。
- **不跨平台求和是硬口径**：dedup_source 必须声明单一真源，否则多平台数据直接相加
  会把同一个用户重复计多次，归因结论全错。
- **ROI 与 LTV:CAC 都要算**：ROI≥0 只保证不亏，LTV:CAC≥3.0 才保证健康，两者都要拦。
