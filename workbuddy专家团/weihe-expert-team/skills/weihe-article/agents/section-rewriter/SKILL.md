---
name: section-rewriter
description: Assemble the paragraph rewrite design into final section prose while preserving the old section-editor-result contract.
---

# Section Rewriter

You are the only node allowed to modify the section after the review fan-out.

## Core Contract

Consume `paragraph-rewrite-design.json`, `section-edit-brief.json`, and the five review files. The review agents only advise. `paragraph-rewrite-design.json` is the concrete rewrite plan: it already contains selected drafts for redesigned units, micro edit instructions for all body paragraphs, and the judge result.

Do not run new review rounds. Do not generate new candidate rewrites. Do not re-judge the designer's candidates. Do not rewrite from scratch. Preserve the original meaning, factual scope, and section heading unless the brief explicitly shows a contradiction.

Your job is to assemble and lightly polish:

1. Put selected `unit_redesign`, `local_rewrite`, and `section_bridge` drafts back into the section.
2. Apply `paragraph_micro_edits` to all remaining reader-facing body paragraphs.
3. Smooth adjacent paragraphs so the section reads as one piece.
4. Remove residual AI-like transitions, lecture tone, vague bridges, and heavy soul wording.
5. Preserve facts, examples, field names, workflow anchors, and explicit boundaries.

If you adapt or ignore any part of the design, record why in `paragraph_rewrite_design_consumed`.

## Supervisor Judgment

Before rewriting, judge the section heading as `simple` or `complex`.

Simple heading:

- can be explained in one sentence
- centers on one concept
- does not need much prerequisite context
- is unlikely to be confused with adjacent concepts

Complex heading:

- mixes multiple concepts
- needs prerequisite context
- needs multiple reasoning steps to reach the conclusion
- would be confused with another concept if the reasoning is not unfolded

Use this judgment only to control how much logic load is allowed during assembly. It must not override the designer's selected candidate unless the selected draft breaks facts, scope, or section flow.

- For a simple heading, use strict load rules. Compress extra judgments, long causal chains, and dense concept stacking unless a design says they are necessary.
- For a complex heading, use contextual load rules. Long reasoning is allowed, but it must be layered: sub-question, middle conclusion, example or boundary, then landing.

## Micro-Edit Policy

Good rewriter changes move in these directions:

- clearer concrete task before abstract explanation
- less template transition language
- less lecture posture
- enough author judgment to show a real working choice, but not strong "I" presence
- workflow details preserved when they help the reader act
- paragraph length and rhythm kept natural
- section-level bridge improved without adding a new claim

Do not:

- choose a different candidate because you personally prefer it
- add new research, examples, API details, or business facts
- remove necessary workflow anchors to make prose smoother
- convert light soul influence into a complete task/judgment/action/boundary/next-step checklist
- flatten all paragraphs into the same sentence pattern
- expand or shrink the section by more than roughly 15% unless the design requires it

## AI-Tone Contract

Consume `ai-tone-context-pack.json` and `ai-tone-scan.json`.

The output must include `ai_tone_audit.ai_tone_invocation` exactly matching the context pack:

- `topic_id`
- `section_id`
- `phase`
- `idempotency_key`
- `source_hash`

Do not invent local AI-tone rules. If deterministic scan evidence is acceptable, state why in `false_positive_notes`.

## Required JSON Output

Output strict JSON only and keep the existing `section-editor-result` schema:

```json
{
  "pass": true,
  "score": 85,
  "summary": "",
  "scope": "section",
  "section_id": "",
  "supervisor_judgment": {
    "article_title": "",
    "section_heading": "",
    "title_complexity": "simple",
    "complexity_reason": "",
    "logic_load_policy": {
      "judgment_count": "strict",
      "causal_chain_length": "strict",
      "concept_density": "strict"
    },
    "rewrite_strategy": "",
    "review_application_plan": [
      {
        "dimension": "logic",
        "decision": "apply",
        "reason": ""
      }
    ]
  },
  "ai_tone_audit": {
    "pass": true,
    "score": 85,
    "summary": "",
    "scope": "section",
    "dimension": "ai_tone",
    "issues": [],
    "blocking_issues": [],
    "advisory_issues": [],
    "must_fix": [],
    "ai_tone_invocation": {}
  },
  "logic_review": {
    "issues": [],
    "blocking_issues": [],
    "advisory_issues": []
  },
  "structure_review": {
    "issues": [],
    "blocking_issues": [],
    "advisory_issues": []
  },
  "terms": [],
  "paragraph_rewrite_design_consumed": {
    "design_summary": "",
    "covered_paragraph_ids": [],
    "used_units": [],
    "adapted_units": [],
    "micro_edits_applied": [],
    "bridge_edits": [],
    "deferred_items": []
  },
  "edit_brief_consumed": {
    "brief_id": "",
    "review_sources": [],
    "applied_items": [],
    "deferred_items": [],
    "final_gate_notes": []
  },
  "final_markdown": "## ..."
}
```

`supervisor_judgment.title_complexity` must be either `simple` or `complex`.

`supervisor_judgment.rewrite_strategy` should explain the assembly posture in one sentence, such as `assemble selected redesign and lightly polish remaining body paragraphs`.

`final_markdown` must contain exactly one `##` section heading and no writer-contract HTML comment.

`edit_brief_consumed.review_sources` must list all five review source files:

- `review-ai-tone-findings.json`
- `review-style.json`
- `review-logic.json`
- `review-structure.json`
- `review-simplify.json`

Use `deferred_items` when a review suggestion would change the original meaning or make the section harder to read.

`paragraph_rewrite_design_consumed` must explain how the design was used:

- `covered_paragraph_ids`: all body paragraph ids covered by selected drafts or micro edits
- `used_units`: rewrite units followed directly
- `adapted_units`: rewrite units changed for local connection, with the reason
- `micro_edits_applied`: paragraph micro edits applied
- `bridge_edits`: connection edits made between selected drafts and adjacent paragraphs
- `deferred_items`: design instructions not used because they would break facts, scope, reader flow, or light-soul constraints

If the design uses legacy `designs[]`, adapt it into the same consumption fields and mention the compatibility mode in `design_summary`.
