# 报告语义模型收敛 SOP（v3.0）

> 中心一句话：**作者只交「事实 + 问题 + 大纲」，系统做其余。**
> v2.0 的两个出发点错误已修正：溯源是内在边（不建账）、语义是一管道（不是两后端各自 lower）。
> 本轮把三条"作者体验"的出发点也翻过来：作者不写代码、不手写长文、不背图型名。

---

## 0. 拓扑（不变）

2 个入口（`run-line` / `flow`）、2 套渲染器（`report_renderer` / `kit`）、3 种作者写法（claims.json / decision.json / facts.py）。收敛语义，不收敛语法、不收敛排版。

---

## 1. 核心原则：最低作者负担

作者交三样，系统做其余：

| 作者交 | 系统做 |
|---|---|
| 事实（facts：数字 + 维度 + 来源） | 校验（声明式 schema，parse 时报错） |
| 问题（question：这节答什么） | 文案（从 facts + 大纲生成） |
| 大纲（outline：这一节论证什么） | 图表（从 question 推断 + 候选确认） |

作者**不**写代码、**不**手写 800 字、**不**背图型名。这三条"不"，分别对应原来的三个差距。

---

## 2. 目标架构

```
3 种作者写法（全部声明式：yaml/json，非 Python）
      ▼ 3 个薄前端（parse + lower，有损则显式降级）
1 份富语义 IR（typed）
      · facts:  {id, metric, entity, period, value, unit, source, derived_from}
      · sections:{title, question, outline, readings, actions, boundary, falsifier,
                   chart:{relation?, chosen?, data_refs, dims}}   # relation 可选
      ▼ 1 条语义管道（唯一语义源）
         schema 校验 → 文案生成 → 图表推断+确认 → 语义一致性 → 溯源解析
      ▼ 1 份已解析的报告模型（所有语义算好）
      ▼ 2 个薄发射器（只排版，不重算语义）
         report_renderer（flow 排版）/ kit（paper 排版）
```

**四条纪律**：

1. 语义只在一条管道里，两个发射器只排版；
2. 溯源是 `source`/`derived_from` 内在边，不建全局账；
3. 富 IR 但强类型（facts 必须带 entity/period/metric/unit），防膨胀成超级 schema；
4. 前端 lowering 有损但显式（降级登记，静默损失=失败）。

---

## 3. 作者格式：声明式，不是代码

- **facts.py（Python）→ facts.yaml（声明式）+ 一份 JSON Schema**；
- claims.json / decision.json 本就是声明式，统一到同一份 schema 下；
- **parse-time 校验**（dbt `parse` / OpenAPI 的模式）：填错当场拿到字段定位清单，不是运行到渲染才崩；
- 编辑器自动补全 + 早报错——这是"作者负担"的根解，不是"更好的校验器"。

---

## 4. 富语义 IR（typed，锚点）

```yaml
schema: dsh.report_ir/v1
meta: {title, subtitle, standfirst, audience, one_thing}
facts:
  - {id, metric, entity, period, value, unit, source, derived_from: [...]}
sections:
  - {title, question, outline,
     readings: [{strong, text, refs}],      # 由文案生成填充，作者只给 outline
     actions: [...], boundary, falsifier,
     chart: {relation, chosen, data_refs, dims}}   # relation 可选
```

- `outline`：作者给的一句话论证意图，文案生成据此展开；
- `readings`：生成产物，作者不手写；
- `chart.relation`：可空，由 question 推断；作者可显式覆盖。

---

## 5. 三条"作者体验"的根解（本轮核心）

| 原差距 | 旧出发点（错） | 新出发点（对） |
|---|---|---|
| 作者负担 | 给 facts.py 加校验 | **声明式格式 + JSON Schema + parse-time 校验** |
| 文案门槛 | 按 profile 调字数 | **文案生成 + 五要素门禁（不查字数）** |
| 自动选型 | 作者声明 relation | **从 question 推断 + 候选确认，relation 是 override** |

**文案门禁改法**：不查"够不够 800 字"，查"事实/机理/反例/信号/所以五要素齐不齐、每要素有没有 refs"。长度是坏代理，语义完整才是真门槛。`prose_render` 已有，改为默认路径。

**图表门禁改法**：`infer_relation(question, dims)` 从问题文本 + 数据形状推断意图，生成 2–3 个候选，作者确认；作者显式写 `relation` 时覆盖推断并校验。这跟 HCI"推荐器看不到意图"不矛盾——意图在问题里，不在字段类型里。

---

## 6. 前端 lowering（有损 + 格式能力表）

每个前端（claims/decision/facts 适配器）：

1. 声明格式能力表（本写法能/不能表达什么）；
2. parse 到 IR，不能映射的登记 `degraded: {field, reason}`；
3. 降级率设上限（如 <10%），超限判前端不合格。

---

## 7. 一条语义管道 + 两个薄发射器

- **一条管道**算完：schema 校验、文案生成、图表推断、语义一致性、溯源解析；
- **两个薄发射器**只把已解析模型排成 flow / paper 版式，不重实现语义；
- 后端只消费"已解析模型"，**不读作者格式字段、不读 IR 之外的语义**（门禁强制）。

---

## 8. 内在溯源（不建账）

- `fact.source` → 来源记录；`fact.derived_from` → 派生原料；
- "这个数从哪来" = 沿边回走，**不建任何全局 provenance 结构**；
- 变换史挂在 fact 自身（可选 `history` 字段），不建独立账本。

---

## 9. 门禁（5 条）

1. **schema**：parse-time 字段校验（早报错）；
2. **文案**：五要素 + refs 完整，不查字数；
3. **图表**：relation×mark 合法、二维只在有二维数据时、候选含 author override；
4. **语义一致性**：同一份 IR 在两个发射器含义一致；
5. **后端只消费已解析模型**：读作者格式字段或 IR 外语义 = 失败。

---

## 10. 步骤

| 步 | 做什么 | 退出条件 |
|---|---|---|
| S0 定 IR + 作者 schema | 富 IR schema v1 + facts.yaml JSON Schema 定稿 | schema 定稿 |
| S1 黄金语料 | 三写法各固一份（含溯源快照） | 可复现 |
| S2 前端 claims | claims→IR | 呼包鄂 content_hash 零回归 |
| S3 前端 decision | decision→IR | A 线快照零回归 |
| S4 前端 facts + 声明式化 | facts.py → facts.yaml + 适配器 | spec-fruit 零回归 |
| S5 语义管道 + 薄发射器 | 一管道 + 两薄发射器，文案生成/图推断接默认 | 语义一致性过 |
| S6 清死代码 | 删三写法旧 schema/选型、旧 facts.py 载体 | 孤儿 0 |

---

## 11. 已否决方案

| 方案 | 为什么否 |
|---|---|
| 最小公共子集 IR | 交集反模式（LLVM） |
| 零回归承诺 | lowering 有损，伪承诺（Pandoc） |
| 两后端各自 lower | 爆炸半径大，应一管道+薄发射器 |
| 作者声明 relation（必填） | 新增作者负担，应从 question 推断 |
| 手写 800 字 + 字数门禁 | 长度是坏代理，应生成+五要素 |
| facts.py 代码载体 | 内容是数据不是代码，应声明式 |
| 全局 provenance 账 | 应内在边，不建账 |

---

## 12. 影响（二阶三阶，摘要）

- 作者负担结构性下降：写声明式数据、给大纲、不背图型名；
- 语义单源：改一处语义三写法受益；
- 文案生成依赖：生成质量决定报告下限，需人工抽检兜底；
- 薄发射器：新增呈现能力仍两发射器各改（正常，排版本就不同），但语义不再重复。

---

## 13. DoD

- 三写法落到同一富 IR，旧输入不回归；
- facts.py 换成 facts.yaml，parse-time 报错；
- 文案由生成填充，五要素门禁过、不查字数；
- 图表由 question 推断 + 候选确认，relation 可选覆盖；
- 溯源可沿 source/derived_from 回走，不建账；
- 两发射器只消费已解析模型，语义一致性过。

---

## 14. 回滚

- 前端/发射器各独立开关 `IR_MODE=ir|legacy`；
- IR schema 版本化 + 迁移脚本；
- 黄金语料 + 溯源回走兜底。

---

## 15. 不做清单

- 不做最小子集 IR；不承诺零回归；不做全自动选型；
- 不让作者手写长文、不背图型名、不写代码载体；
- 不建全局 provenance 账；不长期维护前端；
- 不让后端重读作者格式、重实现语义。
