# REPORT-LINE-V8 · 奶酪零食方法族与六类报告

> v7 只解决「怎么把一条判断论证清楚」；v8 解决「换一个业务，怎么不套旧报告」。
> 本文记录 v8 对 v7 的扩展边界，以及六份报告的可复现入口。

## 1. v8 改了什么（只加，不改 v7 契约）

| 层 | v7 | v8 扩展 | 为什么 |
|---|---|---|---|
| 方法 | `market` 族（社零/家电家具/家装补贴） | `cheese` 族 12 个方法（规模/增长/结构/渠道/供给/区域/政策/单位经济/链路/内容/缺口/价格序列） | 家居百货指标语义套不到奶酪零食 |
| 纲领 | market / operations / chain / content / remediation | `cheese_market` / `cheese_data` / `cheese_ops` / `cheese_chain` / `cheese_content` / `cheese_fix` | 同一批 finding 按六类问题链装配 |
| 帧 | 肉禽蛋三类帧（硬编码活畜/屠宰/冷链） | `core/frames_cheese.py`：整改问题链帧 | 整改方案不能把 finding 平铺 |
| 数据 | 价格 CSV / facts.json | `obs_cheese.json`（40 条带 url/quote/grade 观测）+ 四张价格表 | 每条事实可溯源 |

**关键约束（不破坏既有报告）**

1. 方法 key 全局唯一（`REGISTRY` 是扁平字典，同名会覆盖）。v8 全部加 `cheese_` 前缀。
2. `register_need("cheese.obs", …)` 只在事实表含奶酪观测时挂载，不影响家居百货/肉禽蛋项目。
3. `report_compose` 的 `order` 过滤从「仅 market 生效」放宽为「所有纲领生效」：纲领里没列的方法不装配，避免奶酪报告挂进肉禽蛋方法。
4. 深度门禁 `STRICT` 增加 6 个 cheese 纲领：深度不达标直接不渲染，不靠人眼兜底。

## 2. 六份报告与参考稿的对应

| # | 参考稿 | v8 对应 | 主证据 | 节数 |
|---|---|---|---|---|
| 1 | 家居百货市场调研报告 | `cheese_market` 市场调研报告 | size / structure | 10 |
| 2 | 肉禽蛋市场调研与数据分析报告 | `cheese_data` 市场调研与数据分析报告 | price / size | 9 |
| 3 | 肉禽蛋经营报告 | `cheese_ops` 经营测算报告 | unit_econ | 6 |
| 4 | 肉禽蛋链路优化报告 | `cheese_chain` 链路优化报告 | chain | 6 |
| 5 | 肉禽蛋营销调研与内容增长方案 | `cheese_content` 营销与内容增长方案 | channel / content | 6 |
| 6 | 牛肉与鸡蛋负毛利整改方案 | `cheese_fix` 成本与止损整改方案 | unit_econ / chain | 8 |

## 3. 论证链没有降级

每节仍走 v7 五段：**观察 → 对照 → 机理 → 落点 → 证伪**。

- 判断标题必须是带数字的结论，不是「某某分析」。
- 机理由方法显式写（奶酪零食的成本栈、渠道扣点、礼盒溢价），不调用家居百货的 `_mech_*`。
- 证伪条件必须可观测：原料涨幅、渠道扣点、单品类同比偏离，写进正文。

## 4. 数据契约（沿用 v7，新增奶酪事实表）

```
data/
  obs_cheese.json      # 40 条：id/indicator/value/unit/period/region/url/quote/grade
  facts.json           # F01–F43 + A1–A8 假设（C 级单独声明）
  sources.json         # S1–S7（政府/协会/企业年报/平台洞察）
  奶酪采价_月度.csv     # 品类 × 2024年/2025年/2026-11 + 同比
  奶酪批发报价.csv       # 长表：市场/日期/品类/价格
  奶酪产地出厂价.csv     # 长表：产地/日期/品类/价格
  奶酪区域价格.csv       # 地区 × 品类 × 两期
```

价格表列名必须让 `_is_period_name` 认得出期次（`2024年` / `2026-11`），
否则序列退化成横截面，`price.series2/3` 不成立，数据报告会被主证据门禁拦下。

## 5. 复现

```bash
python guagua.py report produce --intent "内蒙古奶酪零食市场调研" \
  --dir "D:\蛙蛙呱呱\新业务_内蒙古特色奶酪零食_2026-11-15" --out <out>

python guagua.py report produce --intent "内蒙古奶酪零食价格数据分析" \
  --dir <项目> --out <out>        # → cheese_data

python guagua.py report produce --intent "内蒙古奶酪零食经营测算" --dir <项目> --out <out>
python guagua.py report produce --intent "内蒙古奶酪零食供应链链路优化" --dir <项目> --out <out>
python guagua.py report produce --intent "内蒙古奶酪零食营销与内容增长" --dir <项目> --out <out>
python guagua.py report produce --intent "内蒙古奶酪零食成本与止损整改" --dir <项目> --out <out>
```

两道门禁：

```bash
python -m core.report_quality <report.html>          # 七条深度门禁 Q1–Q7 + C1
python scripts/check_report_flow.py <report.html>    # 九条成品门禁 F1–F9
```

## 6. 加新业务的成本（v8 的可复用结论）

三处即可，不动渲染层：

1. `core/methods/<业务>.py`：`@method` + `register_need`，key 加业务前缀；
2. `core/report_thesis.py`：纲领 `order` + `PRIMARY` + `infer()` 路由；
3. `core/frames_<业务>.py`（可选）：整改/诊断类问题链。

数据侧只交 `obs_*.json` + `facts.json` + 价格表，方法层不读业务文案。
