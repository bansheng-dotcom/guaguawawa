# 风格资产输出契约

## 输出目标

文风解析的产物必须能被下一个 agent 直接使用。不要只输出读后感或内容摘要。

## 标准结构

```yaml
style_name:
source_scope:
confidence:
style_profile:
reasoning_pattern:
argument_pattern:
language_bank:
paragraph_rhythm:
cognitive_pattern:
anti_patterns:
reuse_prompt_contract:
review_rubric:
evidence_map:
```

## 字段说明

### style_profile

概括这个文风适合什么内容、有什么总体气质、核心价值是什么。

### reasoning_pattern

说明结论如何得出：

- 从什么问题进入。
- 如何排除误区。
- 如何使用证据。
- 如何得出阶段性判断。
- 如何落到行动或边界。

### argument_pattern

说明文章如何论述：

- 开篇方式。
- 推进顺序。
- 转折位置。
- 收束方式。

### language_bank

按功能给出常用表达：

- 判断句。
- 转折句。
- 解释句。
- 推进句。
- 边界句。
- 收束句。

每条表达都必须说明使用场景，不能只列短语。

### paragraph_rhythm

说明段落节奏：

- 平均段落长度倾向。
- 短段用途。
- 长段用途。
- 段内常见结构。
- 何时单独成段。

### cognitive_pattern

说明作者认知方式：

- 看问题先看什么。
- 反对什么。
- 如何处理复杂性。
- 如何把知识转成行动。

### anti_patterns

列出不像该风格的写法，并说明为什么不像。

### reuse_prompt_contract

给下游 agent 的硬约束，例如：

```text
写作时必须先明确真实问题和常见误区，再给作者判断。
每个核心结论都要包含证据、业务解释、可干预动作和边界。
禁止只用“优化、提升、加强、赋能”等空泛建议收尾。
```

### review_rubric

给审稿 agent 的检查项。每项要能判断通过或不通过。

### evidence_map

列出支撑这些规则的样本来源。可以是文件名、段落编号或短摘录。

## 最小输出

如果用户只要求快速拆解，至少输出：

```yaml
style_name:
top_rules:
language_bank:
paragraph_rhythm:
anti_patterns:
reuse_prompt_contract:
```

