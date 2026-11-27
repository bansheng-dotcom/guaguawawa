# 2026-06-26 Section Editor Fan-out v1

## Goal

Replace the lean-v1 single section-editor prompt with a hardcoded review fan-out plus one consolidated rewrite pass.

## Changed

- `compile_expanded_workflow.py` now emits five advisory review nodes per section:
  - `review-ai-tone-{section_id}`
  - `review-style-{section_id}`
  - `review-logic-{section_id}`
  - `review-structure-{section_id}`
  - `review-simplify-{section_id}`
- `build_section_edit_brief.py` merges review outputs into `section-edit-brief.json`.
- `section-editor-{section_id}` now uses `section-rewriter` and still outputs the old `section-editor-result` JSON.
- `validate_section_rewrite_gate.py` checks brief consumption, AI-tone invocation, heading, and writer-contract removal before materialization.
- `materialize_section_editor_output.py` and downstream AI-tone audit/regression remain unchanged.
- `section-rewriter` must output `supervisor_judgment` before rewriting: it classifies the section heading as simple or complex, chooses strict or contextual logic-load rules, and only then applies review findings.

## Runtime Contract

- Review agents only advise. They never rewrite body text.
- The rewriter owns conflict resolution and one consolidated edit.
- Logic load is heading-driven. Simple headings use strict checks for judgment count, causal-chain length, and concept density; complex headings use contextual checks and require layered reasoning.
- If the rewrite gate fails, the repair target is `section-editor-{section_id}` / `section-rewrite-gate-{section_id}`. The review fan-out should not be rerun.
- Review and rewrite nodes declare `max_retries=2`; the runner stops at retry limit and writes a retry-limit event instead of looping.
- The old downstream files are preserved:
  - `final.md`
  - `review-ai-tone.json`
  - `terms.json`

## Risk

This increases per-section LLM calls compared with the previous single editor node. The intended runtime saving comes from avoiding sequential review-modify-review loops and from preserving the section parallel limit of 3.
