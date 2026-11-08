# s03 落地页与 H5（landing / form）方法论
> 蒸馏自: 补充技能/01-当前能力域/duncan-buildroom__freeskills/first-website/SKILL.md
>


来源沉淀：`makerskills`（landing-page / form）。

## 一、方法论（什么时候用、核心口径）

「把价值主张做成单文件可交付、可收集线索的落地页」。两个动作：
- `landing`：校验落地页八要素齐备（goal/headline/subhead/proof_points/form/button/
  faq/post_submit），佐证点 ≥3，并锁定五条技术约束。
- `form`：校验表单——提交端点（formspree_endpoint 或 mailto 至少其一）+ 每个字段带
  name/label。

核心红线（R08 实现型身份）：**单文件可交付 + 无 JS 库依赖 + 移动优先**。这五条技术约束
不是「风格偏好」而是「交付形态契约」：任何一条 False 都会让落地页脱离「一人公司能自己
上线」的范围，滑向需要构建链的生产工程（R09/R20 的边界）。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

八要素键名、佐证下限、五条技术约束全部外置：`landing.keys`、`landing.proof_min`、
`landing.tech_constraints`（验证链：`experience/thresholds.json → _common.load_thresholds()
→ s03_landing._validate_landing/_validate_form`）。

**landing 校验规则**：
- 八要素任一缺失或为空 → `landing.{k}` BLOCKER；proof_points 特殊：须为非空数组。
- `proof_points` 条数 < 3 → `landing.proof` BLOCKER。
- 五条技术约束（single_file_index_html / no_js_library / form_deliverable /
  mobile_first / button_single_accent）任一缺失或非 True → `landing.{tc}` BLOCKER。
- `max_objection` 为空 → `landing.max_objection` BLOCKER（最大异议必须显式写出）。

**form 校验规则**：
- `formspree_endpoint` 与 `mailto` 双空 → `form.target` BLOCKER（线索没有去处）。
- `fields` 每项缺 name / label → `form.field.{k}` BLOCKER。

**输出键**：landing → `proof_count / verdict / next`；form → `field_count / verdict / next`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/landing.json`：八要素齐、proof_points 3 条、五约束全 True、
  max_objection 非空 → ok=true、proof_count=3、verdict=PASS。
- `examples/form.json`：formspree 端点 + email 字段 → ok=true、field_count=1、verdict=PASS。
- 脏夹具 `landing_dirty.json`：proof_points 仅 1 条 → ok=false / exit 1。
- 脏夹具 `form_dirty.json`：fields=[] → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **技术约束必须是 `is True` 而非 truthy**：有人写 `"true"`（字符串）或 `1`，
  truthy 判定会放行；必须 `v is True` 严格布尔，contracts 输入 schema 同步用 `_BOOL`。
- **proof_points 与八要素的判定分支不同**：八要素里其他键看「非空串」，proof_points
  要看「数组且 ≥1」再单独查「≥3」。漏掉第一层会让 `proof_points: 5`（数字）绕过类型检查
  后被第二层 len() 崩掉。
- **max_objection 是转化率杠杆不是装饰**：写不出「最大异议」说明还没想清用户为什么不买；
  它缺失时必须拦，这是本技能最容易被跳过的字段。
- **form 端点二选一是 OR 语义**：mailto 允许低预算场景（无服务器收集），但两者都空
  等价于「表单永远交不出去」——BLOCKER，不是 WARN。
