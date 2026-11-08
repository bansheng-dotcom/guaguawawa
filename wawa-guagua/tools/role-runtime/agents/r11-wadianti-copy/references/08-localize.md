# s08 持续本地化（term / review / probe）方法论
> 蒸馏自: TBD: 待关联补充技能源文件
>


来源沉淀：`WeblateOrg__weblate`（翻译协作/术语/审校/版本同步）。

## 一、方法论（什么时候用、核心口径）

本地化是重依赖能力——完整翻译执行要 weblate 服务。本角色只做「翻译项目管理」
的确定性校验 + **如实降级探测**，绝不假装会翻译：
- `term`：校验术语表——source/target 语言对在白名单，glossary 逐条含 source/target。
- `review`：校验审校记录——term/source_lang/target_lang/status/reviewer 齐备，
  status 在枚举内（pending/approved/rejected/needs-review）。
- `probe`：探测 weblate 客户端可用性——本机有 `weblate`/`wlc` 则 status=ready，
  否则 status=blocked，**恒 ok=true**（探测非门禁，如实降级）。

边界：真实翻译执行交 weblate 服务；本机无 weblate 客户端时，翻译能力降级为
「术语表 + 审校记录」管理，不硬编造译文。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

阈值外置：`localize.languages`（8 种语言）、`localize.terms_required`（3 字段）、
`localize.review_required`（5 字段）、`localize.status_enum`（4 态）。

**term 校验规则**：
- source/target 任一空 → BLOCKER；glossary 非列表或为空 → BLOCKER。
- source/target 不在 8 语言白名单 → BLOCKER。
- glossary 任一条目缺 source/target → BLOCKER。

**review 校验规则**：
- 五字段任一空 → BLOCKER。
- status 不在 4 态枚举 → BLOCKER。

**probe 规则**（探测非门禁）：
- `shutil.which("weblate")` 或 `which("wlc")` → ready，否则 blocked。
- 无论 ready/blocked 都 ok=true、verdict=PASS（如实降级，不 FAIL）。

**输出键**：term → `glossary_count`；review → `status`；probe → `status/languages`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/term.json`：zh-CN→en + glossary 3 条 → ok=true、glossary_count=3。
- `examples/review_localize.json`：status=approved、reviewer=r04 → ok=true。
- 脏夹具 `term_dirty.json`：target=xx-XX（不在白名单）+ glossary=[] → ok=false / exit 1。
- 脏夹具 `review_localize_dirty.json`：status=draft（不在枚举）→ ok=false / exit 1。
- `probe()`：本机无 weblate 时 status=blocked、ok=true、verdict=PASS。

## 四、实战踩坑（真拦下来的教训）

- **探测是降级不是失败**：probe 恒 ok=true，否则编排器会把「本机没装 weblate」
  当成任务失败；探测结果通过 status 字段传给上层做降级决策，而非 exit code。
- **语言对要两个都查**：source 和 target 都要在 languages 白名单内，只查 source
  会漏掉 target 非法（如 xx-XX 这种伪语言码）。
- **glossary 条目判 source/target 而非 source only**：术语表方向要明确，只判
  source 会让「有源无译」的残缺条目漏网。
