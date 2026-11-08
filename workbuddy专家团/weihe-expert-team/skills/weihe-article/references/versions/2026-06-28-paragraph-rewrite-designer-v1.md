# 2026-06-28 Paragraph Rewrite Designer v1

## Change

Insert `paragraph-rewrite-designer` between deterministic review merge and `section-rewriter` in lean-v1.

Old lean section edit path:

```text
review fan-out -> section-edit-brief -> section-rewriter
```

New lean section edit path:

```text
review fan-out -> section-edit-brief -> paragraph-rewrite-designer -> section-rewriter
```

## Reason

Directly asking `section-rewriter` to consume all review outputs made it behave like a review-priority resolver. That is too weak for prose generation: one sentence or paragraph may need many valid rewrite shapes while preserving meaning.

The new designer does not rewrite final Markdown. It outputs paragraph-level target designs so the rewriter can execute a coherent content change instead of mechanically applying review comments.

## Contracts

- `author-soul-writer-contract.md` gives writer a light prewrite author posture and prevents every paragraph from becoming a full soul checklist.
- `paragraph-rewrite-design.json` gives rewriter target paragraph function, target shape, near-draft text when useful, preserved meaning, and avoid items.
- `section-editor-output.json` must include `paragraph_rewrite_design_consumed` so the gate can verify the design was used, adapted, or explicitly ignored.

## Validation

Run:

```powershell
python -m py_compile skills/article-director/scripts/compile_expanded_workflow.py skills/article-director/scripts/validate_output.py skills/article-director/scripts/validate_section_rewrite_gate.py skills/article-director/scripts/validate_review_chain.py
python skills/article-director/scripts/validate_review_chain.py --topic-id <topic_id>
python skills/article-director/scripts/validate_output.py --output skills/article-director/outputs/<topic_id>/run_<topic_id>_expanded.py --schema expanded-workflow
```

## Rollback

Remove the designer node and edge in `compile_expanded_workflow.py`, restore the edge `merge-edit-brief-{section_id} -> section-editor-{section_id}`, remove `paragraph_rewrite_design_consumed` from `section-editor-result` validation, and delete the extra gate checks for `paragraph-rewrite-design.json`.
