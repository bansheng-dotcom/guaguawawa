# regression-gate · 取舍与优先级规则

## 判定顺序（先到先裁）

1. **回归证据优先于一切**：fail-before 与 pass-after 必须都为 true，否则直接 BLOCK，
   不进入裁决讨论。
2. **既有测试不回退是底线**：existing_green=false 一律 BLOCK。
3. **PASS 必须挂回归报告**：verdict=PASS 而 regression_id 为空 → BLOCK。
4. **证据链非空**：evidence 为空 → BLOCK/拒收。
5. **主观结论零容忍**：出现「效果不错/应该没问题/主观感觉/凭经验判断」等词且未声明
   handoff → fake_pass 红线，退回补评估证据。

## 裁决语义

- PASS：证据齐全，可交 R09 做发布准备。
- BLOCK：存在阻断性缺陷（回归失败/测试回退/证据缺失），退回修复。
- NEEDS_REVIEW：证据不全但无硬缺陷，交人工复核。

## 边界

- R19 只产出发布候选工件与证据链；**实际部署、灰度、流量切分交 R09 + 人工**。
- 「该不该上线」的业务判断交 R06，R19 只保证回归与证据齐备。
