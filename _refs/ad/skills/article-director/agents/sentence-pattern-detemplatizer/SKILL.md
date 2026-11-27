---
name: sentence-pattern-detemplatizer
description: "Deprecated compatibility entry for legacy article-director references. Sentence-pattern de-templatizing has moved to D:\\知识库\\skills\\内容生产\\ai-tone-director. Use ai-tone-director audit/repair-plan/rewrite modes instead."
---

# Deprecated: Sentence Pattern Detemplatizer

本节点不再保存句式家族规则、案例或修订方法。

唯一事实源已迁移到：

- `D:\知识库\skills\内容生产\ai-tone-director\SKILL.md`
- `D:\知识库\skills\内容生产\ai-tone-director\memory\experience-rules.md`
- `D:\知识库\skills\内容生产\ai-tone-director\workflows\article-director-integration.md`
- `D:\知识库\skills\内容生产\ai-tone-director\scripts\scan_ai_tone.py`

## 兼容调用方式

旧 workflow 如果仍引用本节点，应立即转为：

1. 读取 `ai-tone-director`。
2. 用 `audit` 模式输出 `ai-tone-audit.json`。
3. 用 `repair-plan` 模式输出 `ai-tone-repair-plan.md`。
4. 需要改写时用 `rewrite` 模式输出 revised Markdown。

本文件不再作为独立规则库使用。

