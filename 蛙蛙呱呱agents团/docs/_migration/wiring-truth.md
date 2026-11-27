# 接线真相表

> 由 `python scripts/wiring_truth.py --write` 生成，禁止手改。
> LIVE=非测试代码 import 或 core.X 调用；TEST_ONLY=只有测试；DOC_ONLY=只有文档；UNWIRED=都没有。

## 汇总

| 状态 | 数量 |
|---|---:|
| LIVE | 31 |
| TEST_ONLY | 0 |
| DOC_ONLY | 0 |
| UNWIRED | 0 |
| DOC_DEAD | 0 |

## 未接线（0）

无。

## 只有测试引用（0）

无。

## 只有文档提及（0）

无。

## 文档死链（0）

无。

## 职责登记（F7）

| 职责 | 唯一模块 |
|---|---|
| 正文契约 | `core.prose.prose_contract` |
| 正文生成 | `core.prose.prose_render` |
| 拆卡 | `core.cards.pipeline` |
| ClaimCard 契约 | `core.claims.contract` |
