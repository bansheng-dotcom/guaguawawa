# 咨询工作簿 · FRUIT-01

- 客户：蛙蛙呱呱生鲜
- 决策：是否在赤峰做苹果产地直采，12 个月内把单公斤成本降 8%
- partner：r01 / lead：r05
- 截止：2026-12-31

| 阶段 | 名称 | 状态 | 签字 |
|---|---|---|---|
| 1 | 定义问题 | done | r01 |
| 2 | 逻辑地图 | done | r01 |
| 3 | 80/20 聚焦 | done | r01 |
| 4 | 分析计划 | done | r01 |
| 5 | 执行分析 | done | r01 |
| 6 | 整合答案 | done | r01 |
| 7 | 形成建议 | done | r01 |
| 8 | 打包交付 | done | r01 |

## 各阶段产物

### 阶段 1 · 定义问题
```json
{
 "decision": "是否在赤峰做苹果产地直采，12 个月内把单公斤成本降 8%",
 "decision_maker": "创始人（R01）",
 "success_metric": "单公斤总成本 ≤6.12 元、损耗 ≤5%、投资回收 ≤1 年",
 "scope_out": "不做全国调拨、不做自有品牌、不影响现有批发客户"
}
```
### 阶段 2 · 逻辑地图
```json
{
 "branches": [
  {
   "name": "经济性",
   "question": "直采能否降本",
   "hypothesis": "有效成本比现采低 ≥10%",
   "data": "R15 TCO + 成本卡",
   "method": "TCO 对比 + 三情景",
   "falsifier": "损耗 >10% 连续两周"
  },
  {
   "name": "供给",
   "question": "产地能否稳定供货",
   "hypothesis": "周 2 车、到货率 ≥95%",
   "data": "合作社产能 + 到货记录",
   "method": "产能核对 + 履约统计",
   "falsifier": "到货率 <80%"
  },
  {
   "name": "渠道",
   "question": "门店/档口能否消化",
   "hypothesis": "动销 ≥85%、周转 ≤7 天",
   "data": "POS/档口出货",
   "method": "动销测算",
   "falsifier": "连续 2 周动销 <75%"
  },
  {
   "name": "风险",
   "question": "断供/质量/价格风险",
   "hypothesis": "断供可 1 周内切换",
   "data": "供应商备选 + 期货",
   "method": "风险矩阵 + 情景",
   "falsifier": "断供 >1 周"
  }
 ],
 "critical_branch": "经济性"
}
```
### 阶段 3 · 80/20 聚焦
```json
{
 "focus": [
  "经济性",
  "供给"
 ],
 "excluded_reasons": {
  "渠道": "现有 POS 已能验证动销，暂不单独立项",
  "风险": "先做小批试点即可暴露，不前置建模"
 }
}
```
### 阶段 4 · 分析计划
```json
{
 "workstreams": [
  {
   "name": "TCO 对比",
   "data_source": "三家报价 + 运价",
   "method": "TCO",
   "owner": "r15",
   "output": "有效单位成本",
   "fallback": "人工报价 + 行业区间"
  },
  {
   "name": "损耗与温控",
   "data_source": "温控记录",
   "method": "损耗核算",
   "owner": "r06",
   "output": "损耗率区间",
   "fallback": "行业 5—10% 区间"
  },
  {
   "name": "规格匹配",
   "data_source": "新发地分规格",
   "method": "同日分规格对照",
   "owner": "r05",
   "output": "规格价差",
   "fallback": "单日点估计"
  },
  {
   "name": "同期基线",
   "data_source": "2022—2025 农业农村部",
   "method": "同期均值对照",
   "owner": "r05",
   "output": "同比与偏离",
   "fallback": "仅与 2025 对比"
  }
 ]
}
```
### 阶段 5 · 执行分析
```json
{
 "findings": [
  {
   "claim": "赤峰直采有效单位成本 5.23 元/公斤，比呼市现采 8.92 低 41.4%",
   "evidence": "R15 TCO 门禁（S15 报价）",
   "confidence": "A",
   "falsifier": "首批到货损耗 >10%"
  },
  {
   "claim": "省内 8.00 元价差中 64.4% 是规格（5.15 元），同规格区域溢价仅 3.09 元（28%—36%）",
   "evidence": "新发地同日分规格（S5）",
   "confidence": "B",
   "falsifier": "匹配后差 <1 元"
  },
  {
   "claim": "2026 年 10—11 月比 2025 低 5.11%、比 2024 低 8.37%，回到 2022—2023 区间",
   "evidence": "农业农村部 2022—2026 同期（S1）",
   "confidence": "A",
   "falsifier": "窗口口径调整后差异消失"
  },
  {
   "claim": "Φ70-84 报价 73 个交易日恒为 7.60，单日同比不可用",
   "evidence": "新发地 2026 窗口（S5）",
   "confidence": "A",
   "falsifier": "换源后价格有变动"
  },
  {
   "claim": "损耗 8%→5% 可省 0.22 元/公斤，是仅次于去批发的第二收益",
   "evidence": "成本卡敏感性（C 级假设）",
   "confidence": "C",
   "falsifier": "实测损耗不降"
  }
 ],
 "conflicts": [
  {
   "item": "东瓦窑富士 14.00 vs 呼市苹果零售 13.88",
   "reason": "规格/等级不同，不作批零倒挂结论"
  }
 ],
 "gaps": [
  {
   "item": "冷链运价/冷库租金",
   "impact": "成本卡 C 级",
   "fix": "接 2 个来源升 B"
  },
  {
   "item": "门店 POS 动销",
   "impact": "渠道假设",
   "fix": "接内部库或导 CSV"
  }
 ]
}
```
### 阶段 6 · 整合答案
```json
{
 "messages": [
  {
   "message": "直采能降本，但赚的是「去一道批发 + 控损耗」，不是「区域价差」",
   "mechanism": "TCO 5.23 vs 8.92；规格差占价差 64%，同规格区域溢价仅 3.09",
   "competing_explanations": [
    "价格下行带来的账面改善",
    "规模效应而非直采"
   ]
  },
  {
   "message": "2026 是低位年，采购应锁量不锁价",
   "mechanism": "同比 -5.11%、AP0 36 日 -19.27%，期货贴水",
   "competing_explanations": [
    "局部产区减产",
    "消费短期波动"
   ]
  }
 ]
}
```
### 阶段 7 · 形成建议
```json
{
 "options": [
  {
   "name": "全量直采",
   "economics": "降 0.62 元/公斤、年省 93 万",
   "risks": "断供/损耗",
   "preconditions": "合作社产能 ≥3000 吨、双源"
  },
  {
   "name": "试点直采（推荐）",
   "economics": "降 0.3—0.4 元/公斤、投入 70 万",
   "risks": "装载率不足",
   "preconditions": "2 车/周、损耗 ≤8%"
  },
  {
   "name": "维持现采",
   "economics": "0",
   "risks": "成本不动、毛利被压缩",
   "preconditions": "无"
  }
 ],
 "recommendation": {
  "choice": "试点直采",
  "owner": "r15",
  "kpi": "损耗 ≤8%、到店 ≤48h、单公斤成本 ≤6.12 元",
  "rollback": "连续 2 周损耗 >10% 或装载率 <70%，回现采"
 }
}
```
### 阶段 8 · 打包交付
```json
{
 "deliverables": {
  "summary": "一页纸执行摘要（结论先行）",
  "main": "直采试点建议书（含 TCO/规格/基线）",
  "appendix": "全量证据台账 + 缺口清单 + 复盘"
 },
 "value_tracking": {
  "baseline": "6.74 元/公斤（现采落地）",
  "target": "6.12 元/公斤",
  "metric": "单公斤总成本（同规格同城）",
  "review_date": "2027-01-31"
 }
}
```
