# 11 · 经验 RAG 规则：检索、应用与写回

> 服务 R07 G `pm_workflows/experience.py`。经验卡不是「语录库」，而是有边界与时效的判据。

## 1. 来源

- 升级方案 §10.3：`pm/experience/RAG_RULES.md`、`RAG_MODEL.md` →
  `core/prompt_kernel/experience_gate.py` 方向；本仓先落在 `pm_workflows/experience.py`。
- 公开方法：RAG 的 retrieve → rerank → apply 三段；冲突消解按可信度与时效；
  状态机式知识治理（candidate / validated / observed / superseded）。
- 本仓存量：`skills/s08_decision.py` 的经验卡五要素（trigger/scope/rule/boundary/source_credibility）
  只校验「卡格式」，本门补齐「检索与应用」。

## 2. 三档检索

| 档 | 行为 | 输出 | 门禁 |
|---|---|---|---|
| L0 | 不检索 | 空 | cards 必须为空 |
| L1 | 只读索引 | index（id/title/scope/updated_at） | 不返回规则正文 |
| L2 | 3–5 张卡 | cards（含 rule/evidence/boundary） | 逐张检查范围/可信度/时效/证据/边界 |

## 3. 应用前五查

1. **范围**：卡 scope 必须与当前 query 匹配（或为 `*`）；
2. **可信度**：low 可信度的卡只有 `candidate` 状态可参考，不得直接应用；
3. **时效**：`updated_at` 距今 ≤365 天（以输入 `as_of` 为准，保证可复算）；
4. **证据**：evidence 非空，能指向实验/访谈/工单；
5. **边界**：boundary 非空，写清「不适用什么场景」。

## 4. 冲突优先级

同一 trigger 下多张卡：

```
validated > observed > candidate > superseded
```

- 高优先级胜出，其余标记 shadowed 不应用；
- 同优先级但 rule 不同 → 判为不可解析冲突，门禁 FAIL，必须人工裁决。

## 5. 写回状态机

```
candidate → validated / observed / superseded
validated → observed / superseded
observed  → superseded
superseded 终态
```

写回必须带 `card_id / from / to`，且 `from` 与卡片当前状态一致；非法迁移直接阻断。

## 6. 适用边界

- 适用：重复出现的引导/定价/指标口径/交付流程经验。
- 不适用：一次性的项目事实、未验证的个人偏好、与当前 query 无关的历史事故。
- 经验门不替代数据证据；L2 卡也只能作为「先验」，最终仍要当前实验验证。

## 7. 误用反例

| 误用 | 表现 | 本仓拦截 |
|---|---|---|
| 无限堆卡 | 一次返回 8 张 | `experience.cards`（3~5 上限） |
| 低可信度直接用 | credibility=low 且 status=validated | `experience.credibility` |
| 用过时经验 | updated_at 早于 365 天 | `experience.recency` |
| 同级冲突不裁决 | 两张 validated 规则相反 | `experience.conflict` |
| 跳跃写回 | candidate → 直接 superseded 之外乱跳 | `experience.writeback`（状态机） |
