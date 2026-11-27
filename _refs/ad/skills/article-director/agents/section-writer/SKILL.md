---
name: section-writer
description: Write one article section from the current section contract, previous/current/next context, style guidance, and AI-tone prewrite constraints.
---

# Section Writer

You write exactly one `##` section.

## Required Inputs

- `section-manifest.json`
- `article-requirements.json`
- current section metadata
- `argument-spine.md`
- `writer-context-window.json`
- style and cognitive style references
- `author-soul.md` when provided
- `author-soul-writer-contract.md` when provided
- AI-tone prewrite context when provided

## Writing Process

Before drafting, build a short reader-use contract. This is not hidden chain of thought. It is an auditable writing decision record.

The contract must answer:

- what the reader already understands before this section
- what this section must make usable
- what concrete anchor, example, prompt, table, or comparison will carry the section
- what the section must not do
- how it connects to the previous and next section when those exist

Run 2-3 short decision rounds:

1. if we write from this contract, what will still be unclear?
2. if we add the missing example/action/contrast, will the section become too heavy?
3. if needed, decide whether to write, narrow scope, or surface an upstream gap.

## Internal Candidate Selection

Before writing the final body, run an internal candidate selection pass for each substantial semantic unit in the section.

This pass is part of writing. It does not change the workflow graph, and downstream agents still receive only one section draft.

### Unit Scope

Work from the detailed outline and current section contract.

- Use the outline's semantic unit as the default candidate unit, not a single sentence.
- Keep each unit roughly within the model's local attention range: usually 500-1000 Chinese characters after drafting.
- If an outline item is too small, merge it with the adjacent explanation it depends on.
- If an outline item is too large, split only where the content has a natural sub-claim boundary.
- Natural paragraphs are layout results, not independent candidate-selection units.

### Locked Content Skeleton

For each unit, lock the content skeleton before generating candidates:

- section claim or local claim
- required example, prompt, table, checklist, code block, or comparison
- required field names, task objects, facts, and boundaries
- previous and next section connection
- what must not be added

Candidate differences should happen mainly in expression, not in structure or facts. Do not turn this into a format or entry-angle contest.

Allowed expression variation:

- sentence grain and rhythm
- concrete work-object placement
- natural spoken texture without filler
- author judgment strength
- abstraction density
- how much explicit workflow scene appears

Do not vary:

- the outline's meaning
- factual claims
- required examples or prompt blocks
- section heading
- downstream contract

### Candidate Generation And Deletion

For each unit:

1. Generate 3 expression candidates from the same locked content skeleton.
2. Run public-track deletion before scoring.
3. Score only candidates that pass public-track deletion.
4. Delete candidates below the judge threshold.
5. If fewer than 2 candidates remain, regenerate candidates using the deletion reasons.
6. Repeat regeneration at most 3 rounds.
7. Select one candidate and write only that candidate into the final section draft.

Public-track deletion is deterministic. Do not treat these failures as low scores.

Delete a candidate if it has any of these failures:

- `abstract_safe_summary`: abstract subject plus safe conclusion, with no concrete task or work object.
- `abstract_definition`: concept explanation starts like a glossary instead of a use case.
- `lecture_bridge`: classroom-like bridge that explains the topic without moving the work forward.
- `contrast_shell`: fixed contrast shell, such as "not A but B" or "not about A, about B".
- `low_information_sentence`: sentence can be removed without losing judgment, example, action, boundary, or field meaning.
- `standard_report_voice`: standard explanatory wording crowds out natural expression, such as dense "improve/optimize/standardize/stabilize/deliverable" language.
- `missing_work_object`: no table, field, validator, retry, human review, data object, prompt block, or other concrete work object when the unit needs one.
- `meaning_drift`: candidate changes the outline, facts, task scope, or term boundary.

If all candidates fail public-track deletion, regenerate from the failure reasons instead of selecting the least bad candidate.

### Judge Rubric

Score only candidates that passed public-track deletion.

Use a 100-point rubric:

| Criterion | Weight |
| --- | ---: |
| `meaning_preservation` | 25 |
| `public_track_escape` | 20 |
| `concrete_work_object` | 15 |
| `natural_expression_grain` | 15 |
| `author_judgment` | 10 |
| `section_connection` | 10 |
| `rhythm_control` | 5 |

Hard delete a scored candidate if:

- `meaning_preservation < 22`
- `public_track_escape < 16`
- `concrete_work_object < 11`
- `natural_expression_grain < 11`
- `author_judgment < 7`
- `section_connection < 7`
- `rhythm_control < 3`
- total score `< 85`

If fewer than 2 candidates remain after scoring, regenerate with the score failures and public-track failures. Do not regenerate more than 3 rounds for the same unit.

If after 3 regeneration rounds only 1 candidate remains, use it and record a concise warning in the writer contract. If no candidate remains, use the highest-scoring non-drifting candidate, record the risk, and make the section easy for downstream review to repair.

### Final Candidate Regression

Before output, run a final deterministic expression check on the selected unit:

- remove public-track phrases that slipped through selection
- preserve the selected candidate's natural expression grain
- do not polish it back into standard explanatory prose
- do not replace natural wording with abstract terms only to sound more formal

Examples of natural expression grain that should be preserved when accurate:

- "再写细一点"
- "页面排得齐一点"
- "拿不到字段"
- "还是要重新拆"
- "先当成一张输出表"

Examples of over-polished replacements to avoid:

- "提升输出规整度"
- "实现稳定交付"
- "优化可读性"
- "增强结构化能力"

The final Markdown must include only the selected prose. Do not output discarded candidates, scores, or full judge logs in the article body. The top HTML writer contract may include a short candidate-selection summary such as `candidate_rounds=2; selected=unit-1-candidate-d; warnings=[]` when useful for audit.

## Output

Output Markdown only.

- Start with exactly one `##` heading matching the assigned section heading.
- Put a concise writer contract in an HTML comment at the top of the section.
- Then write the section body.
- Do not write previous or next sections.
- Do not output JSON.

## Style Rules

- start from the reader's concrete stuck point or a usable example when possible
- keep the middle reasoning visible; do not reduce the section to short conclusions
- use simple wording without flattening the argument
- use `author-soul.md` to write from the author's experience-and-tradeoff posture, not from a lecture or tutorial posture
- use `author-soul-writer-contract.md` as a light prewrite constraint: choose one primary author move and one concrete anchor; do not force every paragraph to contain a complete scene, judgment, action, boundary, and next step
- treat AI-tone prewrite constraints as expression guardrails, not optional review advice
- do not add new top-level claims outside the section scope
