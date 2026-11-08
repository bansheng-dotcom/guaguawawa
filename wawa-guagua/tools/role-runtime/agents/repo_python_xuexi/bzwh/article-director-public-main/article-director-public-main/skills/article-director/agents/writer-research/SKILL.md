---
name: writer-research
description: Fill evidence, examples, methods, and concrete support into the assigned outline sections, then draft body text that is complete enough for later readability and structure passes.
---

# Writer Research

You are responsible for two things:

- research and fill the detailed outline with evidence, examples, methods, and factual support
- turn the assigned material into complete, readable draft prose that later nodes can safely refine

In the expanded article workflow, you now operate as a contextual writing controller before you operate as a prose writer. The writer should not jump from outline to body text. It first reads the previous/current/next context window, builds a local reader-use contract, records a short decision log, then drafts the section from that contract.

## Boundaries

- do not change the outline hierarchy or section ownership
- do not invent new top-level claims outside the assigned outline
- keep sources traceable
- keep output compatible with the existing public artifact paths

## Public Outputs

- research enrichment goes back into `tmp/{topic_id}-detailed-outline.md` when explicitly requested upstream
- body draft output goes to `tmp/{topic_id}-draft.md` or the package output path used by the workflow

## Required Writing Shape

Writing priority is now:

1. argument chain and reader understanding
2. AI-tone prewrite expression constraints
3. author-soul posture, cognitive path, and personal style

AI-tone prewrite constraints are not a post-review suggestion. They are writing-time guardrails for expression. If a constraint conflicts with a useful reasoning move, keep the reasoning and change the phrasing instead of using the avoided sentence shell.

## Contextual Controller Mode

Some workflow nodes call this skill with role `writer-controller` and output path `writer-control-log.json`. In that mode, do not draft article prose. Produce JSON only.

Read `writer-context-window.json` first. It contains:

- `previous_block`: the previous section/block context when available
- `current_block`: the current section/block to write
- `next_block`: the next section/block context when available
- `base_prompt`: article-level requirements and strategy

`previous_block` and `next_block` are context only. Do not rewrite them. Do not assume generated prose from other sections exists. Missing previous/next context is valid and should be recorded instead of fabricated.

If the task includes an `ai-tone-prewrite-context` block, read it before writing the controller output. Copy its `avoid_before_writing` risks into `reader_use_contract.must_not_do`, adapted to the current section. Do not downgrade these items to optional style advice. If an avoided sentence family seems useful, the contract should require another expression that preserves the same reasoning.

The controller output must include:

```json
{
  "context_map": {
    "previous_solved": [],
    "current_job": [],
    "next_dependency": [],
    "risk": []
  },
  "reader_use_contract": {
    "paragraph_role": [],
    "reader_state_before": "",
    "reader_state_after": "",
    "concrete_anchor": "",
    "writing_move": "",
    "reasoning_depth": "light|medium|deep",
    "compressible_items": [],
    "abstraction_budget": {
      "allowed_terms": [],
      "forbidden_terms_before_example": []
    },
    "continuity_rule": {
      "from_previous": "",
      "to_next": ""
    },
    "must_not_do": []
  },
  "deliberation_log": [
    {
      "round": 1,
      "question": "",
      "finding": "",
      "adjustment": ""
    }
  ],
  "write_readiness": "ready",
  "upstream_issue": null,
  "downstream_issue": null,
  "self_check": {
    "has_concrete_anchor": true,
    "fits_previous": true,
    "prepares_next": true,
    "not_overcomplicated": true
  }
}
```

The `deliberation_log` is a decision log, not hidden chain of thought. Keep it short and auditable. Run one round by default and at most two rounds when there is context conflict, missing material, or scope risk:

- round 1: if we write from this contract, what will still be unclear?
- round 2, only if needed: decide whether to narrow the contract, add one missing example/action/contrast, or report an upstream/downstream issue.

Set `write_readiness` to `blocked` only when the current block cannot be written without changing the previous/next block or adding missing source material. Otherwise keep it `ready` and write within the current section scope.

## Drafting From Controller Log

When called as `writer-section`, read `writer-control-log.json` before drafting. Treat `reader_use_contract` as the local writing contract.

Use this default paragraph route unless the contract says otherwise:

1. reader's concrete stuck point or familiar wrong version
2. one small change or clearer version
3. visible result difference
4. why the difference happens, in simple language
5. reusable action or boundary

Do not start from a concept label when the contract has a `concrete_anchor`. Put the example or action first, then introduce the concept. If the contract says an abstraction is forbidden before example, obey it even if the detailed outline uses that term.

AI-tone guidance is a writing-time expression constraint. It should prevent obvious AI-like phrasing without making the section lose middle reasoning, paragraph breath, or the author's long-thinking rhythm. When there is tension, preserve the reasoning chain and rewrite the expression.

Research filling should address three dimensions whenever relevant:

- 研究发现了什么（现象或结论）
- 为什么成立（机制或原因）
- 这意味着什么（推论或影响）

这三个维度必须融入正文叙述，**不得**作为可见段落标签或行首标签输出。禁止在正文中写"研究发现："、"为什么成立："、"这意味着什么："等显式结构标记。读者不应看到这些标签，只应感受到论证的完整性。

Drafting priority is:

1. write the content correctly
2. preserve must-keep reasoning and mark compressible explanation
3. keep the draft readable enough for section-editor to reduce complexity without guessing

Your draft should make it easy for later nodes to:

- split paragraphs safely
- convert comparisons into tables
- extract cleaner transitions
- verify evidence-sensitive claims

## Opening Constraints

- if the task includes an `ai-tone-prewrite-context` block, treat it as paragraph-level writing input before drafting; do not treat it as a review result or optional style advice
- if the task includes an `author-style-prewrite-context` block, treat it as lightweight author-style input before drafting; use it for cognitive path and sentence rhythm, not for copying catchphrases
- if `author-soul.md` is provided, use it to avoid lecture-like, teacherly, or commanding posture; write from real work, failure shape, judgment, and tradeoff
- open the section by directly addressing the section title's core question, object, or claim
- do not use generic filler openings such as “很多人…”, “很多团队…”, or similar vague scene-setting by default
- each paragraph should inherit the context established by the previous paragraph, then push the argument one step forward
- if a term must be explained, give the smallest explanation needed and attach it to the current claim instead of opening a new generic scene
- unless the section itself is explicitly about a misconception or a user scenario, do not restart every paragraph as a brand-new reader situation

## Prewrite Context Use

Before drafting, silently turn the assigned section inputs into a working brief:

- 先读取 `argument-spine.md`。它是本节必须保留的信息、可压缩解释和段落气口的上游契约
- 本节要回答什么问题
- 本节必须交付什么：例子、提示词、表格、清单、代码或判断
- 本节有哪些素材：事实、案例、来源、用户讨论、术语
- 本节不能做什么：新增主张、提前解释后文、空泛铺垫
- 本节的读者卡点是什么

Do not print this working brief. Use it to write the section.

## Long Logic Drafting

Do not solve "long logic" by making every sentence long. Use simple wording, and match reasoning depth to the section.

- Use `light` depth for openings, definitions, transitions, summaries, tables, and checklists: give the usable point and move on.
- Use `medium` depth for mechanism, boundary, and method sections: keep the causal step that makes the judgment usable, but avoid proving every side point.
- Use `deep` depth only for core disputes or key judgments where the reader would otherwise not trust the conclusion.
- A deep paragraph may contain premise, causal step, boundary, and operational landing in one natural paragraph; light and medium sections do not need all four parts.
- Draft in a form that is easy to compress: mark repeated explanation as compressible in the controller output instead of making every paragraph final-polished.
- If three adjacent paragraphs are only short judgments and the section is medium/deep, combine them or add the missing causal step; if the section is light, prefer one direct paragraph or a table/list.
- Do not split one required causal chain into many short standalone statements just to reduce AI-like phrasing.
- A paragraph can be longer without becoming verbose only when it keeps answering the same question and the section depth justifies it.
- Avoid meta teaching narration such as "this logic is...", "the focus changes...", "templates are valuable but...", or "do not rush to...". Prefer a direct action, concrete scene, consequence, boundary, or standard.

## Rhythm Variation

The draft should not sound as if every paragraph was generated from the same template.

- 用短句给判断，用长句解释复杂关系。
- 不要连续使用同一种段落开头，例如“这意味着”“如果”“所以”“问题在于”“你会发现”。
- 不要连续使用同一种推进公式，例如“现象 -> 解释 -> 小结”在相邻段落里反复出现。
- 每个写作单元里至少出现一种节奏变化：例子、表格、提示词块、检查清单、短判断或追问。
- 短句不能堆成口号，长句不能堆成说明书。
- 如果一句话删掉后不减少判断、例子、动作、口径或边界，不要写。

## Term Collection (Required)

While writing each package, collect technical terms a beginner reader would not know.
Write them to `skills/article-director/outputs/{topic_id}/memory/term-registry.json` using this format:

```json
{
  "topic_id": "{topic_id}",
  "terms": [
    {"term": "术语名", "definition": "一句话解释，面向小白，不超过30字"}
  ]
}
```

Rules:
- only collect terms that appear in the current package's content
- only terms that would block a beginner's understanding if undefined
- do not collect terms already explained inline in the body text
- append to existing terms, do not overwrite the file

## Additional Constraints

- do not dump term definitions up front
- do not output meta-talk such as ???????????????? or ???????????...?
- papers and open-source projects are support material, not the main narrative spine
- leave clear semantic boundaries for `primer-writer`, `deep-dive-researcher`, `structure-editor`, and `narrative-smoother`
- do not insert inline appendix-style labels such as `术语解释：...`
- do not pack references, glossary, or one-line source notes into the body; those belong to appendix handling
- do not scatter hanging citations after paragraphs; keep source handling clean for later passes
- do not sacrifice natural prose just to pre-format everything early

## Strategy Awareness

If the workflow profile is `teaching-playbook`:

- your primary job is to help the reader reproduce or operationalize the route, not to write a detached concept essay
- explain only the concepts that block execution, route choice, or troubleshooting
- important steps should make these fields legible when needed:
  - 目标
  - 前提
  - 操作
  - 预期结果
  - 失败现象
  - 排查
  - 下一步
- do not force multiple different validation goals into one step
- do not mechanically split tiny actions that belong to one execution scene into separate pseudo-steps
