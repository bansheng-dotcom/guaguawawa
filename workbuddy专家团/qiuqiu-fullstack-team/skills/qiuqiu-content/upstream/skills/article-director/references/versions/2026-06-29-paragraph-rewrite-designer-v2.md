# 2026-06-29 Paragraph Rewrite Designer v2

## Change

Upgrade `paragraph-rewrite-designer` from a single target-draft planner to a judged rewrite-unit designer.

The lean section edit path stays unchanged:

```text
review fan-out -> section-edit-brief -> paragraph-rewrite-designer -> section-rewriter
```

The output file name also stays unchanged:

```text
sections/{section_id}/paragraph-rewrite-design.json
```

## Reason

The v1 designer still behaved too much like a conservative repair planner. It could mark paragraphs as `keep` and only fix local review findings, which left scattered AI-like prose in otherwise acceptable paragraphs.

The v2 contract changes the posture:

- every reader-facing body paragraph receives at least a `micro_polish` instruction
- only meaningful rewrite units receive multi-candidate generation and judge scoring
- `section-rewriter` assembles the selected drafts and applies micro edits; it does not re-judge candidates

This keeps AI-tone cleanup broad without making every paragraph run through an expensive candidate loop.

## Rubric

The designer must use this exact 100-point judge rubric:

| Criterion | Weight |
| --- | ---: |
| `meaning_and_fact_preservation` | 20 |
| `review_absorption` | 20 |
| `de_ai_tone` | 15 |
| `reader_readability` | 15 |
| `workflow_scene` | 10 |
| `author_judgment_and_light_soul` | 10 |
| `section_connection` | 10 |

`author_judgment_and_light_soul` internally means 5 points for author judgment and 5 points for light soul influence. It should not increase heavy "I" posture or turn each paragraph into a full soul checklist.

## Contracts

- `paragraph-rewrite-design.json` v2 includes `judge_rubric`, `coverage`, `rewrite_units`, `paragraph_micro_edits`, `preserved_non_body_blocks`, and `handoff_to_rewriter`.
- `coverage.covered_paragraph_ids` must cover every reader-facing id in `coverage.body_paragraph_ids`.
- `unit_redesign` units must include 2-4 candidates, candidate scores, `selected_candidate`, `selected_draft`, and `judge_reason`.
- `section-editor-output.json` keeps the old downstream file name and top-level schema, but `paragraph_rewrite_design_consumed` now records `covered_paragraph_ids`, `used_units`, `adapted_units`, `micro_edits_applied`, `bridge_edits`, and `deferred_items`.

## Validation

Run:

```powershell
python -m py_compile skills/article-director/scripts/compile_expanded_workflow.py skills/article-director/scripts/validate_output.py skills/article-director/scripts/validate_section_rewrite_gate.py skills/article-director/scripts/validate_review_chain.py
python skills/article-director/scripts/validate_output.py --output <v2-design.json> --schema paragraph-rewrite-design
python skills/article-director/scripts/validate_section_rewrite_gate.py --topic-id <topic_id> --section-id <section_id>
python skills/article-director/scripts/validate_review_chain.py --topic-id <topic_id>
```

## Rollback

Rollback only this change:

1. Restore `agents/paragraph-rewrite-designer/SKILL.md` to v1 `designs[]` output.
2. Restore `agents/section-rewriter/SKILL.md` to consuming `used_designs/adapted_designs/ignored_designs`.
3. Restore the `paragraph-rewrite-design` validation branch in `validate_output.py`.
4. Restore `validate_section_rewrite_gate.py` to the legacy `non-keep designs` checks.
5. Restore the compiler prompt, topology, file convention, and agent index wording.

No workflow edge, node id, output path, or materializer contract needs to change.
