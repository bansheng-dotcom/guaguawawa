---
name: design-system
description: 设计系统与令牌技能包。把「视觉要统一」变成可校验的令牌体系：颜色/字体/间距三类令牌必须分类齐全且值合法，主色唯一、字号成阶梯、间距落在刻度内，并能一键落盘 DESIGN.md 与 design_tokens.json 供工程直接引用。当需要定设计系统、写设计令牌、统一多端视觉、或判断一套令牌能不能交给工程时使用。不负责界面布局与交互流程（见 frontend-design）、不做电商主图与详情页（见 ecommerce-designer）、不做品牌 VI 从零设计。
license: MIT
compatibility: 通用。门禁在角色根目录 agent.py（brand token / designsys list|recommend），Python 3.10+、零第三方依赖；无 Python 环境时按 §8 转人工核对，此时不得标记「可交付工程」。
metadata:
  owner: r10
  version: "2.0.0"
  kind: skill
  triggers: "设计系统,设计令牌,design token,色彩体系,字阶,间距刻度,多端统一"
  verify: python agent.py brand token --input <令牌.json>
  entry: "python agent.py designsys recommend"
  consumers: "r09,r08,r14"
  supersedes: "README.md"
---

<!-- 本文件由 scripts/sync_dsh_skills.py 生成，请勿手改；改源包后重跑同步 -->

# 设计系统与令牌（Design System）

> 一句话定位：**这个技能存在的意义，是防止「每个页面单独看都好看，放一起像三个产品」**。
> 视觉不统一的根因很少是审美，而是**没有令牌**：
> 颜色是手填的十六进制、字号靠目测、间距随手 13px。
> 一旦没有令牌，改动就是逐页手改；一旦有令牌，改动是一行。

## §1 何时用 / 何时不用

**该用（用户真实这么问）**
- 「设计系统怎么定」「令牌怎么写」
- 「为什么各页面颜色不一致」「字号有几级」
- 「这套令牌能交给工程吗」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 页面布局、交互流程、可用性 | 本角色的 `frontend-design` | 那是界面设计 |
| 电商主图、详情页、活动图 | 本角色的 `ecommerce-designer` | 那是转化导向的视觉 |
| 品牌 VI 从零（标志/字库/手册） | 创始人 + `r10` | 品牌设计是独立范畴 |
| 工程侧怎么落地令牌 | `r09` 的 `web-app-development` | 本包只出令牌与规范 |

**最小可开工输入**：**一套颜色 + 一个主色**，即可起步；其余按默认刻度补全。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| 颜色（主色至少 1 个，十六进制） | 必需 | 无颜色无法建令牌 |
| 字体族（≤2 种） | 建议 | 缺则给"中文黑体 + 西文无衬线"默认并标注 |
| 间距刻度 | 建议 | 缺则用 4/8/12/16/24/32/48 |
| 目标端（Web / 小程序 / App） | 建议 | 缺则给 Web 优先并标注 |
| 品牌已有规范 | 可选 | 有则以品牌为准，不另造 |

**追问纪律**：最多一轮，只问**主色是什么、有几种字体**。其余按刻度默认。

---

## §3 执行流水线（Workflow）

### Step 1 · 三类令牌分类齐全
```bash
python agent.py brand token --input <令牌.json>
```
令牌必须分三类，且每类有值：

```json
{"tokens": {
  "color":      [{"name": "primary",  "value": "#1E3A5F"}],
  "typography": [{"name": "heading",  "value": "24px/1.4"}],
  "spacing":    [{"name": "gap",      "value": "8px"}]
}, "primary": "#1E3A5F"}
```

门禁实测：三类缺任一类、或主色缺失/不合法 → FAIL（`token_dirty` 即此情形）。

- **产出**：三类令牌表
- **过关条件**：`agent.py brand token` 退出码 0

### Step 2 · 主色唯一 + 色阶可推导
- **主色只有一个**，其余是它的色阶（如 50/100/…/900）；
- 色阶必须是主色的明度变化，不能是"另外挑的七个颜色"；
- 语义色（成功/警告/危险/信息）单独成组，**不与品牌色混用**。

**判据**：删掉主色这一行，其余颜色还能推导出来吗？不能 → 色阶是拼的。

### Step 3 · 字号阶梯（≤5 级，正文 ≥14px）
| 级 | 用途 | 行高 |
|---|---|---|
| 28 | 页面标题 | 1.2 |
| 20 | 区块标题 | 1.25 |
| 16 | 小标题 | 1.4 |
| **14** | 正文（下限） | 1.5 |
| 12 | 辅助 | 1.5 |

出现 13/18/22 这类值，说明是目测调的，不是设计出来的。

### Step 4 · 间距刻度（七档，不出刻度）
`4 / 8 / 12 / 16 / 24 / 32 / 48`。
**任何间距值都必须能在刻度里找到**；找不到就是新增一档，要走评审，不能随手加。

### Step 5 · 落盘与推荐
```bash
python agent.py designsys recommend --input <项目类型.json>   # 按项目类型推荐库内设计系统
python agent.py designsys list                                # 看库里有哪些
python agent.py designsys apply --input <令牌.json> --out <目录>  # 落盘 DESIGN.md + design_tokens.json
```
**令牌必须落成文件**，工程只认文件不认口述。

- **产出**：`DESIGN.md` + `design_tokens.json`
- **过关条件**：两个文件都生成且可被工程直接读取

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | 三类令牌表（color/typography/spacing） | `.json` | `examples/token.json` |
| 2 | 主色与色阶推导说明 | `.md` | 本文 §3 Step 2 |
| 3 | 字号阶梯表（≤5 级） | `.md` | 本文 §3 Step 3 |
| 4 | 间距刻度表（七档） | `.md` | 本文 §3 Step 4 |
| 5 | `DESIGN.md` + `design_tokens.json` | 文件 | `agent.py designsys apply` |

- 命名：`design_<品牌/产品短码>_<YYYYMMDD>/`
- **令牌文件是唯一可交付工程的载体**；截图与口述不算。

---

## §5 质量门（一票否决，不过不给交付）

1. **三类令牌齐全**（color / typography / spacing）；
2. **主色存在且为合法十六进制**（`brand token` 门禁）；
3. **主色唯一**，其余为色阶或有明确语义命名；
4. **字号 ≤5 级且正文 ≥14px**；
5. **间距全部落在 4/8/12/16/24/32/48**；
6. **字体族 ≤2 种**，且标明商用授权状态；
7. **`DESIGN.md` 与 `design_tokens.json` 已落盘**。

> 验收命令：`python agent.py brand token --input <令牌.json>`
> 命中任一项不过 → 回 §3 对应 Step 重做，**不允许删掉某一类令牌让门禁变绿**。

---

## §6 交付前自检清单

- [ ] 三类令牌都有，不是只有颜色
- [ ] 主色只有一个，且是合法十六进制
- [ ] 其余颜色能由主色推导（或明确标为语义色）
- [ ] 字号不超过 5 级，正文 ≥14px，行高按 1.5 / 1.2
- [ ] 所有间距值都在 4/8/12/16/24/32/48 里
- [ ] 字体族不超过 2 种，逐款标明商用授权
- [ ] 对比度：正文 ≥4.5:1（用工具量过）
- [ ] `DESIGN.md` 与 `design_tokens.json` 都生成了
- [ ] 工程方能直接读 `design_tokens.json`，不需要我再解释

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 只给颜色，没有字体与间距 | 三类缺一不可，否则工程还得猜 |
| EX-02 | 主色有两个（"品牌蓝"和"主蓝"） | 主色唯一，其余是色阶或语义色 |
| EX-03 | 色阶是"另挑的七个颜色" | 色阶由主色明度推导，能复现 |
| EX-04 | 字号 7–8 级 | ≤5 级；正文 ≥14px |
| EX-05 | 间距随手 13px / 18px | 只用七档刻度，新增刻度走评审 |
| EX-06 | 字体 4 种混排 | ≤2 种；逐款标明商用授权 |
| EX-07 | 令牌只写在文档里 | 必须落盘成 `design_tokens.json` |
| EX-08 | 语义色与品牌色混用（错误也用主色） | 成功/警告/危险/信息单独成组 |
| EX-09 | 没量对比度就交付 | 正文 ≥4.5:1，用工具量 |
| EX-10 | 令牌改了不同步工程 | 令牌是单一来源，改令牌即改全站 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `agent.py` 门禁跑不了 | 按 §6 人工核对，标注「未跑门禁」；**不得标记"可交付工程"** |
| 只有品牌 logo 没有色值 | 从 logo 提取主色并标注"提取值，需品牌确认" |
| 无字体授权信息 | 全部标"授权待确认"，并给免费可商用替代方案 |
| 多端（Web + 小程序 + App） | 一套令牌 + 各端映射表，不各造一套 |
| 品牌已有规范 | 以品牌为准，不另造；缺的项才补 |
| 需要暗色模式 | 两套色值都要令牌化，不能只调背景 |
| 视觉规范本身没定 | 转 `ecommerce-designer` 或 `frontend-design` |

**明确不做**
- 不做界面布局与交互（归 `frontend-design`）；
- 不做电商主图与详情页（归 `ecommerce-designer`）；
- 不做品牌 VI 从零（归创始人 + 品牌设计）；
- 不做工程落地（归 `r09`）。

---

## §9 资源地图（按需读取，禁止全量加载）

| 什么时候需要 | 读哪个文件 |
|---|---|
| 令牌三类结构骨架 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r10-wachengmei-design/examples/token.json` |
| 反例（缺类/主色不合法） | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r10-wachengmei-design/examples/token_dirty.json` |
| 工程细节与子命令 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r10-wachengmei-design/references/engineering-notes.md` |
| 本角色能力章程 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r10-wachengmei-design/references/00-capability-charter.md` |
| 门禁是否还有效（正/反例 fixture） | `scripts/gate_selftest.py --self-test` |
| 负向用例 | `tests/misuse.md` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言 `brand token` 门禁与 `designsys list` 的退出码 | `--self-test` / `--verbose` |

**常用命令**

| 用途 | 命令 |
|---|---|
| 令牌门禁 | `python agent.py brand token --input <令牌.json>` |
| 按项目推荐设计系统 | `python agent.py designsys recommend --input <项目类型.json>` |
| 看库内设计系统 | `python agent.py designsys list` |
| 落盘 DESIGN.md + tokens | `python agent.py designsys apply --input <令牌.json> --out <目录>` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 从能力卡升级为十节技能包。
  新增：§1 转交表、§2 最小可开工输入、§3 五步流水线（三类令牌→主色色阶→字号→间距→落盘）、
  §7 十条错误表、§8 七种降级、`scripts/gate_selftest.py`、`tests/misuse.md`。
  门禁复用 `agent.py brand token` 与 `designsys`，未新增判定实现。
- v1.0（此前）：能力卡形态（`README.md`，约 0.82 KB，无 frontmatter/触发语/门禁声明）。
