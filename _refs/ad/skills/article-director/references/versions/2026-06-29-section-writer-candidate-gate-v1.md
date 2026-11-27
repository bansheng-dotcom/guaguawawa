# 2026-06-29 section-writer candidate gate v1

## Change

Add an internal candidate-selection pass to `section-writer`.

The workflow graph stays unchanged:

```text
section-writer -> review fan-out -> paragraph-rewrite-designer -> section-rewriter
```

`section-writer` still outputs one Markdown section. The multi-candidate logic is internal to the writer.

## Why

Single-shot drafting lets the first version pull the section into common model expression tracks. Later review can repair obvious problems, but it is still revising around the first draft's wording.

The new writer contract makes the writer generate multiple expression candidates for each semantic unit, delete public-track failures deterministically, score the remaining candidates, and select one before downstream review.

## Rules

- Candidate units follow detailed-outline semantic units, not single sentences.
- Content skeleton is locked before candidate generation.
- Candidate variation is mainly expression: rhythm, work-object placement, natural grain, author judgment, abstraction density.
- Public-track failures are deleted before scoring.
- Scored candidates below threshold are deleted.
- If fewer than 2 candidates remain, regenerate using failure reasons.
- Regeneration is capped at 3 rounds per unit.
- Downstream agents receive only one final draft.

## Thresholds

Public-track deletion is deterministic and not a score.

Judge threshold:

- total score must be at least 85
- `meaning_preservation >= 22`
- `public_track_escape >= 16`
- `concrete_work_object >= 11`
- `natural_expression_grain >= 11`
- `author_judgment >= 7`
- `section_connection >= 7`
- `rhythm_control >= 3`

## Validation

Manual test artifacts:

- `tmp/7-05-opening-writer-candidate-test-20260629.md`
- `tmp/7-05-opening-writer-candidate-selected-20260629.md`
- `tmp/7-05-opening-schema-definition-candidate-test-20260629.md`
- `tmp/7-05-opening-schema-definition-selected-20260629.md`

Commands:

```powershell
python D:\知识库\skills\内容生产\ai-tone-director\scripts\scan_ai_tone.py tmp\7-05-opening-schema-definition-selected-20260629.md
rg -n "首先|其次|再次|最后|总之|总的来说|综上所述|总而言之|因此|所以|于是|作为一个|来说|关键是|本质上|真正|更稳定|继续往下走|不是.+而是|不在于.+而在于|不应该.+应该|问题在于|问题出在|可以看到|你会发现|不难发现|最常见|最容易|值得注意的是|由此可见|简单来说|说白了|换个角度看|可以这样理解|能接住|先看" tmp\7-05-opening-schema-definition-selected-20260629.md
```

Both selected-output checks passed after final deterministic regression.

## Rollback

Restore `agents/section-writer/SKILL.md` to the previous contract that only used reader-use-contract and 2-3 short decision rounds.
