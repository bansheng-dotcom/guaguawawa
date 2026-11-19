# scripts/_archive · 已停用脚本

> 2026-11-17 体检后的归档区。**这里的脚本不再被任何代码/CI 调用**，保留只为取证与历史。
> 不要直接运行：它们的路径推导按 `scripts/` 层级写死，移到子目录后 `ROOT` 会算错。

## 归档清单

| 脚本 | 原本用途 | 为什么归档 |
|---|---|---|
| `_intent_snapshot.py` | 意图路由快照 | 一次性迁移辅助，路由已由 `prompt_profile.json` 单一出处 |
| `_migrate_intents.py` | 意图数据迁移 | 迁移已完成 |
| `build_skill_map.py` | 生成技能映射 | 被 `core/skill_graph.py` + `skill_graph.json` 取代 |
| `calibrate_judge.py` | 评分器校准 | 校准已固化进 `evals/consulting/rubric.md` |
| `compile_vi.py` | VI 编译 | 设计令牌改由 `shared/design_systems.py` 产出 |
| `measure_prompt_size.py` | 测 Prompt 体积 | 一次性容量评估 |
| `probe_p3_gates.py` | P3 门禁探针 | 门禁已收敛到 `check_report_flow` / `check_skill_gate` |
| `seed_eval_tasks.py` | 造评测任务 | `evals/consulting/tasks.json` 已固化 |
| `seed_knowledge.py` | 灌知识库 | `knowledge/` 已固化 |
| `seed_role_ports.py` | 造端口数据 | `datasets/ports/` 已固化 |

## 还留在 scripts/ 的同类似脚本

体检时另有 22 个「代码无引用但文档里提到」的脚本（如 `make_package.py`、`gen_method_packs.py`、
`analyze_agent_skills.py`），**没有归档**：文档链接会断。要归档请先改文档，再一起移。
