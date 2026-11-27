---
name: section-editor
description: Umbrella compatibility contract for the section-editor workflow; active lean edits are handled by section-rewriter after review fan-out.
---

# Section Editor

This is the umbrella contract for the section-editor workflow.

The lean workflow no longer uses one agent to review and rewrite at the same time. It is hardcoded as:

1. parallel section reviews: AI tone, style, logic, structure, simplify
2. deterministic merge into `section-edit-brief.json`
3. one `paragraph-rewrite-designer` v2 pass that outputs `paragraph-rewrite-design.json`
4. one `section-rewriter` assembly pass that outputs `section-editor-output.json`
5. deterministic rewrite gate before materialization

Do not collapse those roles back into one prompt-only pass.

## Responsibilities

- keep the review fan-out advisory only
- keep rewrite unit selection, candidate generation, and judging inside `paragraph-rewrite-designer`
- keep final body assembly, paragraph micro edits, and connection smoothing inside `section-rewriter`
- audit AI tone using the ai-tone-director context pack and scan
- check logic against `argument-spine.md`
- check structure, paragraph rhythm, tables, bullets, and section flow
- revise the section into final Markdown through one consolidated rewrite
- use v2 paragraph rewrite designs as the bridge between review findings and final prose edits
- remove low-information bridge sentences that do not add a judgment, example, boundary, or action
- preserve the section heading and scope

## Required Inputs

- current section draft
- `argument-spine.md`
- `paragraph-tags.json` when available
- `ai-tone-context-pack.json`
- `ai-tone-scan.json`
- style references and cognitive style references
- `ai-tone-director` integration contract
- `paragraph-rewrite-design.json` when available

## AI Tone Contract

Do not invent local AI-tone rules. Consume `ai-tone-context-pack.json` and `ai-tone-scan.json`.

The output must include `ai_tone_audit.ai_tone_invocation` exactly matching the context pack:

- `topic_id`
- `section_id`
- `phase`
- `idempotency_key`
- `source_hash`

If the deterministic scan has hits but they are acceptable, include `deterministic_evidence_acknowledged=true` and `false_positive_notes`.

Do not mark these continuity shells acceptable without a concrete false-positive reason: “继续往下走”, “很好理解”, “把这件事分清楚”, “下一步很自然”, “卡住的点很具体”, “差别会变得很清楚”, “选择题很具体”, “判断标准很简单”, “优先级应该很清楚”, or “不是 A 而是 B” used as a generic transition.

## Output

The active output contract belongs to `agents/section-rewriter/SKILL.md`; the workflow keeps the legacy `section-editor-output.json` name for downstream compatibility.

Output strict JSON only when an older generated workflow still calls this compatibility prompt:

```json
{
  "pass": true,
  "score": 85,
  "summary": "",
  "scope": "section",
  "section_id": "",
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
  "final_markdown": "## ..."
}
```

`final_markdown` must be the final revised section. Keep exactly one `##` heading. Remove writer-contract HTML comments.
