# s05 品牌语调与编辑（guide / edit）方法论
> 蒸馏自: TBD: 待关联补充技能源文件
>


来源沉淀：`bzwh321__article-director-public`（style-harmonizer 统一称谓/口吻/术语、
style-guide 品牌语调指南）。

## 一、方法论（什么时候用、核心口径）

品牌语调一旦漂移，读者会感到「不是同一个人写的」。本角色把「统一口径」转成
确定性校验：
- `guide`：校验品牌语调指南——audience/tone/terms/forbidden/grammar 五字段齐备，
  且 dimensions 六维（称呼/口吻/术语/禁词/语法/标点）至少覆盖 4 维。
- `edit`：校验清洁终稿——forbidden_hits 可追溯、term_fixes 每条约含 from/to、
  终稿文本不得再含残留禁词。

核心红线：**清洁声明与终稿必须一致**。编辑若声称「已去禁词」但文本仍含
「总而言之」等禁词，即 FAIL——编辑动作不能只声明不改文。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

阈值外置：`voice.dimensions`（6 维）、`voice.guide_required`（5 字段）、
`voice.edit_required`（text/forbidden_hits/term_fixes）。

**guide 校验规则**：
- `audience/tone/grammar` 任一空串 → BLOCKER。
- `terms/forbidden` 任一非列表或为空 → BLOCKER。
- `dimensions` 覆盖 `voice.dimensions` 的维度数 <4 → BLOCKER。

**edit 校验规则**：
- `text/forbidden_hits/term_fixes` 任一键缺失 → BLOCKER。
- `forbidden_hits` 非列表 → BLOCKER。
- 终稿 text 残留 `copy.forbidden_zh` 任一 → BLOCKER。
- `term_fixes` 非列表、或任一条目缺 from/to → BLOCKER。

**输出键**：guide → `dimension_count`；edit → `forbidden_count/fix_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/guide.json`：五字段齐备 + dimensions 覆盖 6 维 → ok=true、dimension_count=6。
- `examples/edit.json`：text 无残留禁词 + forbidden_hits=[赋能] + 2 条 from/to fix
  → ok=true、fix_count=2。
- 脏夹具 `guide_dirty.json`：terms=[] + dimensions 仅 1 维 → ok=false / exit 1。
- 脏夹具 `edit_dirty.json`：text 含「值得我们深思」残留禁词 + term_fixes 缺 to
  → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **terms/forbidden 是列表不是字符串**：指南里这两个字段天然是多值，判
  `isinstance(list) and len>0`，否则把空串当齐备漏判。
- **残留禁词复用 copy 口径**：edit 的禁词与 s04 copy 同源（都读 `copy.forbidden_zh`），
  避免两处口径漂移——改一处，全角色一致。
- **dimensions 是白名单覆盖**：判「6 维里覆盖了几个」而非「用户填了几个」，
  用户填 4 个不在白名单的维度不算数。
