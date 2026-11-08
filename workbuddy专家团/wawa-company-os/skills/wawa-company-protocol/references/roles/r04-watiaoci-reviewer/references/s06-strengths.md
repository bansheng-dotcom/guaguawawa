# S06 优点标记与复检（mark / recheck）
> 蒸馏自: 补充技能/01-当前能力域/petergyang__human-review/positive-feedback/SKILL.md
>


## 方法论（来源 harness-engineering / strengths）

评审不止挑错。但记下的优点必须**可辩护**：

- **mark**：把值得保留的决策/结构记入 keep_list，
  每项必须回答 why_keep（为什么留）+ evidence（凭什么说好）——
  没有 why 的 keep 只是人情；
- **recheck**：复检防三种失真——
  1. 优点被**无声降级**（keep 项被改差却不说理由）；
  2. 新 FAIL **不落 change 区**（修坏了哪里说不清）；
  3. **resolved 重报**（已解决的问题再报一遍凑数）。

## 可执行口径

- mark：keep 每项必填字段外置在 `strengths.keep_required_fields`
  （id / what / why_keep / evidence），缺一即 FAIL；
- recheck 三查（前轮 keep 列表 vs 本轮 critique/findings）：
  - keep 项降级且无 resolution_reason → error（downgrades 计数）；
  - 本轮新 FAIL 且 changed_ref 里定位不到 → error（untraceable 计数）；
  - 上一轮已 resolved 的问题再报 → error（不许重报）；
  - 0 error / 0 downgrades / 0 untraceable → PASS。

## 已验证算例

- `cases/landing-acceptance/` 第 6 步：修复后复评，
  keep 项无降级、新增 0 fail → recheck PASS
  （对照 landing-prev-critique 与 landing-recheck-new 两个轮次）；
- `examples/strengths_mark_dirty.json`：缺 why_keep 的 keep 项被拦；
- `examples/strengths_recheck_dirty.json`：降级无理由 → FAIL；
- `examples/strengths_recheck_new_dirty.json`：新 FAIL 无 changed_ref → FAIL。

## 实战踩坑

- recheck 是**跨轮对照**，输入必须带上一轮与本轮两份数据，
  只给本轮等于没对照；
- 「resolved 不重报」与「remaining 要重报」不冲突：
  没修好的继续报是 delta 的 remaining，修好的再报是凑数——
  判定键是上一轮的结论，不是这一轮的心情。

## 补充算例（run_tests.py T08 精确值，已对拍）

- **mark 干净件**：`strengths_mark.json` → `verdict=PASS`、`invalid=[]`。
- **mark 脏件**：`strengths_mark_dirty.json` → `verdict=FAIL`、
  `invalid[0]={id:K1, missing_fields:[why_keep]}`（keep 项缺 why_keep 即拦）。
- **mark 空表**：`{"keep_list": []}` → `ok=false`（没有优点记录也算不合格）。
- **recheck 干净件**：前轮 `strengths_recheck.json` + 本轮
  `strengths_recheck_new.json` → `recheck_verdict=PASS`，
  `downgrades=[]` / `untraceable_new_fails=[]` / `resurfaced_resolved=[]` 三者全空。
- **recheck 脏件**：`strengths_recheck_dirty.json` +
  `strengths_recheck_new_dirty.json` → `recheck_verdict=FAIL`，
  `downgrades=[{keep_id:K1, documented:false}]`（降级无理由）、
  `untraceable_new_fails=[NF1,NF3]`（新 FAIL 定位不到 change 区）、
  `resurfaced_resolved=[PF1]`（已 resolved 问题重报凑数）。
- **resolved 不重报**：前轮 PF1 已 resolved、本轮不再报 → `PASS`，
  `resurfaced_resolved=[]`（判定键是上一轮结论，不是本轮是否又出现）。

## 补充踩坑

- 三个计数器（downgrades / untraceable_new_fails / resurfaced_resolved）
  必须**同时为空**才 PASS——只查一个会让另两类失真漏网。
- keep 的 `evidence` 要能指到具体文件行（如 `a.md:1`），
  只写「设计合理」不指向证据的 keep 与人情无异。
- recheck 的 `--new` 是必填：不给本轮数据无法对照，
  早期漏传会误把「无对照」当 PASS。
