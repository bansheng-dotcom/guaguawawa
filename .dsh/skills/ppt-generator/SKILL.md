---
name: ppt-generator
description: 单文件 HTML 幻灯片技能包。把「做个 PPT」变成可校验的演示结构：页数落在 6–30、封面必须在第 1 页、收尾必须在最后一页、每页都要有标题与一句话结论，产出单文件 HTML 可离线打开。当需要做汇报稿、路演页、复盘演示，或判断一份 deck 结构能不能讲清一件事时使用。不负责长文与 HTML 报告（见 html-report-presentation）、不做 Excel/Word 交付物（见 office-plugin）、不做动效与视频。
license: MIT
compatibility: 通用。门禁在角色根目录 agent.py（deck plan / deck html），Python 3.10+、零第三方依赖；无 Python 环境时按 §8 转人工六项核对，此时不得标记「可讲」。
metadata:
  owner: r08
  version: "2.0.0"
  kind: skill
  triggers: "PPT,幻灯片,汇报稿,路演页,封面,单文件HTML"
  verify: python agent.py deck plan --input <deck.json>
  entry: "python agent.py deck plan"
  consumers: "r01,r07,r12"
  supersedes: "README.md"
---

<!-- 本文件由 scripts/sync_dsh_skills.py 生成，请勿手改；改源包后重跑同步 -->

# 单文件 HTML 幻灯片（Deck）

> 一句话定位：**这个技能存在的意义，是防止「页很多、但讲不清一件事」**。
> Deck 最贵的失败不是不好看，而是**结构不成立**：
> 没有封面、没有收尾、每页只有标题没有结论、页数多到讲不完。
> 这些都能在动手做页面之前就判掉。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「做个 PPT」「帮我把这个做成汇报页」
- 「这份 deck 能不能讲」「页数够不够」
- 「路演要讲 10 分钟，几页合适」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 长文/报告（能读的） | 本角色的 `html-report-presentation` | 报告是读的，deck 是讲的 |
| Excel 表格 / Word 文档 | 本角色的 `office-plugin` | 那是 Office 交付物 |
| 动效视频 | 外部工具 | 本包只出单文件 HTML |
| 讲稿逐字稿 | `r11` 的 `longform-article` | 那是文字稿 |

**最小可开工输入**：**要讲给谁 + 一句核心结论**。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| 听众与场合（内部复盘/路演/汇报） | 必需 | 无听众无法定页数与深度 |
| 一句核心结论 | 必需 | 没有结论的 deck 是资料堆 |
| 页数或时长 | 建议 | 缺则按"10 分钟 ≈ 8–12 页"默认 |
| 已有素材（数据/图） | 建议 | 缺则标注"待补数据页" |
| 品牌色/字体 | 建议 | 缺则沿用 `r10` 的 DESIGN.md 令牌 |

**追问纪律**：最多一轮，只问**讲给谁、核心结论是什么**。

---

## §3 执行流水线（Workflow）

### Step 1 · 结构校验（页数 + 首尾 + 每页结论）
```bash
python agent.py deck plan --input <deck.json>
```
四条硬规则，实测缺任一条即 FAIL：

| # | 规则 | 说明 |
|---|---|---|
| 1 | **页数 6–30** | 少于 6 讲不成事，多于 30 讲不完 |
| 2 | **封面在第 1 页**（`is_cover: true`） | 上来就讲内容＝没有落点 |
| 3 | **收尾在最后一页**（`is_closing: true`） | 没有收尾＝讲完就散了 |
| 4 | **每页有 `title` 与 `message`** | `message` 是该页的一句结论 |

**最容易漏的是 `message`**：只有标题的页面，讲的时候你会现编，
现编的内容和下一页大概率矛盾。

- **产出**：deck.json（结构合法）
- **过关条件**：`agent.py deck plan` 退出码 0

### Step 2 · 一页一件事（`message` 是结论不是主题）
| 反例（主题） | 正例（结论） |
|---|---|
| 「关于转化率」 | 「转化卡在 2%，主因是落地页跳出 78%」 |
| 「下一步计划」 | 「下季度只做续费，不做新客」 |

**判据**：`message` 如果拿掉动词还能成立，它就是主题不是结论。

### Step 3 · 每页 bullets ≤4（多了就不讲）
`bullets` 合计用于统计信息密度。单页超过 4 条，听众会开始读而不是听。

### Step 4 · 生成单文件 HTML
```bash
python agent.py deck html --input <deck.json>
```
产出**单文件 HTML**：样式内联、无外部依赖、离线可开、可直接投屏。
不要产出多文件工程——投屏现场最怕"少一个 css 就白屏"。

- **产出**：`deck.html`
- **过关条件**：双击能开、翻页正常、无外链

### Step 5 · 讲一遍（时间校验）
按每页 45–60 秒估算总时长。超时就砍页，不要加速讲。

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | deck.json（结构合法） | `.json` | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r08-wajiancheng-mvp/examples/deck.json` |
| 2 | 单文件 HTML | `.html` | `agent.py deck html` 产出 |
| 3 | 每页一句话结论清单 | `.md` | 本文 §3 Step 2 |

- 命名：`deck_<主题短码>_<YYYYMMDD>.html`
- **`message` 缺失的页面不算完成**；只有标题的页等于没想清楚。

---

## §5 质量门（一票否决，不过不给交付）

1. **页数 6–30**（`deck.count`）；
2. **封面在第 1 页**，`is_cover: true`（`deck.cover`）；
3. **收尾在最后一页**，`is_closing: true`（`deck.closing`）；
4. **每页有 title 与 message**（`deck.slide.title` / `message`）；
5. **每页 message 是结论句**，不是主题词；
6. **单页 bullets ≤4**；
7. **产出单文件 HTML**，无外部依赖。

> 验收命令：`python agent.py deck plan --input <deck.json>`
> 命中任一项不过 → 回 §3 对应 Step，**不允许删掉封面页让页数达标**。

---

## §6 交付前自检清单

- [ ] 页数在 6–30 之间，且我按 45–60 秒/页估过总时长
- [ ] 第 1 页是封面，标题与场合匹配
- [ ] 最后一页是收尾（结论/下一步/行动请求）
- [ ] 每页都有 message，且都是结论句不是主题词
- [ ] 单页 bullets ≤4
- [ ] 单文件 HTML 双击能开、翻页正常、无外链
- [ ] 我在投屏分辨率下看过（不是只在笔记本上看）
- [ ] 讲一遍没超过约定时长

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 页数 30+ 讲不完 | 6–30 页；按 45–60 秒/页算时长 |
| EX-02 | 没有封面直接讲内容 | 第 1 页必须是封面（`is_cover`） |
| EX-03 | 讲完没有收尾页 | 最后一页是收尾（`is_closing`） |
| EX-04 | 每页只有标题没有 message | 每页一句结论，写进 `message` |
| EX-05 | message 写主题（"关于转化"） | 写结论（"转化卡在 2%，主因是跳出 78%"） |
| EX-06 | 单页 8 条 bullets | ≤4 条，多了拆页或删 |
| EX-07 | 产出多文件工程 | 单文件 HTML，样式内联 |
| EX-08 | 依赖外部 CDN | 无外链，离线能开 |
| EX-09 | 只在笔记本分辨率下看 | 按投屏分辨率检查字号 |
| EX-10 | 时间不够就加速讲 | 砍页，不加速 |
| EX-11 | 每页信息量平均 | 论点页留白、数据页给足 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `agent.py` 门禁跑不了 | 按 §6 人工核对，标注「未跑门禁」；**不得标记"可讲"** |
| 素材不足（缺数据页） | 标注"待补数据"，不要用假数据填 |
| 页数被要求压到 6 页以下 | 说明"讲不成事"，给"拆成两场"的替代方案 |
| 需要动效/视频 | 明确不做，转外部工具 |
| 听众是外部客户 | 额外过 `r10` 的品牌一致性（`brand-guardian`） |
| 需要逐字讲稿 | 转 `r11` 的 `longform-article`，但讲稿≠页面 |

**明确不做**
- 不做长文/HTML 报告（归 `html-report-presentation`）；
- 不做 Excel/Word（归 `office-plugin`）；
- 不做动效视频；
- 不写逐字讲稿（归 `longform-article`）。

---

## §9 资源地图（按需读取，禁止全量加载）

| 什么时候需要 | 读哪个文件 |
|---|---|
| 正例（6 页、封面首、收尾末） | `tests/deck-pass.json` |
| 反例（2 页、标题空、封面不在首） | `tests/deck-fail.json` |
| 工程细节与子命令 | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r08-wajiancheng-mvp/references/engineering-notes.md` |
| 品牌色与字体 | `r10` 的 `DESIGN.md` / `brand-guardian` |
| 门禁是否还有效 | `scripts/gate_selftest.py --self-test` |
| 负向用例 | `tests/misuse.md` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言 `deck plan` 对正/反例的退出码 | `--self-test` / `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 从能力卡升级为十节技能包。
  **新增夹具**（此前无任何 deck 夹具）：`tests/deck-pass.json`（6 页，实测 exit 0）/
  `tests/deck-fail.json`（2 页，实测 exit 1）。
  含 §1–§10、`scripts/gate_selftest.py`、`tests/misuse.md`。
  门禁复用 `agent.py deck`（plan / html），未新增判定实现。
- v1.0（此前）：能力卡形态（`README.md`，无 frontmatter/触发语/夹具）。
