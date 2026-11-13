# S03 外置验收判据（review / delta）
> 蒸馏自: 补充技能/01-当前能力域/petergyang__human-review/acceptance-criteria/SKILL.md
>


## 方法论（来源 human-review：判据外置）

判据不写在评审者脑子里，而是外置成可执行条目（id / statement / evidence /
expected）。评审就是拿成品逐条对拍，输出三态判定，绝不给「整体感觉不错」
这类模糊结论。多轮评审之间用 delta 说清楚：修好了几条、新增几条、还剩几条。

## 可执行口径

- review 三态：`criteria.statuses`（pass / warn / fail）；
  - **PASS 仅当 0 fail**（warn 不阻断但要写清楚为什么容忍）；
  - 证据须「具体」才算数：满足 `criteria.evidence_line_re`（形如 file:line）
    或 `criteria.evidence_field_re`（形如 field.subfield）——
    只写「已检查」「没问题」的 evidence 等于没有证据；
  - 没给证据的 fail 判据，理由记 no_evidence。
- delta：两轮结果按判据 id 建 prev_by_id / cur_by_id 对照——
  - **fixed**：上轮 fail/warn、本轮 pass；
  - **new**：上轮没有（或 pass）、本轮 fail；
  - **remaining**：两轮都 fail/warn。

## 已验证算例

- `cases/landing-acceptance/` 第 1 步：4 条判据 → 2 pass / 1 warn / 1 fail，
  verdict=FAIL，ac-04 的理由是 no_evidence（判据说改了但没有 file:line 证据）；
- `examples/criteria_review.json` 干净全 pass；`criteria_review_dirty.json`
  含 no_evidence 项被拦；
- `examples/criteria_delta.json` + `criteria_delta_state.json`：
  fixed=1 / new=0 / remaining 对拍通过。

## 实战踩坑

- 证据特异性判定别写成「非空即真」：一行「verified manually」是空话，
  必须同时过 `criteria.evidence_line_re` 或 `criteria.evidence_field_re` 才算；
- 技能模块里曾把 delta 子命令注册了两次（循环注册 + 手动注册各一次）——
  子命令注册要么全循环、要么全显式，混用必撞车；
- delta 按 **id** 对照而不是按顺序对照——两轮之间判据顺序可能重排。
