# 项目规则（PROJECT-RULES.md）

> 2026-11-18 沉淀。来源：《交付/复盘-返工根因与项目规则-2026-11-18.md》。
> 每条规则都对应一次真实事故，并绑定一个可执行检查（`scripts/check_convergence.py`）。
> **规则不是愿望清单**：没有检查的规则视为没写。

---

## 一、报告与内容

### R1. 一条产线一个出口
出 HTML/MD/PDF 报告只能走 `core/report_flow` → `core/report_bridge` → `core/report_renderer`。
角色目录只允许产出 `result.json` / `evidence.json` / `claims.json`，不得自带 `report.py` / `generate_html_report*.py` / 成品 `.html`。

- 事故：R03 曾自带 `report.py`，R06 曾有 3 份 `generate_*report*.py`，形成第二作者。
- 检查：`S5 孤儿接线` + 角色目录约定（`tests/regression/test_role_invariants.py`）。
- 违反：删除该出口，或把能力上收到 `core/`。

### R2. 单一事实来源，其余只能是生成物
同一类事实只允许一个「手写源」，其余文件必须由脚本生成并带 `--check`：

| 事实 | 唯一源 | 生成物 |
|---|---|---|
| 角色身份 / 是否进报告 | `core/registry.py::ROLES` | `roster` / `experts.yaml` / `agent-packs` |
| 图型集合 | `core/charts/v2/RENDERERS` | `chart_capabilities` / 选型配置 |
| 门禁阈值 | `report_quality.PROFILES`（或 policy） | 文档里的表格 |

- 事故：`enters_report` 在 `core/roster.py:80` 与 `scripts/gen_experts.py:209` 各硬编码一份；`experts.yaml` 现在仍列着已删除的 `size/demand/consistency/coverage/channel`。
- 检查：`S1 单一事实来源`（漂移 / 两套口径 / 硬编码）。
- 违反：改源，重跑生成器；禁止手改生成物。

### R3. 失败即失败，降级必须显性
「答不了 / 缺数据 / 引擎拒绝 / 技能失败」不得被转换成成功路径。允许降级，但必须同时满足：
1. 写进 `manifest.degraded`（原因 + 受影响的问题/节）；
2. `ok` 不得为 `true`，或该结论不得进头条；
3. 有一条「降级后仍可读」的显式文案。

- 事故：`decision_report.py:77-82` 在专家答不了时静默回退 `decision.draft`，实测「小红书内容营销增长」出了水果报告且 `ok=true`；`analysis_methods.py:199` 把「没返回 ok」当成功；`orchestrator.py:209` 把「没有方法」当 `readiness=1.0`；`report_cli.py:310-312` 把未知子命令当 intent（`report decide` 至今能跑）。
- 检查：`S2 失败即失败` 五条。
- 违反：删掉 fallback，或补 `degraded` 并 block。

### R4. 新增之前先搜：同一概念第二次出现即缺陷
新增表 / 配置 / 名册 / 词汇表前，先 `grep` 现有实现；如果同一概念已有定义，只能接线或合并，不能新建第二份。

- 事故：图表选型曾有 6 套词汇表（48 型注册表 / `chart_by_relation.yaml` / `chart_type_by_question.json` / `CHART_POLICY` / 方法内 type / 渲染器分发）；问题来源曾有 4 套（QBANK / question_library / derive / roster）。
- 检查：`S1`、`S5`。
- 违反：先写一页「为什么不能复用」再动手；否则不予合并。

### R5. 删除是完成定义的一部分
新路径上线的那次提交，必须同时删除旧路径；旧文件先 `git mv` 到 `_attic/` 并在 `_attic/DELETED.md` 记一行（谁、何时、为什么、替代物）。

- 事故：v11 说删了 `build/decide`，`report_cli.cmd_plan` 仍暴露 `--thesis`；`report_flow` docstring 仍写 A/B 分支；`analysis_methods` 仍承诺 `report_compose`。v12.3 才把被 P1–P5 切断的 48 型图表接回。
- 检查：`S4 文档可执行` + `S5`。
- 违反：同一次提交补齐删除，否则视为未完成。

### R6. 每个数字、每张图、每条降级都能追到 id
报告正文的每个数字必须能追到 `evidence_pack.numbers[].id` 或 `derived.formula`；每张图必须带 `source / unit_meta / claim_to_prove`；每条降级必须带原因。

- 事故：表格单位串列（`report.md` 的「变化率（零售价，元/斤）」「期数（元/斤）」）；图回退 v1 时不写 manifest。
- 检查：`report_flow.check_sections` + `quality_gate` + 新增图表断言（见 R10）。
- 违反：报告不落盘。

---

## 二、验证与提交

### R7. 每个 P0 bug 必须有一条「会失败」的测试
修 bug 的提交必须附一条反例测试：在修复前会红、修复后绿。只测 happy path 不算。

- 事故：233 个测试全绿，但「意图不匹配 → 降级出报告」没有任何测试；`tests/test_report_model.py` 曾把「死配置」写成断言。
- 检查：`S2` + 新增 `tests/test_intent_binding.py`（建议：招聘 / 内容营销 / 空数据 / 脏数据四例）。
- 违反：PR 不予合并。

### R8. 一次变更一个提交，提交前工作区干净
- 不允许「同一标题连提两次」（实测有 8 秒 / 8 秒 / 24 秒三对）。
- 不允许把已跟踪文件从磁盘删掉却不提交（实测 1,073 个）。
- 提交前：`python scripts/check_convergence.py` 不新增违规 + `git status` 只剩预期文件。

- 检查：`S3 工作区纪律`。
- 违反：先 `git stash`/分支隔离，再改。

### R9. 删除交付物前先归档
任何交付物 / 历史项目 / 报告体系目录删除前，`git mv` 到 `_archive/YYYY-MM-DD/`，并在 `manifest.json` 记来源与哈希。禁止 `rm -rf`。

- 事故：`报告体系/`（156 文件）、`内蒙古水果调研_2026-11-12/`（460 文件）等 1,073 个已跟踪文件从磁盘消失且未提交，干净克隆里已不可见。
- 检查：`S3`。
- 违反：从 HEAD 恢复后按归档流程重做。

### R10. 文档只做索引，命令必须可执行
README / AGENTS / REPORT-* 不重复正文，只放链接；文档里出现的每条命令，必须能在当前 HEAD 执行成功（或行尾明确标「已下线」）。

- 事故：`README.md:41` 教 `report produce`（已删）；`使用指南.md:356/360` 教 `report decide`（已删）；`REPORT-STANDARD.md` 同文件第 5 行说删了、第 64/79 行又教。
- 检查：`S4 文档可执行`。
- 违反：改文档或加「已下线」标记。

### R11. 一次性脚本与生成物不进主仓
- 仓根禁止 `_*.py` 探针（现有 25 个）；一次性脚本进 `scripts/_oneoff/`，带 `--dry-run` 与幂等说明。
- `pipelines/out/`、`projects/`、`evals/results/`、`__pycache__/`、`z/` 不入库。
- 全仓改写类脚本（如 `convert_encoding.py`）必须：先备份、先 `--dry-run`、只处理指定目录、输出变更清单。

- 事故：`convert_encoding.py` 以 GBK 优先遍历全仓 `.py/.md`，无备份、无 dry-run；UTF-8 中文被 GBK 成功解码时会写成乱码。
- 检查：`S3`。
- 违反：移出主仓。

### R12. 图表只留一个运行时引擎，另一个只能是显式对照
默认 `v2`；`v1` 只允许 `engine="v1"` 显式调用（对照/快照），不得作为静默兜底。任何回退必须：写 `chart_stats`、进门禁（`v2==total and fallback==0 and error==0`）、图上显示「数据不足」占位。

- 事故：v2 把所有异常吞成 `None`（`core/charts/v2/__init__.py:407-410`），`error` 计数几乎不动；v1 接不住 v2 的 payload（实测 gantt / ridgeline / small_mult 直接抛异常），回退等于把报告打死或画素图。
- 检查：`scripts/check_chart_fallback.py` + 新增「报告级 chart_stats 断言」。
- 违反：图不落盘，或标注「降级图」。

---

## 三、复盘本身

### R13. 复盘只加「当前事实页」，不新增第 N 份诊断
每次复盘更新同一页（本目录的 `复盘-返工根因与项目规则-YYYY-MM-DD.md` 只保留最新一版 + 历史归档），不并列 5 份互相矛盾的诊断。

- 事故：11-18 一天内出现《实际结构与问题》《根因与修复》《重构 SOP》《P1–P5 验收》四套口径，读者无法判断哪份是现行。
- 检查：人工（文档索引 `docs/README.md`）。
- 违反：合并进现行页，旧稿进 `_attic/docs/`。

---

## 附：检查器与接入

```bash
python scripts/check_convergence.py                 # 14 项，当前 12 项违规
python scripts/check_convergence.py --json out.json
python scripts/check_convergence.py --baseline .convergence-baseline.json   # 只许下降
```

建议接入顺序：
1. 先 `--write-baseline` 冻结当前 12 项（不阻塞今天的工作）；
2. 每次修完一条，基线减一；
3. 基线归零后去掉 `--baseline`，改为硬门禁。
