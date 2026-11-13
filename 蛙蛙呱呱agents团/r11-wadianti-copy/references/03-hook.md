# s03 钩子、提纲与立场（hook / outline）方法论
> 蒸馏自: TBD: 待关联补充技能源文件
>


来源沉淀：`bzwh321__article-director-public`（topic-architect 的「答案先行」「读者卡点」
纪律：先给结论、站在读者角度卡痛点）。

## 一、方法论（什么时候用、核心口径）

钩子决定打开率，提纲决定可信度，立场决定边界。本角色把「标题党 vs 可信钩子」
的区别做成确定性规则：
- `hook`：校验钩子与标题——hook_type 在白名单（数字/反常识/问题/场景/对比/悬念），
  标题备选至少 3 选 1。
- `outline`：校验提纲与立场——二级标题（##）至少 3 个；立场三件套
  claim/audience/boundary 齐备，且 boundary 必须写清「不替读者拍板」。

边界：**不替读者拍板**是本角色的核心红线。立场里的 boundary 必须显式声明
「不替/不代表/仅供参考/需自行」，否则提纲再完整也 FAIL——内容角色可以给方法，
不能替读者做经营或消费决策。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

阈值外置：`hook.hook_types`（6 类）、`hook.title_min`（3）、`hook.outline_h2_min`（3）、
`hook.stance_required`（claim/audience/boundary）。

**hook 校验规则**：
- `hook_type` 不在 6 类白名单 → BLOCKER（短路，title_count=0）。
- `titles` 非列表、含空串、或数量 < `title_min` → BLOCKER。

**outline 校验规则**：
- `outline` 文本内 `^## ` 计数 < `outline_h2_min` → BLOCKER。
- `stance` 非对象 → BLOCKER。
- claim/audience/boundary 任一空 → BLOCKER。
- boundary 不含「不替/不代表/仅供参考/需自行」任一 → BLOCKER。

**输出键**：hook → `hook_type/title_count`；outline → `h2_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/hook.json`：hook_type=数字、3 个标题备选 → ok=true、title_count=3。
- `examples/outline.json`：4 个二级标题 + boundary=「不替读者拍板经营决策，需自行判断」
  → ok=true、h2_count=4。
- 脏夹具 `hook_dirty.json`：hook_type=玄学（不在白名单）→ ok=false / exit 1。
- 脏夹具 `outline_dirty.json`：1 个标题 + boundary=「听我的就行」（未声明不拍板）
  → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **boundary 是语义检查不是关键词堆砌**：只判「不替读者拍板」四个词，边界写
  「请读者自行判断」也过（含「需自行」），但写「听我的就行」必拦——把软约束
  落成可测的关键词白名单。
- **hook_type 短路与 brief 一致**：类型非法直接返回，别继续数标题，否则脏数据
  在标题数量上「碰巧」显得正常。
- **二级标题用行首锚定**：`re.MULTILINE` 的 `^## ` 才认标题，正文里出现的
  `##` 符号（比如代码块）不会误计。
