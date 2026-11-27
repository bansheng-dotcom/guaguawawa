---
name: article-popular-science-writer
description: "Plan, research, draft, and review knowledge-popularization articles for ZSXQ or similar communities. Use when Codex needs to turn a topic into a source-backed Chinese article through a staged workflow: knowledge architecture, outline, detailed outline, evidence filling, term explanation, drafting, code checks, and review."
---

# Article Popular Science Writer

Use this skill for article tasks that need both research rigor and publishable prose.

## Workflow

Follow the six-stage pipeline defined in [agents/article-writer.md](../../../agents/article-writer.md):

1. Build the topic knowledge architecture first
2. Draft the high-level outline
3. Expand it into a detailed outline
4. Fill evidence item by item
5. Inject term explanations only where needed
6. Assemble the article, run code checks, then review

Do not skip directly from topic to full article unless the user explicitly asks for a quick draft.

## Required Companions

- Load skills/topic-knowledge-architecture/SKILL.md before phase 1 (位于原项目 `D:\知识库\projects\知识星球自动更新-AI社群\skills\topic-knowledge-architecture\SKILL.md`)
- Load [agents/researcher.md](../../../agents/researcher.md) when doing evidence filling
- Load [agents/reviewer.md](../../../agents/reviewer.md) when reviewing a draft

## Standard Files

Write intermediate outputs to:

- `tmp/{id}-outline.md`
- `tmp/{id}-detailed-outline.md`
- `tmp/{id}-draft.md`
- `state/reviews/{id}.json`

If an older run uses numbered files such as `01-选题+大纲.md`, keep the mapping explicit and normalize before archiving.

## Deterministic Checks

Before calling the article ready:

```powershell
python D:\知识库\projects\知识星球自动更新-AI社群\scripts\check_article.py tmp/{id}-draft.md
```

The article cannot be considered complete if that script fails.

## Do Not

- Do not fabricate evidence when research is incomplete
- Do not add new arguments during drafting
- Do not publish automatically
- Do not leave the workflow only in chat without writing files
