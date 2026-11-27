# Article Workflow Schema

## Strategy Profile

- strategy lives in `skills/article-director/outputs/{topic_id}/workflow-profile.json`
- built-in strategies:
  - `knowledge-explainer`
  - `teaching-playbook`
- strategy controls:
  - concept explanation policy
  - section intent
  - step boundary rules
  - required step fields for tutorial-like sections

## Core Nodes

- `topic-architect-01-plan`
- `topic-architect-01-exec`
- `director-inspect-01`
- `outline-confirmation-01`
- `writer-package-*`
- `adversarial-reviewer-*`
- `draft-assembler-01`
- `style-harmonizer-01`
- `source-map-repair-01`
- `appendix-agent-01`
- `finalize-draft-01`
- `article-review-a-01`
- `article-review-b-01`
- `review-diff-01`
- `code-check-01`
- `human-approval-01`

## Default Chain

The stable default production chain is:

1. `outline-confirmation-01`
2. `writer-package-*`
3. `adversarial-reviewer-*`
4. `draft-assembler-01`
5. `style-harmonizer-01`
6. `source-map-repair-01`
7. `appendix-agent-01`
8. `finalize-draft-01`
9. `article-review-a-01`
10. `article-review-b-01`
11. `review-diff-01`
12. `code-check-01`
13. `human-approval-01`

Default chain stops at final article approval.

These are not baseline default nodes:

- `content-ingest-01`
- publish preparation nodes
- package gate nodes such as `package-check-*`
- repair-loop nodes such as `post-review-revision-*`
- older structure / primer / deep-dive side routes unless explicitly enabled

## Public Output Contract

- outline: `tmp/{topic_id}-outline.md`
- detailed outline: `tmp/{topic_id}-detailed-outline.md`
- draft: `tmp/{topic_id}-draft.md`
- review: `state/reviews/{topic_id}.json`
- appendix output: `skills/article-director/outputs/{topic_id}/appendix-agent-01/output.md`

## Optional Approved Asset Contract

- publish file: `platforms/知识星球/{formal_id}.md`
- outline archive: `state/topic-requirements/{formal_id}-outline.md`
- asset dir: `assets/publish-ready/{formal_id}/`
- source dir: `state/content-sources/{formal_id}/`
- content index: `state/content-index/content-library.json`

These outputs apply only when approved-content ingest is explicitly enabled outside the stable default chain.

## Post-Draft Structure Contract

Structure shaping happens after draft writing.

`style-harmonizer-01` may:

- tighten rhythm
- unify tone
- smooth transitions
- remove obvious repetition

It may not:

- invent new claims
- invent new evidence
- change article direction

## Appendix Contract

The appendix is generated outside body paragraphs and should include:

- `## 附录：术语速查`
- `## 附录：参考资料与一句话说明`
- `## 延伸阅读`
