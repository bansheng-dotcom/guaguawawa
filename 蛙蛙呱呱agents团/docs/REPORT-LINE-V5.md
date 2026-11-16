# 报告产线 v5：方法注册表 · 角色适配层 · 跨域纲领

> 2026-11-15。v4 解决了「会分析」，v5 解决「可扩展」：
> 加方法不用改调度器，加报告类型不用改渲染器，加角色不用改产线。
> 三件事都是工程化落地，不是设计稿。

---

## 一、方法注册表（`core/methods/`）

### 1.1 方法变成「能力声明」

```python
@method("funnel", family="growth",
        needs=["table.orders"],            # 需要什么数据能力
        produces="转化漏斗",                # 产出什么判断
        tags=("growth", "marketing"),      # 哪类纲领会用到
        priority=70)
def m_funnel(ctx): ...
```

调度器只认 `needs`：

```bash
python guagua.py report plan --dir <项目> --intent "增长诊断"
```

输出 `mounted`（挂上哪些方法）与 `skipped`（缺哪个能力、为什么跳过）。
换项目不用改 `collect()`，换报告类型只要加声明 + 加纲领。

### 1.2 当前方法清单（28 条声明，含别名）

| 族 | 方法 | 需要的能力 | 产出 |
|---|---|---|---|
| 价格/成本 | structure / momentum / trajectory / contribution / economics / breakeven / forecast / risk / sample | `price.series2/3/4`、`price.momentum`、`price.economics` | 分化、节奏、轨迹、贡献、单位经济、保本、外推、风险、样本 |
| 链路 | transmission / arbitrage（别名 chain / spread） | `price.origin`、`price.wholesale`、`price.region` | 三段价差、跨市净利 |
| 增长 | funnel / retention / rfm / roi / payment_mix | `table.orders`、`table.retention`、`table.spend`、`table.payments` | 漏斗、复购、RFM、投放 ROI、支付结构 |
| 体验 | sla / reviews | `table.sla`、`table.reviews` | 准时率、VOC |
| 产品 | priority | `table.priority` | RICE 排序 |
| 商品/门店 | sku / store | `table.sku`、`table.store` | ABC 结构、坪效/租售比 |
| 组织 | headcount / capacity | `table.headcount`、`table.capacity` | 到岗率、利用率 |
| 稳定 | incidents | `table.incidents` | 可用性、MTTR |

能力谓词在 `spec.register_need()` 注册，`Caps.has()` 查询；
新增一个能力只要写一个谓词函数，不用改调度器。

### 1.3 主证据守卫

每类纲领声明 `PRIMARY`（主证据）。主证据一个都没命中时，产线**拒绝出报告**并给出缺什么：

```
「sku」纲领缺主证据（sku）：需要能力 table.sku；补数据后重跑，或先用 report plan 看这份数据能挂哪些方法
```

这条守卫防止「用风险节硬凑一份商品结构报告」——那正是模板化的来源。

---

## 二、角色适配层（`core/report_roles.py`）

### 2.1 覆盖全量，不靠人工逐个拍

- 扫描 `skill_graph`：**20 角色 / 195 技能 / 337 动作**；
- 规则分类（14 个技能族：stat / cost / commerce / growth / support / content /
  product / people / sre / finance / decision / eval / research / ops / dataops）+
  11 条人工覆盖（`OVERRIDES`）；
- 每个技能输出：`category / claim / eligible / theses / reason`。

**结果：94 个技能、143 个动作可进报告；其余 101 个技能显式排除**，排除理由分三类：

| 排除类 | 例子 | 理由 |
|---|---|---|
| mutate | 支付、退款、部署、发布、审批、删除 | 写操作/不可逆，不许进报告 |
| security | 凭据、密钥、KYC、合规红线 | 红线类，不引用 |
| meta | manifest/demo/test/harness | 只做门禁，不进正文 |

### 2.2 输出什么 claim

| 技能族 | claim 模板 | 进哪些纲领 |
|---|---|---|
| stat | 统计量（n/均值/斜率/p 值/效应量） | 全部 |
| cost | 单位成本/排序/覆盖率 | 经营/链路/商品/单店 |
| growth | 转化/ROI/留存/健康分 | 增长/营销/体验 |
| research | 台账/规模/情景 | 调研/营销 |
| decision | 任务卡/决策卡 | 全部 |
| content | 定性（标题/结构/合规） | 营销 |
| … | … | … |

### 2.3 命令

```bash
python guagua.py report capabilities          # 20 角色覆盖率表
python guagua.py report capabilities --json   # 每条技能的分类与 claim
python guagua.py report capabilities --write  # 落盘 workspace/_configs/report_capabilities.json
```

---

## 三、跨域纲领（`core/report_thesis.py`）

13 类纲领：5 个价格/经营类（research / operations / remediation / chain / forecast）
+ 8 个跨域类（growth / product / support / people / sre / marketing / sku / store）。

每类声明四件事：

```python
"growth": {
    "label": "增长诊断",
    "order": ["funnel", "retention", "rfm", "roi", "payment_mix", "reviews", "risk"],
    "primary": ["funnel", "retention"],     # 没有主证据就不出这类报告
    "ask": "增长卡在获客、转化还是留存？",
}
```

`infer()` 先看意图关键词，缺关键词时看数据能力（有批发价→经营；有订单/评价→增长）。

---

## 四、新增报告类型的标准动作（解决方案）

以「SKU 结构报告」为例，**不新开产线**，只做四步：

| 步 | 做什么 | 落点 | 判据 |
|---|---|---|---|
| 1 | 准备数据：`sku, qty, price, margin` 四列（一张表即可） | 项目目录 CSV | `report plan` 里 `sku` 出现在 mounted |
| 2 | 如果现有方法不够，加一个方法：`@method("xxx", needs=[...])` | `core/methods/generic.py` 或新族文件 | `report capabilities --json` 能看到它 |
| 3 | 在纲领里加一类（或复用）：`THESES["sku"] = {...}` | `core/report_thesis.py` | `infer()` 能命中，`PRIMARY` 有主证据 |
| 4 | 跑 + 过门禁：`report produce --intent … --dir …` | `workspace/reports/…` | 九条门禁 PASS |

**不需要动**：渲染器（`report_renderer`）、过账（`report_flow`）、CLI 主体、门禁脚本。
**必须动**：只有「能力声明 + 方法 + 纲领」三处，且都有模板可抄。

### 已有但缺数据的报告类型

| 报告类型 | 纲领 | 方法 | 缺什么数据 |
|---|---|---|---|
| 营销方案 | marketing | roi / funnel / reviews / rfm | 渠道花费、内容/人群表 |
| SKU 结构 | sku | sku / store / forecast | SKU×销量×毛利 |
| 单店模型 | store | store / sku / economics | 面积、租金、销售、毛利 |
| 产品决策 | product | priority / reviews / retention | RICE 四列或需求清单 |
| 组织人效 | people | headcount / capacity | 编制、到岗、周期 |
| 稳定性复盘 | sre | incidents / capacity | 故障时长、等级、容量 |

数据一到位，一条命令出报告——**这就是「不新开产线」的意思**。

---

## 五、验证

```bash
python -m pytest tests/test_analysis_line.py -q     # 10 条（v4 5 条 + v5 5 条）
python scripts/check_report_flow.py --dir <out>      # 九条门禁
python scripts/ci_report_checks.py                   # A/B 分支 + 20 角色 + 图表
```

v5 新增 5 条测试锁定：方法声明完整性、按数据形状挂载、20 角色全覆盖、
跨域纲领识别、增长报告端到端过门禁。

---

## 六、边界（仍然是工程事实，不是能力吹嘘）

1. **角色适配层是「资格判定 + claim 模板」，不是「所有技能都已接入报告」**：
   94 个技能有资格，但目前真正被方法库消费的是价格/增长/体验/商品等 20 余个；
   其余是「可接入」状态，需要时按第四节第 2 步加方法。
2. **通用表方法依赖列名同义词**：列名与 `SYN` 差异过大时会判为缺能力；
   补一条同义词即可，不需要改方法。
3. **跨域报告的证据强度取决于源表**：Olist 演示里没有投放花费，`roi` 自动跳过并记缺口，
   没有编一个 ROI。
4. **写操作与红线技能永远不进报告**：这是策略，不是能力缺失。
