> status: ARCHIVED · 2026-11-27 · 现行规则见 docs/README.md

# CONTRACTS · 数据与图表契约（P6）

> 唯一的「一行数据」定义在 `core/data/data_standard.py`。本文只列字段与最小样例，
> 校验函数返回人类可读错误清单（空 = 合法），不抛异常、不写盘、不调模型。

## 1. 四份契约

```text
L0 Source      采集规格：url / policy / extract schema（configs/collections、configs/policies）
L1 Record      原始记录：抓到了什么，原样留档（不可变）
L2 Observation 清洗后指标：全链路唯一可比较单元
L3 Dataset     observations + manifest + dq + profile
L4 ChartSpec   图表声明：类型 + 数据引用 + 编码 + 选项
```

### 1.1 Record

| 字段 | 必填 | 说明 |
|---|---|---|
| `record_id` | ✓ | 批内唯一 |
| `source_id` | ✓ | 对应 `configs/sources/*.yaml` 的 id |
| `values` | ✓ | 原始列 → 值，**不做任何归一** |
| `url` / `fetched_at` / `batch` / `raw_text` | | 可追溯用 |

```json
{"record_id": "b1-0001", "source_id": "demo", "values": {"name": "甲", "price": "10"},
 "url": "https://example.invalid/list?page=1", "fetched_at": "2026-11-25T10:00:00"}
```

### 1.2 Observation

| 字段 | 必填 | 说明 |
|---|---|---|
| `metric_id` / `entity` / `period` / `value` / `unit` | ✓ | 单位未识别写 `unknown`，不许留空 |
| `value_base` / `unit_base` / `scale` | | 归一后的值与单位（跨单位比较只读它） |
| `scope` / `segment` | | 口径与细分（与 metric_id 一起构成主键） |
| `source_id` / `grade` / `record_id` | | 证据链 |

> 旧 `data_model.Row` 不删除：`observation_from_row()` / `row_from_observation()`
> 双向适配，历史 `raw.json` 仍可读。

### 1.3 Dataset

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` / `grain` / `observations` | ✓ | grain 是「一行代表什么」 |
| `manifest` | | 来源列表、冲突、未映射 |
| `dq` | | rows_in / rows_out / dropped / dup_rate / unit_unverified |
| `profile` | | 列画像（空值率 / distinct / top1 / 数值统计），供选型 |

### 1.4 ChartSpec（数据引用，不内嵌数字）

| 字段 | 必填 | 说明 |
|---|---|---|
| `chart_type` | ✓ | 必须是 `data_standard.CHART_TYPES` 里登记的类型 |
| `data_ref` | ✓ | 至少 `dataset` 或 `metric` |
| `encode` | ✓ | 至少 `x`/`value`/`label`/`series` 之一 |
| `option` | | 标题、单位、降级说明 |

```json
{"chart_type": "hbar",
 "data_ref": {"dataset": "sales", "metric": ["m_3f2a"]},
 "encode": {"label": "entity", "value": "value"},
 "option": {"title": "各主体销量", "unit": "件"}}
```

## 2. 两份「图表契约」的分工（别混）

| 模块 | 管什么 | 谁在用 |
|---|---|---|
| `core/charts/chart_spec.py` | **交付契约**：type/title/source/unit_meta/claim_to_prove | 决策报告 `decision.chart_contract_ok` |
| `core/charts/chart_contract.py` | **三条线归一**：relation/intent/chosen/dims | S4/S5 选型与门禁输入 |
| `core/charts/chart_field_contract.py` | **渲染字段契约**：REQUIRED vs SAMPLE 同源审计 | `scripts/check_charts_pro.py` |

## 3. 门禁对应

| 契约 | 门禁 |
|---|---|
| 采集规格 | `collection_spec.validate()`（raw / metric 两种模式） |
| 语义层四段 | `card_upgrade.validate_semantic()` → S5 不发卡 |
| 图型字段 | `scripts/check_charts_pro.py`（contract audit） |
| 业务词隔离 | `scripts/check_business_terms.py --check`（CI `[0c]`） |
| 项目边界 | `scripts/check_project_boundary.py` + `core/paths.write_artifact` |
