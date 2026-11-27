# shared/engines —— 全角色共享引擎

## 为什么有这一层

方案 T0 原假设“9 类通用引擎是 143 份重复实现”。2026-11-27 实测后发现：

- 143 个同名文件**没有一个字节级重复**；
- 同名副本相似度最高 0.973（telemetry_watchdog），多数在 0.33–0.94；
- 差异主要是角色领域语义（供应链/人事/增长/审查的术语、规则、状态字段）。

直接合并成一份实现会改变角色行为，属于重构而不是去重。因此 T0 分两步：

1. **能合的先合**：telemetry_watchdog 的 r11/r12 两个近似副本已收敛到这里，
   角色侧只留薄适配器；
2. **其余登记冻结**：`configs/engine_variants.json` 记录 143 个文件的哈希与状态，
   `scripts/check_engine_variants.py --check` 阻止新增未登记副本与近似副本。

## 接入规则

```python
# 角色 engines/telemetry_watchdog.py（薄适配器）
from shared.engines.telemetry_watchdog import ContentTelemetryWatchdog  # noqa: F401
```

- 能复用 → 直接从 `shared.engines.<name>` 导入；
- 确需角色差异 → 写适配器（别名/子类），不要复制整份实现；
- 新增/修改角色引擎 → 运行 `python scripts/check_engine_variants.py --write`
  更新台账，再提交。

## 台账

- 文件：`configs/engine_variants.json`
- 报表：`docs/ENGINE-LEDGER.md`
- 门禁：`python scripts/check_engine_variants.py --check`

## 后续

逐引擎合并需要 owner 单独立项（先补角色黄金样本与回归，再动实现）。
在合并前，台账保证“不会再多出第 144 份副本”。
