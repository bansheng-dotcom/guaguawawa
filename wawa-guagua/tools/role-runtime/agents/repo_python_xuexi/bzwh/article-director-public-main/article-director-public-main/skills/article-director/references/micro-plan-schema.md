# Micro Plan Schema

## Purpose

This protocol defines the first-stage micro-plan artifacts for `article-director`.

All generated JSON files must:

- use UTF-8
- use `ensure_ascii=False`
- keep stable top-level keys
- keep file paths relative to project root when stored as strings

## Generated Files

### `micro-plan/global-plan.json`

Required top-level fields:

- `schema_version`
- `plan_type`
- `topic_id`
- `generated_at`
- `source_files`
- `section_summary`
- `package_summary`
- `execution_chain`
- `coordination_rules`
- `outputs`

Field intent:

- `schema_version`: current protocol version, start with `micro-plan/v1`
- `plan_type`: fixed string `global-plan`
- `source_files`: relative paths for `section-manifest.json` and `article-packages.json`
- `section_summary`: article-wide counts, totals, and risk distribution
- `package_summary`: package-level scope overview for all packages
- `execution_chain`: deterministic package node chain and reserved review templates
- `coordination_rules`: stable protocol rules used by later runners or planners
- `outputs`: where the node micro plans and revision plans live

### `micro-plan/node-micro-plans.json`

Required top-level fields:

- `schema_version`
- `plan_type`
- `topic_id`
- `generated_at`
- `package_plans`
- `review_templates`

Each `package_plans[]` item must contain:

- `package_id`
- `package_order`
- `package_scope`
- `nodes`

Each `nodes[]` item must contain:

- `node_id`
- `role`
- `node_type`
- `stage`
- `package_id`
- `depends_on`
- `next_nodes`
- `input_files`
- `output_file`
- `objective`
- `section_scope`
- `focus_points`
- `constraints`
- `acceptance_checks`
- `handoff_notes`

Required package node coverage:

- `writer-package`
- `primer-writer`
- `deep-dive-researcher`
- `structure-editor`
- `narrative-smoother`
- `adversarial-reviewer`

Recommended extra package node:

- `package-check`

Recommended review templates:

- `article-review-a-01`
- `article-review-b-01`

### `micro-plan/revision-plans/{node_id}-rev01.json`

Required top-level fields:

- `schema_version`
- `plan_type`
- `topic_id`
- `revision_id`
- `created_at`
- `node_id`
- `role`
- `reason`
- `source_files`
- `context`
- `revision_framework`

`revision_framework` should be a repair scaffold, not a final answer. It should include:

- `status`
- `problem_statement`
- `must_preserve`
- `revision_goals`
- `repair_actions`
- `validation_checks`
- `handoff`

## Package Scope Contract

`package_scope` should summarize only the sections owned by that package:

- `section_ids`
- `section_headings`
- `target_word_count`
- `target_paragraph_count`
- `package_score`
- `risk_tier`
- `requires_fact_verification`
- `fact_sections`
- `image_sections`
- `sections`

Each `sections[]` entry should preserve the key section signals needed by downstream planning:

- `section_id`
- `heading`
- `target_word_count`
- `target_paragraph_count`
- `risk_tier`
- `argument_complexity`
- `cross_section_dependency_count`
- `requires_fact_verification`
- `requires_image`
- `recommended_presentation`
- `parallel_point_count`

## Node Semantics

### `writer-package`

- produces the first package draft
- must stay inside package boundary
- must preserve section thesis and evidence anchors
- should optimize for complete, natural draft content before later structure editing

### `structure-editor`

- reorganizes a written package draft into easier public-facing structure
- may split paragraphs, add lists, or turn comparisons into tables
- must not invent new content

### `primer-writer`

- rewrites each section opening for beginners
- must not replace the package thesis

### `deep-dive-researcher`

- adds theory, papers, mechanism, implementation, or boundary detail
- must not turn the body into an appendix or literature dump

### `narrative-smoother`

- connects shallow explanation and deep explanation
- removes jumps, filler, and tone drift
- may improve rhythm, but may not flatten structural blocks, tables, or lists

### `adversarial-reviewer`

- pressure-tests logic, jargon, unsupported claims, and AI-style phrasing
- outputs repaired body text, not an audit memo

### `package-check`

- validates the final package output after adversarial revision
- validates package coverage and output readiness before assembly

### Review Templates

`article-review-a-01` and `article-review-b-01` are global templates, not package nodes.

- `article-review-a-01`: logic, structure, and boundary discipline
- `article-review-b-01`: readability, examples, and AI-flavor scan

## Stability Rules

- Node IDs must follow existing workflow naming.
- Package plans must remain deterministic for the same manifest inputs.
- Revision plans may infer `package_id` from `node_id`, but explicit `package_id` wins.
- New fields may be added later, but existing required fields should not be renamed in `v1`.
