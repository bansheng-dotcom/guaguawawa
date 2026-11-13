---
name: miniapp-builder
description: 小程序工程脚手架技能包。把「做个小程序」变成可校验的工程骨架：工程名必须合法（小写字母开头、3–31 位）、页数 2–20、页面路径形如 pages/a/b、每页有标题、tabbar 只能指向已定义页面，产出可直接导入开发者工具的工程目录。当需要搭小程序骨架、判断页面结构是否成立、或排查 tabbar 跳转失败时使用。不负责业务逻辑与后端接口、不做 App 原生打包（见 crossplatform）、不做审核提审。
license: MIT
compatibility: 通用。门禁在角色根目录 agent.py（miniapp plan / miniapp scaffold），Python 3.10+、零第三方依赖；无 Python 环境时按 §8 转人工六项核对，此时不得标记「可导入」。
metadata:
  owner: r08
  version: "2.0.0"
  kind: skill
  triggers: "小程序,工程骨架,pages,tabbar,页面路径,脚手架"
  verify: python agent.py miniapp plan --input <小程序.json>
  entry: "python agent.py miniapp plan"
  consumers: "r07,r09,r14"
  supersedes: "README.md"
---

# 小程序工程脚手架（Miniapp Builder）

> 一句话定位：**这个技能存在的意义，是防止「页面都建了，tabbar 一点就白屏」**。
> 小程序骨架最贵的失败不是样式，而是**结构不成立**：
> 工程名非法导致打包失败、tabbar 指向未定义页面导致跳转白屏、
> 页面没有标题导致导航栏空着。这些在导入开发者工具之前就能判掉。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「搭个小程序骨架」「页面怎么分」
- 「tabbar 点了没反应」「跳转白屏」
- 「这个工程能导入开发者工具吗」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| App 原生打包 | 本角色的 `crossplatform` 域 | 那是跨端构建 |
| 后端接口与业务逻辑 | `r09` | 本包只出前端骨架 |
| 提审与合规材料 | 外部 + `r16` | 本包不管审核 |
| 页面视觉设计 | `r10` 的 `frontend-design` / `ecommerce-designer` | 那是视觉 |

**最小可开工输入**：**要做几个页面 + 底部要有几个 tab**。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| `name`（工程名） | 必需 | 必须小写字母开头、3–31 位，如 `quote-tool` |
| `pages[]`（2–20 页，含 path 与 title） | 必需 | 少于 2 页不成应用 |
| `tabbar[]`（可选） | 建议 | 有 tab 时必须指向已定义页面 |
| 品牌色/标题 | 建议 | 缺则给中性默认 |

**追问纪律**：最多一轮，只问**几个页面、几个 tab**。

---

## §3 执行流水线（Workflow）

### Step 1 · 工程名（最容易第一步就错）
```bash
python agent.py miniapp plan --input <小程序.json>
```
**判据**：`^[a-z][a-z0-9-]{2,30}$`。
实测：中文名"报价小工具"直接 BLOCKER——小程序工程名只认小写字母开头的标识符。

| 反例 | 正例 |
|---|---|
| 报价小工具 | `quote-tool` |
| QuoteTool | `quote-tool` |
| qt | `quick-quote` |

- **产出**：合法工程名
- **过关条件**：`miniapp.name` 通过

### Step 2 · 页数与路径规范
| 规则 | 判据 |
|---|---|
| 页数 **2–20** | `miniapp.pages` |
| 路径形如 `pages/a/b`（`pages/` 开头） | `miniapp.page.path` |
| 每页有 `title` | `miniapp.page.title` |

**路径不是随便写的**：它同时是文件路径与路由，
写成 `pages/list` 会导致找不到文件。

### Step 3 · tabbar 只能指向已定义页面
**这是"点了白屏"的头号原因**：
```json
"tabbar": [{"page": "pages/not-exist/not-exist"}]
```
门禁会算差集，指向未定义页面即 FAIL。

**判据**：tabbar 的每个 `page` 必须出现在 `pages[].path` 里。

### Step 4 · 生成工程骨架
```bash
python agent.py miniapp scaffold --input <小程序.json> --out <目录>
```
产出可直接导入开发者工具的目录结构（含 `app.json` 基础配置）。
**不要手写 app.json**——手写最容易漏 tabbar 的 `list` 与页面注册。

- **产出**：工程目录
- **过关条件**：`agent.py miniapp scaffold` 退出码 0

### Step 5 · 导入后必查三件
1. 首页能渲染（不是白屏）；
2. 每个 tab 都能跳且不报错；
3. 导航栏标题与页面 title 一致。

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | 小程序配置 JSON（结构合法） | `.json` | `tests/miniapp-pass.json` |
| 2 | 工程目录（可导入开发者工具） | 目录 | `agent.py miniapp scaffold` 产出 |
| 3 | 页面清单（路径 ↔ 标题 ↔ 是否 tab） | `.md` | 本文 §3 Step 2–3 |

- 命名：工程目录名 = `name`（合法标识符）
- **页面清单必须随工程交付**；只有代码，接手的人不知道哪页在哪。

---

## §5 质量门（一票否决，不过不给交付）

1. **工程名合法**（小写字母开头、3–31 位）；
2. **页数 2–20**；
3. **每个页面路径以 `pages/` 开头**，形如 `pages/a/b`；
4. **每页有 title**；
5. **tabbar 的每个 page 都在 pages 里**（否则白屏）；
6. **产出可直接导入开发者工具的目录**。

> 验收命令：`python agent.py miniapp plan --input <小程序.json>`
> 命中任一项不过 → 回 §3 对应 Step，**不允许删掉 tabbar 让门禁变绿**。

---

## §6 交付前自检清单

- [ ] 工程名是小写字母开头、3–31 位（如 `quote-tool`）
- [ ] 页数在 2–20 之间
- [ ] 每个页面路径都从 `pages/` 开始，且是两段式 `pages/a/b`
- [ ] 每页都有 title（导航栏不会空着）
- [ ] tabbar 每个 page 都能在 pages 里找到（否则点了白屏）
- [ ] 工程目录是脚手架生成的，不是手拼的
- [ ] 我导入开发者工具试过：首页能渲染
- [ ] 每个 tab 我都点过，没报错
- [ ] 页面清单已随工程交付

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 工程名用中文 | 小写字母开头标识符，如 `quote-tool` |
| EX-02 | 工程名 2 位（`qt`） | 至少 3 位，用 `quick-quote` |
| EX-03 | 只有 1 个页面 | 2–20 页才叫应用 |
| EX-04 | 路径写 `pages/list` | 两段式 `pages/list/list` |
| EX-05 | tabbar 指向未定义页面 | 每个 page 必须在 pages 里 |
| EX-06 | app.json 手写 | 用 scaffold 生成，避免漏注册 |
| EX-07 | 页面没有 title | 每页给 title，导航栏才有字 |
| EX-08 | 页面 25 个 | 超过 20 说明该拆分包 |
| EX-09 | 只跑 plan 没导入验证 | 导入开发者工具实测首页与 tab |
| EX-10 | 用中文页面路径 | 路径只用小写字母与短横线 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `agent.py` 门禁跑不了 | 按 §6 人工核对，标注「未跑门禁」；**不得标记"可导入"** |
| 无开发者工具 | 只交货架与页面清单，标注"未实测导入" |
| 页面超过 20 | 建议拆成主包 + 分包，说明分包策略 |
| tabbar 想要 6 个 | 小程序 tab 一般 ≤5，建议减项 |
| 需要原生 App | 转 `crossplatform` 域 |
| 需要后端接口 | 转 `r09`，本包只出前端骨架 |

**明确不做**
- 不做业务逻辑与后端接口（归 `r09`）；
- 不做 App 原生打包（归 `crossplatform`）；
- 不做提审与合规材料（归外部 + `r16`）；
- 不做页面视觉设计（归 `r10`）。

---

## §9 资源地图（按需读取，禁止全量加载）

| 什么时候需要 | 读哪个文件 |
|---|---|
| 正例（合法工程名 + 2 页 + tabbar 合法） | `tests/miniapp-pass.json` |
| 反例（中文名 / 页面无标题 / tabbar 悬空） | `tests/miniapp-fail.json` |
| 工程细节与子命令 | `../../../references/engineering-notes.md` |
| 跨端构建 | 本角色的 `crossplatform` 域 |
| 门禁是否还有效 | `scripts/gate_selftest.py --self-test` |
| 负向用例 | `tests/misuse.md` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言 `miniapp plan` 对正/反例的退出码 | `--self-test` / `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 从能力卡升级为十节技能包。
  **新增夹具**（此前无任何小程序夹具）：`tests/miniapp-pass.json`（实测 exit 0）/
  `tests/miniapp-fail.json`（中文名 + 页面无标题 + tabbar 悬空，实测 exit 1）。
  含 §1–§10、`scripts/gate_selftest.py`、`tests/misuse.md`。
  门禁复用 `agent.py miniapp`（plan / scaffold），未新增判定实现。
- v1.0（此前）：能力卡形态（`README.md`，无 frontmatter/触发语/夹具）。
