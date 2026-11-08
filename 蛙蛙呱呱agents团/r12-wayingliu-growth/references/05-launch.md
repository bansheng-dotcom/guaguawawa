# s05 ASO 与发布（aso / ph）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/marketing/seo-audit/SKILL.md
>


来源沉淀：`coreyhaines31__marketingskills`（aso 的应用商店优化、launch 的发布清单）+
`retieedra-profound__skills-marketing-library`（PH 发布 playbook，去重后不重复计数）。

## 一、方法论（什么时候用、核心口径）

ASO 与发布是产品上线的临门一脚。本角色的立场：**发布不能拍脑袋，要能算分**。两个动作：
- `aso`：校验应用商店优化清单——store 在枚举内、标题/副标题字符上限、六维加权评分。
- `ph`：校验发布清单与上市节奏——tagline/maker_comment/first_comment/links 四要素齐备、
  上市节奏三阶段。

边界：本角色只校验发布清单与评分口径，不真提交应用商店；内容改写归 R11，
本角色只产出发布清单结构。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`launch.stores`（app_store/google_play）、`launch.title_max/subtitle_max`（30）、
`launch.weights`（title20/description15/visual25/rating20/metadata10/conversion10）、
`launch.grade_bands`（A85/B70/C50/D30）、`launch.ph_required`（四要素）、
`launch.launch_stages`（预热/发布日/后续跟进）。

**六维加权评分**：`score = Σ(dim_score × weight/100)`，各维 0-10 分，总分 0-10。
**等级**：`≥8.5→A、≥7.0→B、≥5.0→C、≥3.0→D、否则→F`。

**aso 校验规则**：
- `store` 不在 `stores` → BLOCKER（短路返回）。
- 标题长度不在 (0,30] → BLOCKER；副标题长度>30 → BLOCKER。
- `scores` 非对象或六维任一缺失 → BLOCKER；任一维不在 [0,10] → BLOCKER。

**ph 校验规则**：
- 四要素任一为空 → BLOCKER。
- `stages` 非列表或长度≠3 → BLOCKER；任一阶段不在 `launch_stages` → BLOCKER。

**输出键**：aso → `store/score/grade`；ph → `stage_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/aso.json`：store=app_store、标题 8 字、六维 9/8/8/9/8/9 → score≈8.5、grade=A → ok=true。
- `examples/ph.json`：四要素齐备 + 三阶段齐备 → ok=true、stage_count=3。
- 脏夹具 `aso_dirty.json`：store=steam（不在枚举）+ 标题/副标题超长 + title 维度 15 分（>10）
  → ok=false / exit 1。
- 脏夹具 `ph_dirty.json`：maker_comment/first_comment/links 空 + 阶段越界 → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **store 枚举要短路**：store 非法时直接返回，别继续算分，否则会白算一通。
- **评分维度要卡区间**：title 维度写 15 分（满分 10）必须拦，否则加权分会被拉爆，
  所以每个维度都要判 `0<=x<=10`。
- **等级用 grade_bands 外置**：等级线会随行业调整，外置到 thresholds 后改 A/B/C/D 线
  不用改代码。
