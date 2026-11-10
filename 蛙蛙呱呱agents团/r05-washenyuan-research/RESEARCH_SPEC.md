# R05 蛙深远（战略研究官）领域标准账本 (RESEARCH_SPEC.md)

> **版本**：v2.0.0  
> **指导思想**：战略研究不替决策层拍板，无来源标待核实，全证据链溯源闭环。  
> **对标标杆**：`dbt-labs/dbt-core`（语义层单一信任源 SSOT） / `great-expectations/great_expectations`（声明式门禁与加权评分） / `OpenBB-finance/OpenBB` / `Gartner Research Methodology`

---

## 1. 证据等级与置信度基准 (Evidence Tier & Confidence Levels)

在 R05 的战略分析框架中，所有断言（Claims）必须严格绑定来源证据（Sources）：

| 证据等级 | 来源类型 (Source Type) | 最低交叉验证来源数 | 最低置信度评分 | 采纳与决策建议 |
| :---: | :--- | :---: | :---: | :--- |
| **Tier 1 (黄金级)** | 权威官方年报、监管披露文件 (`company_filing`)、同行评审行业研报 (`industry_report`) | 1 项即可 | 0.90 | 高置信度，可直接作为核心测算基准输入 |
| **Tier 2 (白银级)** | 权威主流财经科技媒体 (`news`)、第三方专业数据服务平台 (`dataset`) | 2 项独立信源交叉 | 0.75 | 稳健置信度，需注明采集时间截点与统计口径 |
| **Tier 3 (青铜级)** | 专家访谈纪要 (`expert_interview`)、竞品公关稿、一手定性调研 | 2 项以上 | 0.60 | 辅助参考，需标记「待持续交叉验证」 |
| **Tier 0 (无效级)** | 匿名论坛发帖、无法溯源的二手传言、无出处截图 | 0 | 0.00 | **强行红线拦截**，禁止录入正式研报 |

---

## 2. 行业集中度与市场格局基准 (HHI & Market Structure)

基于美国司法部 (DOJ) / FTC 与反垄断反不正当竞争基准口径：

| 结构分类 (Structure) | HHI 指数区间 | CR4 集中度区间 | 竞争态势特征 | 破局与进入策略建议 |
| :--- | :---: | :---: | :--- | :--- |
| **充分竞争 (Competitive)** | HHI < 1500 | CR4 < 40% | 市场高度分散，无绝对支配者 | 拼产品体验、快速获客与差异化定位 |
| **中度集中 (Moderate)** | 1500 ≤ HHI ≤ 2500 | 40% ≤ CR4 < 70% | 头部出现多强并立格局 | 寻找巨头夹缝，切入垂直细分品类 |
| **寡头垄断 (Oligopoly)** | HHI > 2500 | CR4 ≥ 70% | 少数几个巨头占据核心市场份额 | 避免正面正面肉搏，深耕差异化生态或被并购价值 |

---

## 3. 市场规模与置信收敛基准 (TAM / SAM / SOM Dual-Track)

自上而下 (Top-Down) 与自下而上 (Bottom-Up) 测算必须满足双口径收敛：

1. **双口径相对方差容差**：  
   $$\text{Variance} = \frac{|\text{TAM}_{\text{top}} - \text{TAM}_{\text{bottom}}|}{\text{TAM}_{\text{top}}} < 0.30 \quad (30\%)$$
   若相对方差 $\ge 30\%$，强制触发置信区间过宽预警，不可作为确定性研报输出。
2. **三情景梯次递减法则**：  
   $$\text{SOM} < \text{SAM} \le \text{TAM}$$
   - **Downside (悲观紧缩型)**：获客份额与渗透率取保守下限（如 1%~5%）；
   - **Base (基准稳健型)**：以行业平均转化与中位获客能力为基准（如 5%~15%）；
   - **Upside (乐观突破型)**：在强网络效应或飞轮驱动下的扩张上限（如 15%~25%）。
3. **敏感性单点分析**：  
   按摆动幅度（$\text{Swing} = |\text{High} - \text{Low}|$ 以及 $\text{Swing Pct} = \text{Swing} / \text{Base}$）排序，第一驱动要素即为战略死穴。

---

## 4. 事前尸检与失效风险矩阵 (Pre-mortem & Risk Tiers)

风险评分机制：$$\text{Risk Score} = \text{Likelihood (1~3)} \times \text{Impact (1~3)} \in [1, 9]$$

| 风险等级 (Tier) | 分值区间 (Score) | 处置原则 | 强制硬约束 |
| :--- | :---: | :--- | :--- |
| **Critical (致命级)** | 9 分 (3×3) | 属于项目一票否决/最高级别威胁 | 必须配备经推演的缓解预案与提前预警信号 (Early Warning) |
| **High (严重级)** | 6 分 (2×3 或 3×2) | 严重威胁商业模型跑通 | 必须明确应对策略与替代路线备选方案 |
| **Medium (中等度)** | 3~4 分 | 常规业务阻力 | 纳入定期跟踪监测清单 |
| **Low (轻微级)** | 1~2 分 | 偶发性干扰 | 观察留档 |

---

## 5. 商业研究禁词与反模式红线 (Anti-Slop & Redlines)

1. **决绝越权拍板 (Decision Redline)**：  
   R05 严禁以决策者口吻输出：“必须进入”、“绝对可行”、“老板直接投”。必须转换为选项呈现：“在方案 A 下风险点为 X，方案 B 下收益弹性为 Y”。
2. **绝无凭空断言 (Sourcing Redline)**：  
   严禁使用“业内公认”、“显而易见”、“根据普遍共识”等模糊信源，每一个核心数据指标必须能够回溯到登记凭据。
3. **模糊敷衍词清洗 (Slop Clean)**：  
   严禁充斥“前景广阔”、“未来可期”、“大有作为”等无法量化度量的假大空词汇，必须结合行业数据与事实给出客观分析。

---

## 6. 机器可读 SSOT 与 8 维发布门禁 (Machine-Readable SSOT & 8-Gate Release Gate)

本节是 R05 领域账本的**唯一机器可信源（Single Source of Truth）**。`engines/spec_ledger.py`
只解析文档中的第一个 `json` 围栏代码块，并以文件中的阈值驱动 `evaluate()` 与发布门禁，
禁止把版本、TAM 方差容差、HHI 区间、证据等级置信度或 8 维门禁权重再次写死在 Python 代码中。
修改本文件即等于修改全链路门禁口径，可被 CLI、下游 R06 看板与 CI 以确定性方式复现。

### 6.1 SSOT 字段说明

- `tam_variance_max`：TAM 双口径相对方差上限，超过即不可作为确定性研报输出；
- `hhi`：DOJ/FTC 口径的竞争/中度/寡头三段 HHI 阈值；
- `evidence_tiers`：Tier 1/2/3/0 的最低交叉来源数与最低置信度；
- `north_star`：北极星指标「证据覆盖率」目标值 1.0（每条断言均可溯源）；
- `gates`：8 维发布门禁，`rule=min` 表示指标须 `>= threshold`，`rule=max` 表示须 `<= threshold`，
  权重之和恒为 1.0，加权得分 100 分制，全部通过才允许发布。

### 6.2 机器可读 SSOT（解析器只认本文件的第一个 json 块）

```json
{
  "version": "2.0.0",
  "tam_variance_max": 0.30,
  "hhi": {
    "competitive_max": 1500,
    "moderate_max": 2500,
    "oligopoly_min": 2500
  },
  "evidence_tiers": {
    "tier_1": {"sources_required": 1, "min_confidence": 0.90},
    "tier_2": {"sources_required": 2, "min_confidence": 0.75},
    "tier_3": {"sources_required": 2, "min_confidence": 0.60},
    "tier_0": {"sources_required": 0, "min_confidence": 0.0}
  },
  "north_star": {"name": "证据覆盖率", "target": 1.0},
  "gates": [
    {
      "id": "evidence_coverage",
      "metric": "evidence_coverage",
      "rule": "min",
      "threshold": 1.0,
      "weight": 0.15,
      "description": "证据覆盖率必须达到 100%，每条断言均可回溯到登记来源"
    },
    {
      "id": "tier0_free",
      "metric": "tier0_count",
      "rule": "max",
      "threshold": 0,
      "weight": 0.10,
      "description": "Tier 0 匿名/不可溯源断言数量必须为 0，出现即红线拦截"
    },
    {
      "id": "tam_convergence",
      "metric": "tam_variance",
      "rule": "max",
      "threshold": 0.30,
      "weight": 0.15,
      "description": "TAM 自上而下与自下而上双口径相对方差必须 <= 0.30"
    },
    {
      "id": "hhi_declared",
      "metric": "hhi_declared",
      "rule": "min",
      "threshold": 1,
      "weight": 0.10,
      "description": "必须显式声明 HHI 与市场结构判定，未声明视为未完成研究"
    },
    {
      "id": "scenario_three",
      "metric": "scenario_count",
      "rule": "min",
      "threshold": 3,
      "weight": 0.10,
      "description": "必须给出保守/基准/乐观三情景横向比选，少于 3 个不可发布"
    },
    {
      "id": "redline_clean",
      "metric": "redline_clean",
      "rule": "min",
      "threshold": 1,
      "weight": 0.15,
      "description": "决策越权与跨角色红线扫描必须全部通过（1=干净）"
    },
    {
      "id": "slop_score",
      "metric": "slop_score",
      "rule": "min",
      "threshold": 80,
      "weight": 0.15,
      "description": "质感去劣评分必须 >= 80，且不得残留占位套话与无证据断言"
    },
    {
      "id": "bundle_manifest",
      "metric": "bundle_manifest",
      "rule": "min",
      "threshold": 1,
      "weight": 0.10,
      "description": "必须落盘带 SHA256 的伴生资产清单，保证下游可回放（1=已生成）"
    }
  ]
}
```
