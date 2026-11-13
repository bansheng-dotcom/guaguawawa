# R01 蛙全局 · CEO 治理与决策规范账本 (EXECUTIVE_GOVERNANCE_SPEC)

> 版本：v1.0 (工业级规范)  
> 适用：R01 蛙全局决策中枢及全矩阵 20 角色治理红线约束。  
> 标杆对齐：awesome-design-md (126k+) & 治理架构标准。

---

## 1. 核心治理硬性阈值 (Governance Constants)

```json
{
  "FREEZE_DAYS_PRICING": 60,
  "FREEZE_DAYS_FUNDING": 30,
  "FREEZE_DAYS_PIVOT": 90,
  "FREEZE_DAYS_LAYOFFS": 30,
  "SCORECARD_METRICS_MIN": 5,
  "SCORECARD_METRICS_MAX": 15,
  "ESCALATION_COST_THRESHOLD_MONTHS": 6,
  "DEFAULT_MAX_RETRIES": 3
}
```

## 2. 决策治理三大黄金法则 (The Three Golden Rules)

1. **不可逆性锁定法则 (Reversibility Lock)**：
   - 凡涉及资金沉没、客户定价调整、核心技术架构弃用或裁员，必须定义清晰的 **回滚方案 (Rollback Plan)** 与成本承受极限。
   - 不可逆且撤回成本 $\ge 6$ 个月的决策，必须人工签名审批 (Human Sign-off)。
2. **熔断与杀死标准法则 (Kill Criteria)**：
   - 任何战略立项与实验必须白纸黑字写明 **杀死标准 (Kill Criteria)**。
   - 达到负向阈值必须无条件终止，杜绝沉没成本谬误 (Sunk Cost Fallacy)。
3. **单一责任人与事后留痕 (Single DRI & Decision Log)**：
   - 每个决策卡只允许一个最终决策 DRI (Directly Responsible Individual)。
   - 禁止复述决策作为理由，理由必须基于反方质询 (Devil's Advocate) 后的可验证逻辑。
   - 标明 `DO_NOT_RESURFACE` 的被否提案，在同一治理周期内严禁再次提议，除非具备全新环境突破证据。

## 3. 反伪影与空话套话治理红线 (Anti-Slop Prohibited Phrases)

- 严禁出现以下无 DRI、无指标、无时间截点的伪决策套话：
  - ❌ “逐步推进” / “尽快落实” / “进一步优化”
  - ❌ “加强各部门协同” / “高度重视并积极研究”
  - ❌ “原则上同意，后续细化”
- 必须替换为具体 DRI、完成日期与量化交付验收标准。
