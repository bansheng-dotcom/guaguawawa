# s06 付费投放与 CRO（media / cro）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/marketing/campaign-plan/SKILL.md
>


来源沉淀：`coreyhaines31__marketingskills`（ads 的付费投放、cro 的转化优化、ab-testing 的实验
设计）+ `retieedra-profound__skills-marketing-library`（投放 ROI 口径，去重后不重复计数）。

## 一、方法论（什么时候用、核心口径）

付费投放是用钱换增长，CRO 是用实验换转化。本角色的立场：**投放不能只追曝光，要能算
ROI；实验不能只看结果，要能过显著性**。两个动作：
- `media`：校验付费投放计划——渠道/受众/创意/预算四要素齐备、渠道在白名单、ROI 实算非负。
- `cro`：校验转化实验——hypothesis/metric/significance 三件套齐备、显著性≤0.05。

边界：本角色只校验投放计划与实验设计，不真投放、不代跑实验；显著性检验本身交 R06，
本角色只校验显著性门槛是否达标。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`paid.media_required`（channel/audience/creative/budget）、`paid.channels`
（搜索广告/信息流/社交广告/程序化/红人投放/邮件/联盟）、`paid.cro_required`
（hypothesis/metric/significance）、`paid.significance_min`（0.05）。

**ROI 实算**：`ROI = (return - spend) / spend`（`safe_div` 除零返回 0）。

**media 校验规则**：
- 四要素任一为空 → BLOCKER。
- `channel` 不在 `channels` → BLOCKER（短路返回）。
- `return/spend` 缺或非数字 → BLOCKER；`spend≤0` → BLOCKER；`ROI<0` → BLOCKER。

**cro 校验规则**：
- 三件套任一为空 → BLOCKER。
- `significance` 非数字或 >0.05 → BLOCKER。

**输出键**：media → `channel/roi`；cro → `significance`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/media.json`：channel=搜索广告、return=15000、spend=5000 → ROI=2.0 → ok=true。
- `examples/cro.json`：三件套齐备 + significance=0.05 → ok=true。
- 脏夹具 `media_dirty.json`：channel=电视广告（不在白名单）+ 四要素缺 → ok=false / exit 1。
- 脏夹具 `cro_dirty.json`：significance=0.5（>0.05）→ ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **ROI 要 safe_div**：spend=0 时除零崩溃，必须 safe_div 返回 0 并让 ROI<0 或后续判断
  自然 FAIL。
- **channel 枚举要短路**：channel 非法时直接返回，别继续算 ROI，否则白算。
- **显著性门槛外置**：0.05 是默认，业务可能要求 0.01，外置到 thresholds 后只改 JSON。
- **spend 必须为正**：spend=0 或负数是脏数据，ROI 无从谈起，先拦。
