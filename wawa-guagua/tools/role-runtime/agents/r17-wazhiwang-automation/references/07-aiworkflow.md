# 参考层 07 —— AI 工作流接入（intent-recognition / model-selection）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/small-business/skills/build-agent/SKILL.md
>


> 来源：n8n-io__n8n `packages/@n8n/instance-ai/skills/intent-recognition` +
> `model-selection`
> 角色：R17 蛙织网 · S07 aiworkflow 的确定性口径来源。

## 第一层 · 方法论

把 AI 接进自动化，n8n 的核心区分是**意图锚点**（intent anchor）：

- **workflow-anchored（工作流锚定）**：任务目标固定，流程是确定性管道，AI 只做
  其中的一步（如字段抽取、分类）。适合可预测、可评估的任务。
- **agent-anchored（Agent 锚定）**：目标开放，需要 AI 动态决策（选择工具、多步
  推理）。适合探索性任务，但必须配**工具**（tools）和**护栏**（guardrails）。

无论哪种锚点，两条铁律：

1. **模型显式声明**：不允许「默认模型」隐式兜底——模型不同，输出质量与成本
   差异巨大，必须显式写 `model`。
2. **输入输出有记录**：AI 节点的输入输出要可回放、可评估（io_record /
   evaluation），否则出了问题无法追溯「模型当时看到了什么」。

## 第二层 · 可执行口径（判据 | 口径 | 取值来源）

| 判据 | 口径 | 取值来源 |
|---|---|---|
| 锚点 | agent / workflow 二选一 | intent-recognition |
| 模型显式 | model 非空，无默认兜底 | model-selection |
| 用途显式 | purpose 非空 | model-selection |
| 节点类型 | aiAgent/chainLlm/basicChainLlm/toolCode/toolHttpRequest/lmChatOpenAi | n8n AI 节点 |
| agent 护栏 | anchor=agent → 必须有 tools 且 guardrails | agent-anchored |
| 输入输出记录 | io_record 或 evaluation | n8n 可评估性 |
| 高风险权限 | risk_level=high → 必须有 permission | n8n 权限边界 |

## 第三层 · 已验证算例

**干净 AI 节点**：
```
ai_nodes=[{name: Classify Intent, type: aiAgent, model: claude-sonnet-5,
           purpose: 意图分类, risk_level: low}], io_record=True
```
门禁：节点类型白名单 + model 显式 + purpose 显式 + io_record → PASS。

**脏 AI 节点**：
```
ai_nodes=[{name: Classify, type: aiAgent, purpose: 分类}]   # 无 model
```
门禁：`每个 AI 节点显式声明 model（缺 ['Classify']）` → FAIL。

**干净模型选择**：
```
anchor=workflow, model=claude-sonnet-5, purpose=字段抽取
```
门禁：workflow 锚点 + 模型显式 → PASS。

**脏模型选择**：
```
anchor=agent, model=claude-sonnet-5, purpose=动态决策   # 无 tools/guardrails
```
门禁：`agent 锚点声明 tools 与 guardrails` → FAIL。

## 第四层 · 实战踩坑

1. **agent 锚点必须双护栏**：`tools` 和 `guardrails` 二者都缺才拦，只写一个也
   是 fail——agent 有工具没护栏 = 失控，有护栏没工具 = 空转。
2. **workflow 锚点不强制护栏**：固定管道里 AI 只做一步，不需要 agent 的 tools/
   guardrails，别一刀切。
3. **节点类型别用前缀匹配**：`lmChatOpenAi`、`chainLlm` 大小写混合，白名单要
   精确，不能 `lower().startswith("ai")`。
4. **模型显式 ≠ 模型名合法**：R17 只校验「是否显式声明」，不校验模型名是否在
   供应商目录里（那是模型注册表的职责）。
