# 蛙客成 · pipeline/pipeline
> 帮我看一下销售管道，哪些商机停滞了、加权预测多少 

**结论**：next=工件通过全部门禁，可进入授权与交接

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 8/8 项 |
| next | **工件通过全部门禁，可进入授权与交接** | 输出字段 |
| opp_count | **4** | 输出字段 |
| stage_count | **4** | 输出字段 |

## 1. opp_count
> opp_count 的判定与证据是什么？

- **opp_count：**4

## 2. stage_count
> stage_count 的判定与证据是什么？

- **stage_count：**4

## 3. open_count
> open_count 的判定与证据是什么？

- **open_count：**4

## 4. weighted_value
> weighted_value 的判定与证据是什么？

- **weighted_value：**890,000.00

## 5. stale_count
> stale_count 的判定与证据是什么？

- **stale_count：**0

## 6. concentration_hhi
> concentration_hhi 的判定与证据是什么？

- **concentration_hhi：**0.42

## 7. stage_distribution
> stage_distribution 的判定与证据是什么？

- {'NEW': 0, 'SCREENING': 1, 'MEETING': 1, 'PROPOSAL': 1, 'NEGOTIATION': 1, 'WON': 0, 'LOST': 0}

## 8. top_accounts
> top_accounts 的判定与证据是什么？

| company | amount |
|---|---|
| 云启科技 | 900,000.00 |
| 晨星零售 | 450,000.00 |
| 山海物流 | 250,000.00 |

## 9. narrative
> narrative 的判定与证据是什么？

- **narrative：**开放商机 4 条、加权管道值 890000.0、停滞 0 条、客户集中度 HHI=0.4199

## 10. capability_status
> capability_status 的判定与证据是什么？

- **capability_status：**real

## 11. capability_evidence
> capability_evidence 的判定与证据是什么？

- **capability_evidence：**local records inspected

## 口径与边界

- **来源：**技能 pipeline/pipeline 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
