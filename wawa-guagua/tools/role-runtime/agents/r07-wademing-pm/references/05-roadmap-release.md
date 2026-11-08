# 模块E · 路线图与发布（S05）
> 蒸馏自: 补充技能/product-manager/SKILL.md 及相关 workflow
>


## 一、方法论

什么时候用：要把 backlog 排进时间线、并对外发布「这次改了什么」时。路线图的正确单位
是**结果（outcome）**而非功能（feature）——「让试用户 10 分钟建好首项目」比「做引导」
更可验证。发布说明要按固定分类，事前尸检要在发布前就想象失败。

- **成果路线图句式**：`Enable [分群] to [期望结果] so that [业务影响]`，用「So what?」
  一路追问到业务影响。
- **发布说明五分类**：New Features / Improvements / Bug Fixes / Breaking Changes /
  Deprecations，每类条目格式固定。
- **事前尸检（Pre-Mortem）**：假设 14 天后已发布，倒推会怎么失败；风险分三类。

## 二、可执行口径（与 skills/s05_roadmap.py 逐字对齐）

阈值一律以 `experience/thresholds.json` 为准，键名如下：

| 校验 | 读 thresholds.json 键 | 判读 |
|---|---|---|
| 发布分类 | `roadmap.release_categories`（5 类枚举） | 五类齐全且非空才 ok |
| 路线图 items | 无阈值（固定） | items 非空；dict 项须 segment/outcome/business_impact 俱全 |
| 事前尸检 tigers | 无阈值 | ≥1 个 Tiger（真实风险） |
| 行动表字段 | 无阈值 | risk/mitigation/owner/due_date 俱全 |
| Fast-Follow 时限 | 代码内固定 30 天 | days > 30 → BLOCKER |

输出键（contracts.py `roadmap` 契约）：`ok`、`checks` + 动作专属：
- `roadmap` → `item_count`
- `releasenotes` → `categories`
- `premortem` → `tiger_count`、`action_count`

## 三、已验证算例（只写 run_tests.py 真实跑过的数字）

| 算例 | 输入 | 结果 |
|---|---|---|
| roadmap | 1 项（segment/outcome/business_impact） | ok=true |
| roadmap 空 | `{}` | ok=false，item_count=0 |
| releasenotes 五分类 | 5 类各含条目 | ok=true |
| premortem | 1 tiger + 1 行动表 | ok=true |

## 四、实战踩坑

1. **早退路径要保契约字段**：`_roadmap` 在 items 为空时早退，最初只返回
   `{ok:false, checks}`，漏了 `item_count`——verify_loop 的「脏行输出契约校验」当场抓出
   「输出缺必填字段」。（已修：早退补 `item_count=0`。）这印证 SOP「smoke ≠ 闭环」：
   脏数据路径的输出结构也必须合规，否则下游消费方拿到残缺 JSON。
2. **路线图 dict 项和 str 项都认**：str 项走 `Enable…so that` 正则，dict 项走
   segment/outcome/business_impact 三字段，两种形态别混在一个 items 里。
3. **发布说明五类是封闭枚举**：分类名写中文或缩写会被判缺类，必须用 thresholds 里的
   5 个英文枚举。
4. **Fast-Follow 阈值 30 天是硬编码在代码里**，不在 thresholds.json——若业务口径要改，
   应把它提到 thresholds（当前是遗留，见 SOP 第十二节「阈值单一真源」的整改方向）。
