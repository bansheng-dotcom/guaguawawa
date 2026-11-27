# R05 黄金成品（golden）

三份 HTML 不是手写稿，全部由研究链跑真实夹具后导出，可复现：

```bash
cd r05-washenyuan-research
python -m research_chain.build_golden
```

| 文件 | 内容 | 硬指标 |
|---|---|---|
| `industry-research.html` | 行业研究报告：结论先行、市场测算、竞争格局、证据附录、矛盾与边界 | 34 条证据 / 23 个独立来源；每条结论可追 source id |
| `competitor-matrix.html` | 竞品分析：5 家 × 8 维矩阵 + battlecard + 五力 + 份额 | 40 格全部有 source id；份额合计 68% |
| `market-sizing.html` | 市场测算：top-down × bottom-up × p10/p50/p90 + 假设清单 | 双口径 87.00 / 87.05 亿元，差异 <1%；每条假设挂 evidence_id |

夹具：`fixtures/pet_smart_hardware.json`（确定性、无联网）。

生成时链上 8 段门禁全部 PASS，跨段一致 7 项全部 PASS：

- `cross:conclusion_sources_exist`：结论引用的 source 都在证据台账；
- `cross:cell_sources_exist`：40 个矩阵格子的 source 都在源地图；
- `cross:market_size_consistency`：竞争格局规模 87.00 与 size p50 88.17 偏差 1.3% ≤5%；
- `cross:shares_sum`：5 家份额为正且合计 ≤100%；
- `cross:assumption_evidence`：4 条测算假设都能回到台账证据；
- `cross:subquestion_coverage`：6 个子问题均有证据；
- `cross:report_traceability`：报告结论来源与台账一致。

复核方式：`python agent.py chain audit --out-dir artifacts/chain`（先跑一次 `chain run`）。
审计会重算每个工件的 sha256 与全部门禁，文件被手改会直接 FAIL。
