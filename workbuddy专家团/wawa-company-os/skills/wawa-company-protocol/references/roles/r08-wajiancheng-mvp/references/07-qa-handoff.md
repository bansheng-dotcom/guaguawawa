# s07 质量验证与交接（qa / handoff）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/testing-strategy/SKILL.md
>


来源沉淀：`makerskills`（quality-gate / handoff）+ `product-manager`。

## 一、方法论（什么时候用、核心口径）

「把 MVP 快速跑过质量门禁并干净交接」。两个动作：
- `qa`：校验质量验证——五大必需检查（build/typecheck/screenshot/design_qa/a11y）
  状态合法、无障碍项 ≥3、测试点带预期。
- `handoff`：校验交接包——产出物 ≥2、可运行命令、验收标准、责任人齐备。

核心红线（R08 实现型身份）：**交接是责任移交，不是甩文档**。handoff 必须同时给出
「产出物 + 可运行命令 + 验收标准 + 责任人」四件套；生产级工程/CI-CD/可靠性演进
继续交 R09/R20——出现生产级词但无 handoff 声明由 T7 review 的 scope_boundary 拦下。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

必需检查项、合法状态、a11y 下限全部外置：`qa.required_checks`、`qa.status_types`、
`qa.a11y_min`（验证链：`experience/thresholds.json → _common.load_thresholds()
→ s07_qa._validate_qa/_validate_handoff`）。

**qa 校验规则**：
- `checks` 归一化（dict 或 list 皆可）后，五必需检查任一缺失 → `qa.{rc}` BLOCKER。
- 每项 `status` 不在 pass/fail/block → `qa.{rc}.status` BLOCKER。
- `a11y_items` 条数 < 3 → `qa.a11y` BLOCKER。
- `test_points` 为空 → `qa.test_points` BLOCKER；每项缺 name / expectation →
  `qa.test_point.{k}` BLOCKER。
- `check_count` = 归一化后的检查条数。

**handoff 校验规则**：
- `artifacts` 条数 < 2 → `handoff.artifacts` BLOCKER。
- `run_commands` 为空 → `handoff.run_commands` BLOCKER。
- `acceptance` 为空 → `handoff.acceptance` BLOCKER。
- `owner` 为空 → `handoff.owner` BLOCKER。

**输出键**：qa → `check_count / verdict / next`；handoff → `artifact_count / verdict / next`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/qa.json`：五检查全 pass、a11y 3 项、测试点 1 项 →
  ok=true、check_count=5、verdict=PASS。
- `examples/handoff.json`：2 产出物 + 1 命令 + 1 验收 + owner=r09 →
  ok=true、artifact_count=2、verdict=PASS。
- 脏夹具 `qa_dirty.json`：checks 仅 build 一项 → ok=false / exit 1。
- 脏夹具 `handoff_dirty.json`：artifacts 仅 1 个 → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **checks 的动态键 ≠ 固定键**：契约输入 schema 只能把 `checks` 声明为 object
  （键是 build/typecheck/…五检查名），逐项合法性由技能本体按 `required_checks` 判——
  契约管形状，技能管语义，两层不能混。
- **状态用归一化而非直接比对**：`status` 必须先 `.strip().lower()`；写 `"PASS"`
  的阳春产出若不归一会被误拦（r06 同款教训）。
- **a11y 三条是可用性底线**：对比度/语义标签/键盘可达缺一即残障用户不可用；
  少一条就是 BLOCKER，不能降级为 WARN。
- **handoff 的 owner 不能是「团队/大家」**：责任人必须可指认（如 r09）；
  空 owner 或模糊责任等于没有交接，门禁直接拦下。
