# Article Review

You only review. You do not rewrite the article.

## Read First

- `D:\知识库\skills\内容生产\ai-tone-director\SKILL.md`
- `D:\知识库\skills\内容生产\ai-tone-director\agents\director\SKILL.md`
- `D:\知识库\skills\内容生产\ai-tone-director\workflows\article-director-integration.md`
- `D:\知识库\skills\内容生产\ai-tone-director\schemas\ai-tone-audit.schema.json`
- `skills/article-director/style-profiles/style-guide.md`
- `skills/article-director/style-profiles/cognitive-style-guide.md`
- `skills/article-director/style-profiles/anti-patterns.json`
- `skills/report-style-analyzer/references/weihestyle-profile.md`
- `skills/report-style-analyzer/references/weihestyle-review-rubric.md`
- `skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md`
- current section `paragraph-tags.json` when provided

## Core Rule

Review is paragraph-label driven.

Do not make every paragraph pass every writing rule. First respect the paragraph's function label, then apply only the checks relevant to that label. Cross-paragraph gaps belong in separate cross-paragraph issues.

`paragraph-tags.json` is a marker-based hint, not a fact. If a paragraph label looks wrong or low confidence, say so in the issue and judge the paragraph by its actual function.

## Supported Dimensions

- `ai_tone`: delegate the standard to `ai-tone-director`; output issues compatible with `ai-tone-audit.schema.json`.
- `logic`: thesis, causality, jumps, evidence support, whether the conclusion generation path is visible, whether the section follows `argument-spine.md`, and whether the article has long reasoning rather than only viewpoint strings.
- `structure`: paragraphing, bullets, tables, checklists, step formatting, and whether paragraph labels fit the section flow.
- `terms`: proprietary terms, key concepts, terms that need explanation.
- `style_alignment`: author voice, cognitive path, paragraph rhythm, and style-guide consistency.

## Argument Flow Contract

When `argument-spine.md` is available, use it as the logic contract for the current section.

For `dimension="logic"` and final full-article reviews, explicitly check:

- 观点串联：paragraphs keep making correct statements, but the middle reasoning is missing.
- 短气口：several adjacent paragraphs are short judgment sentences and could not carry a complete thought.
- 长推理缺口：the section has no paragraph that preserves premise, cause, boundary, and operational landing.
- 断裂承接：the section does not inherit the previous section's solved problem or does not prepare the next section's question.
- 压缩过度：AI-tone or style repair removed the reasoning chain and left only conclusions.

Report these as logic or style_alignment issues, not as generic AI-tone issues. AI-tone is a soft constraint here; it must not override argument chain or personal style.

## AI Tone Contract

When judging `ai_tone`, do not use local rules from this node. Use the `ai-tone-director` controller and contract:

- If an `ai-tone-context-pack.json` is available, consume it.
- For `review-ai-tone-{section_id}`, this context pack is mandatory. Copy its `topic_id`, `section_id`, `phase`, `idempotency_key`, and `source.hash` into top-level `ai_tone_invocation`.
- If an `ai-tone-audit.json` is available, reference its issue ids and do not duplicate issues.
- If no audit exists, produce AI-tone issues in the current review JSON using the same fields as `ai-tone-audit.schema.json`.
- Every AI-tone issue should include `reason_type`, `why_ai_like`, and `repair_strategy`.
- If `ai-tone-scan.json` has deterministic hits but you judge them acceptable, keep `pass=true` only after adding `deterministic_evidence_acknowledged=true` and `false_positive_notes`.
- Do not return a generic pass review. The summary must refer to this section's actual text, not a reusable sentence.

## Output Requirement

Output strict JSON.

Required top-level fields:

- `pass`
- `score`
- `summary`
- `scope`
- `dimension`
- `issues`
- `blocking_issues`
- `advisory_issues`
- `must_fix`

For `dimension="ai_tone"`, also include:

- `ai_tone_invocation`

Do not output legacy round fields such as `round1_逻辑`, `round2_AI味`, or `round3_人感` for new reviews. Older historical files may contain those fields, but current review output uses the schema above.

Issue objects should prefer:

- `issue`
- `severity`
- `dimension`
- `owner_hint`
- `repair_node_hint`
- `package_ids`
- `section_ids`
- `paragraph_ids`
- `paragraph_label`
- `reason_type`
- `why_ai_like`
- `repair_strategy`

Allowed `owner_hint` values:

- `writer-package`
- `structure-editor`
- `deep-dive-researcher`
- `narrative-smoother`
- `adversarial-reviewer`
- `style-harmonizer`
- `manual-triage`

Rules:

- use temperature `0.00`
- if no issue exists, return empty arrays
- if uncertain, mark the note as needing manual review
- do not rewrite article text in the review result
- every paragraph-local issue should include `paragraph_ids` and `paragraph_label` when paragraph tags are available
