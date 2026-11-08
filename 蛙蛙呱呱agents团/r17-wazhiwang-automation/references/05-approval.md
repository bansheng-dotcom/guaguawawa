# 参考层 05 —— 人工审批节点（publishing / progressive-building）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/legal/skills/signature-request/SKILL.md
>


> 来源：n8n-io__n8n `packages/@n8n/instance-ai/skills/publishing` +
> `progressive-building`
> 角色：R17 蛙织网 · S05 approval 的确定性口径来源。

## 第一层 · 方法论

自动化的力量与风险同源：**能自动做的事，也能自动做错事**。n8n 的立场是
「progressive / HITL」——高风险动作必须有人类在环（human-in-the-loop）：

1. **发布不是默认动作**：工作流创建后处于 draft，**发布**（deploy/activate）是
   一个需要**显式请求**的动作。测试不需要发布，n8n 官方铁律是「never publish
   just to test」。
2. **高风险动作前置审批**：退款、删除、扣款、合同签署、发送 PII、wire transfer
   等，必须先有人审批（HITL 卡片 / approval node）。
3. **发布前 evidence**：发布前应有 live run 证据；若有节点未被触达（unreached）
   或被模拟（simulated），必须**显式披露**（verification disclosure），不能装作
   全绿。
4. **错误工作流先发布再指派**：`errorWorkflow` 若未发布，挂载时会绑到一个
   draft，运行时才发现错误流没生效——所以 publish-before-assign。

## 第二层 · 可执行口径（判据 | 口径 | 取值来源）

| 判据 | 口径 | 取值来源 |
|---|---|---|
| 风险等级 | low/medium/high/critical | n8n risk_level |
| 高危动作 | publish/deploy/refund/delete/drop/payout/contract_sign/send_pii/wire_transfer/revoke_access | n8n 高危动作集 |
| 审批要求 | high/critical 或命中高危动作 → 必须有 approver/authorization | HITL |
| 发布门禁 | publish_requested 或 has_live_run_evidence | publishing skill |
| 未验证披露 | 有 unreached/simulated 且未 acknowledge → 拦截 | progressive-building |
| 错误流 | uses_error_workflow → error_workflow_published=True | publish-before-assign |

## 第三层 · 已验证算例

**干净审批**：
```
approvals=[{action: email_notify, risk_level: low},
           {action: publish, risk_level: high, approver: biz-owner@acme.com, authorization: 审批单#123}]
```
门禁：`publish` 高危但已声明 approver + authorization → PASS，`high_risk_count=1`。

**脏审批**：
```
approvals=[{action: refund, risk_level: critical}]   # 无 approver/authorization
```
门禁：`高危动作 refund 有审批人/授权（缺 ['refund']）` → FAIL。

**脏发布**：
```
publish.json: publish_requested=True, has_live_run_evidence=False,
              nodes_unreached=["Create Lead"], acknowledge_unverified 缺省
```
门禁：`存在未验证节点但未披露 acknowledge` → FAIL。

## 第四层 · 实战踩坑

1. **`publish_requested` 与 `has_live_run_evidence` 是「或」关系**：用户显式要求
   发布，或已有 live run 证据，二者满足其一即可过发布门禁；两者都无才拦。
2. **高风险判定是「动作 ∈ 高危集」或「等级 ∈ {high,critical}」的并集**：一个
   `risk_level=low` 但 `action=refund` 的节点仍然高危，别只看等级。
3. **未验证披露是「有未验证 且 未 ack」才拦**：如果 unreached 为空、simulated
   为假，即使没 ack 也放行（没东西要披露）。
4. **错误流门禁只在 `uses_error_workflow=True` 时生效**：不涉错误流的工作流不该
   被 publish-before-assign 规则误伤。
