# topic-architect first-agent contract v1

Date: 2026-06-29

## Decision

`topic-architect` is the authoritative first article agent for outline and detailed-outline planning.

`article-architect` remains a compatibility alias during migration. It must not be treated as a separate strategy layer or a second planning agent.

## Rationale

The first agent should solve writing-planning problems only:

- reader stuck points
- upstream/downstream knowledge order
- logic handoff between sections
- examples and prompt examples
- before/after demonstrations
- presentation mode
- writer-executable information

Strategy is no longer allowed to hard-code the outline structure. Strategy contracts act as pluggable pre-prompt packages only.

## Contract Changes

Each detailed-outline H2 section must include:

- `论点:`
- `读者卡点:`
- `上下游承接:`
- `逻辑难点:`
- `需要解释:`
- `需要引用:`
- `需要案例:`
- `提示词样例:`
- `规范化前后:`
- `展示方式:`
- `writer可执行信息:`
- `待研究:`

When a field is not applicable, write `无，原因：...` instead of deleting the field.

## Handoff Rule

The writer receives outline and detailed-outline outputs, then adds its own writer pre-prompt, author-soul writer contract, candidate generation, and expression-selection rules. The first agent must not pre-empt or replace the writer's own style and rewriting prompts.

## Files

- `agents/topic-architect/SKILL.md`
- `agents/topic-architect/resources/output-contract.md`
- `agents/article-architect/SKILL.md`
- `agents/article-architect/manifest.yaml`
- `agents/_index.yaml`
- `prompts.yaml`
- `references/strategies/knowledge-explainer.json`
- `workflows/topology.yaml`
- `scripts/init_workflow.py`
- `scripts/normalize_detailed_outline.py`
- `scripts/compiler_lib.py`
- `scripts/build_writer_context_window.py`
- `scripts/build_argument_spine.py`
- `scripts/validate_output.py`
- `scripts/compile_expanded_workflow.py`

## Validation

- `python -m py_compile` passed for modified workflow scripts.
- `git diff --check` passed for the touched files.
- `validate_output.py --schema detailed-outline` passes on a complete fixture.
- `validate_output.py --schema detailed-outline` fails when a section lacks `提示词样例:` and `规范化前后:`.
- `compiler_lib.parse_detailed_outline` preserves new fields and maps `展示方式: before/after 对照表` to `recommended_presentation=comparison-table`.
- A lean-v1 smoke initialization generated `topic-architect-01-plan -> topic-architect-01-exec -> normalize-detailed-outline-01`, with `topic-architect-01-exec` guarded by the `detailed-outline` schema.
- Expanded workflow smoke compilation produced a connected graph with no `agents/article-architect/SKILL.md` skill references; support script metadata now uses `agents/director/SKILL.md`.
- Runtime handoff smoke confirmed `argument-spine.md` and `writer-context-window.json` preserve `reader_stuck`, `upstream_downstream`, `prompt_example`, `before_after`, `presentation_hint`, and `writer_actionable`.

## Rollback

Rollback this version by restoring the previous `article-architect` route in `init_workflow.py`, removing `required_section_labels` from the detailed-outline schema, and reverting the new section fields in `compiler_lib.py`, `build_writer_context_window.py`, and `build_argument_spine.py`.
