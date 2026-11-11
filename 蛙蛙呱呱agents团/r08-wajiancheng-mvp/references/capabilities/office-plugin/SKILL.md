---
name: office-plugin
description: Office 交付物技能包。把「导个表/写个文档」变成可校验的交付：xlsx 必须多表带表头且行宽与表头一致、输出扩展名合法、默认不覆盖同名文件（需 --force）；docx 必须有标题、分节与文档属性。当需要出 Excel 工作簿、Word 文档，或判断一份 Office 文件能不能直接发给外部时使用。不负责 HTML 报告与幻灯片（见 html-report-presentation / ppt-generator）、不做 PDF 排版精修。
license: MIT
compatibility: 通用。门禁在角色根目录 agent.py（office probe / office xlsx / office docx），写盘需要 openpyxl / python-docx；缺库时 `office probe` 会如实报缺失，不得伪造生成。
metadata:
  owner: r08
  version: "2.0.0"
  kind: skill
  triggers: "Excel,Word,xlsx,docx,工作簿,交付物,防覆盖,表头"
  verify: python agent.py office xlsx --input tests/xlsx-pass.json --out tests/_out.xlsx
  entry: "python agent.py office xlsx"
  consumers: "r03,r06,r16"
  supersedes: "README.md"
---

# Office 交付物（Office Plugin）

> 一句话定位：**这个技能存在的意义，是防止「表导出来了，但没有表头、行数错位、还覆盖了原文件」**。
> Office 交付物最贵的失败不是格式，而是**不可用**：
> 表头缺失导致别人读不懂列、行宽与表头不一致导致错列、
> 默认覆盖同名文件导致上一版没了。这些都能在生成前判掉。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「导个 Excel 给我」「做个多表工作簿」
- 「写成 Word 文档」「加个文档属性」
- 「这个表能直接发客户吗」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 网页报告 | 本角色的 `html-report-presentation` | 那是 HTML |
| 幻灯片 | 本角色的 `ppt-generator` | 那是 deck |
| PDF 排版精修 | 外部 / `office-export-pdf` 技能 | 本包只出原生 Office 文件 |
| 数据口径校验 | `r06` 的 `data-validation` | 那是质量门禁 |

**最小可开工输入**：**X 里要哪几列 + 给谁看**。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| `sheets[]`（xlsx）| 必需 | 无表无法生成 |
| 每表 `headers[]` | 必需 | 门禁要求表头 ≥1 列 |
| 每表 `rows[]` | 必需 | 行宽必须与表头一致 |
| `--out` 路径（含 `.xlsx`/`.docx`） | 必需 | 扩展名不合法会被拦 |
| docx 的 `title` / `sections[]` | 必需（docx） | 无标题无法定调 |

**追问纪律**：最多一轮，只问**要哪几列、发给谁**。

---

## §3 执行流水线（Workflow）

### Step 0 · 先探测依赖（不探测就动手＝赌博）
```bash
python agent.py office probe
```
实测会报 `openpyxl` / `python-docx` 是否可用。
**缺库时如实报缺失，不得伪造生成**——一个空文件比报错更糟。

### Step 1 · xlsx：多表 + 表头 + 行宽一致
```bash
python agent.py office xlsx --input <表.json> --out <输出.xlsx>
```
实测五项，缺任一即 FAIL：

| # | 规则 | 判据 |
|---|---|---|
| 1 | 输出扩展名 `.xlsx` | `office.ext` |
| 2 | 默认不覆盖（需 `--force`） | `office.overwrite` |
| 3 | 工作表 ≥1 | `office.sheets` |
| 4 | 每表表头 ≥1 列 | `office.headers` |
| 5 | 行宽与表头列数一致 | `office.rows` |

**行宽错位是最隐蔽的坑**：少一格会让整行数据左移，
表面上"生成了"，实际每行都配错了列。

- **产出**：`.xlsx`
- **过关条件**：`agent.py office xlsx` 退出码 0

### Step 2 · 表头是给人读的
表头不要用 `col1/col2` 或字段名（`gmv_usd`）；写业务人能懂的词。
数字列要标明单位与口径（"金额（元，含税）"）。

### Step 3 · docx：标题 + 分节 + 属性
```bash
python agent.py office docx --input <文档.json> --out <输出.docx>
```
要求：`title` 非空、`sections[]` 有内容、`meta` 带文档属性（作者/日期）。
文档属性不是形式主义——外发时它决定了"这是谁什么时候出的哪一版"。

### Step 4 · 版本与命名（外发前最后一步）
命名带日期与版本：`<主题>_v<N>_<YYYYMMDD>.xlsx`。
**不要用"最终版""最终版2"**——那是无法排序的命名。

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | xlsx 工作簿（多表、带表头） | `.xlsx` | `tests/xlsx-pass.json` |
| 2 | docx 文档（标题+分节+属性） | `.docx` | 同目录骨架 |
| 3 | 列口径说明（单位/含税/时间窗） | `.md` | 本文 §3 Step 2 |

- 命名：`<主题>_v<N>_<YYYYMMDD>.xlsx`
- **列口径说明必须随文件交付**；只有表，别人不知道数字怎么来的。

---

## §5 质量门（一票否决，不过不给交付）

1. **`office probe` 确认依赖可用**（否则如实报缺失）；
2. **输出扩展名与格式匹配**（`.xlsx` / `.docx`）；
3. **不覆盖同名文件**（默认拦，需 `--force`）；
4. **工作表 ≥1，每表表头 ≥1 列**；
5. **每行宽度与表头列数一致**；
6. **docx 有 title 与 sections**，`meta` 带作者/日期；
7. **列口径（单位/含税/时间窗）写明**。

> 验收命令：`python agent.py office xlsx --input <表.json> --out <文件.xlsx>`
> 命中任一项不过 → 回 §3 对应 Step，**不允许用 `--force` 覆盖上一版来"省事"**。

---

## §6 交付前自检清单

- [ ] 我先跑过 `office probe`，知道依赖在不在
- [ ] 输出扩展名是 `.xlsx` / `.docx`，不是 `.xls` / `.doc`
- [ ] 我没有覆盖同名文件（或已确认要覆盖并备份）
- [ ] 每个表都有表头，且表头是业务人能读的词
- [ ] 每行宽度与表头列数一致（错位会让整列配错）
- [ ] 数字列标了单位与是否含税
- [ ] docx 有标题、分节、作者与日期属性
- [ ] 文件名带版本与日期，不是"最终版"
- [ ] 列口径说明已随文件交付

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 表头写 `col1/col2` 或字段名 | 写业务人能懂的词 |
| EX-02 | 某些行少一格 | 行宽必须与表头一致，缺值填空 |
| EX-03 | 默认覆盖同名文件 | 默认新路径；覆盖需 `--force` 且先备份 |
| EX-04 | 用 `.xls` / `.doc` 扩展名 | 与格式匹配：`.xlsx` / `.docx` |
| EX-05 | 数字列不标单位/含税 | 表头写明"金额（元，含税）" |
| EX-06 | docx 无标题无分节 | title + sections + meta |
| EX-07 | 文件名"最终版2" | `<主题>_v<N>_<YYYYMMDD>` |
| EX-08 | 缺库却生成空文件 | 如实报缺失，不伪造 |
| EX-09 | 一个表塞 30 列 | 拆表；单表列数受控 |
| EX-10 | 只有表没有口径说明 | 随文件交付列口径说明 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| 缺 openpyxl / python-docx | `office probe` 如实报缺失，给安装命令；**不生成空文件** |
| 需要 `.xls`/`.doc` 旧格式 | 说明只支持 OOXML，给出另存建议 |
| 需要复杂公式/透视表 | 生成静态值并在口径说明里写"公式未内嵌" |
| 需要 PDF | 转 `office-export-pdf` 技能或外部转换 |
| 要覆盖已有文件 | 先备份到 `_orig/`，再 `--force` |
| 数据涉密 | 脱敏或标注"含敏感字段，勿外发" |

**明确不做**
- 不做 HTML 报告（归 `html-report-presentation`）；
- 不做幻灯片（归 `ppt-generator`）；
- 不做 PDF 排版精修；
- 不做数据质量校验（归 `r06`）。

---

## §9 资源地图（按需读取，禁止全量加载）

| 什么时候需要 | 读哪个文件 |
|---|---|
| 正例（两表带表头、行宽一致） | `tests/xlsx-pass.json` |
| 反例（sheet 无表头/无数据） | `tests/xlsx-fail.json` |
| 工程细节与子命令 | `../../../references/engineering-notes.md` |
| 依赖探测 | `python agent.py office probe` |
| 门禁是否还有效 | `scripts/gate_selftest.py --self-test` |
| 负向用例 | `tests/misuse.md` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言 `office xlsx` 对正/反例的退出码（写入临时目录并清理） | `--self-test` / `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 从能力卡升级为十节技能包。
  **新增夹具**（此前无任何 Office 夹具）：`tests/xlsx-pass.json`（两表带表头，实测 exit 0）/
  `tests/xlsx-fail.json`（无表头无数据，实测 exit 1）。
  自检会写 `tests/_out.xlsx` 并在结束后清理，避免污染仓库。
  含 §1–§10、`scripts/gate_selftest.py`、`tests/misuse.md`。
  门禁复用 `agent.py office`（probe / xlsx / docx），未新增判定实现。
- v1.0（此前）：能力卡形态（`README.md`，无 frontmatter/触发语/夹具）。
