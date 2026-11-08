# S07 人工评审收尾（package / ingest / ack）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/design/design-handoff/SKILL.md
>


## 方法论（来源 petergyang / human-review）

确定性检查到头后，剩余的不确定性交人工。四段闭环：

1. **package**：把成品 + 评审维度 + 判据 + 截止时间打包给人工评审人；
2. 人看（R04 不替代人看）；
3. **ingest**：人工批次反馈回灌，校验契约 + 逐字回填；
4. **ack**：归档确认，staged 资产全部复制到位才算闭环。

## 可执行口径

- package 必填字段外置在 `human.package_required_fields`
  （artifact / review_dimensions / criteria_ref / producer / reviewer / deadline）；
  - **身份红线：reviewer == producer 即 FAIL**——自评不算评审，
  不看字段齐不齐，先看身份。
- ingest 批次契约（全部枚举外置）：
  - comment.kind ∈ `human.comment_kinds`（selection / element）；
  - edit.kind ∈ `human.edit_kinds`（edited / deleted / moved）；
  - anchor 结构 {prefix, quote, suffix}：quote 是定位文本；
  - **edited.after 必须逐字保留原文**（after=改后全文本，回填时
    applied_plan 的 action=apply_verbatim 逐字替换 anchor 命中处）；
  - **deleted**：整块删除，没有 after 可对，不问原因直接标记；
  - **moved**：用 moved_after / moved_before 二选一定位去向；
  - edits_saved=true 才触发 re_read_files（改完必须重读复核）。
- ack：staged_assets 列表**每一项 copied:true** 才放行，
  任何一项未复制 → BLOCKED。

## 已验证算例

- `cases/landing-acceptance/` 第 3 步：producer=r08 / reviewer=r04，
  身份红线通过（self_review_blocked=false），package_valid=true；
- `examples/human_package_dirty.json`：reviewer==producer → 身份红线 FAIL；
- `examples/human_ingest.json` / `human_ingest_dirty.json`：
  契约齐全回灌成功 vs kind 非法 / after 不逐字被拦；
- `examples/human_ack.json` / `human_ack_dirty.json`：
  staged 全 copied 放行 vs 有未复制项 BLOCKED。

## 实战踩坑

- 「逐字」是真的逐字：after 与磁盘文本差一个空白都算违约
  ——校验按字符串相等，不做 normalize（一旦 normalize 就会吞掉
  「改错了空白」这类真问题）；
- deleted 与 edited 是两种契约：deleted 没有 after，别用 edited 的
  校验逻辑去要求它；
- ack 检查的是**复制完成度**，不是内容好坏——内容评审在前三步已完成，
  归档时只剩「东西到位没有」一个维度。
