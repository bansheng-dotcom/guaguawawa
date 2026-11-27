> status: ARCHIVED · 2026-11-27 · 现行规则见 docs/README.md

# 数据 intake：来源分级与 quote 门禁（REPORT-DATA-INTAKE.md）

> 版本：v0.1 · 2026-11-17（P3 产物）
> 实现：`core/sources/research_intake.py`　｜　证据包：`core/data/evidence_pack.py`
> 产物：`data/quote_check.json`、`manifest.json` 的 `quotes`、`evidence_pack.json` 的 `source_records`

---

## 1. 一句话

**证据不能只是“能回溯”，还要“能回抓”。** 没有 quote 的来源，不能支撑头条断言。

---

## 2. 来源等级 A/B/C/D

| 等级 | 含义 | 能做什么 |
|---|---|---|
| **A** | 政府 / 官方 / 一手监测 | 可支撑头条断言；口径、期次、地区写全 |
| **B** | 行业协会 / 企业公告 / 券商研报 | 可支撑头条；注明机构、年份、口径 |
| **C** | 平台报价 / 媒体报道 / 抽样估算 | **只能做量级判断**；不能与 A 级混算 |
| **D** | 专家判断 / 模型假设 / 经验值 | 必须进 `assumptions`，给敏感性；不能写成事实 |

规则：

- 头条断言只能引 `A` / `B`；
- `C` 级只能进观察/量级，不进动作；
- `D` 级必须单列假设，不能冒充台账。

---

## 3. quote 规则

`data/sources.json` 每条来源建议带：

```json
{
  "id": "S01",
  "title": "…",
  "org": "…",
  "type": "government",
  "grade": "A",
  "url": "https://…",
  "quote": "富士苹果 14.00"
}
```

校验逻辑（`research_intake.verify`）：

1. 没有 `quote` → `unverified`，**不发请求**（拿标题当证据 = 假核验）；
2. 有 `quote` → 回抓 URL，把页面去标签/去空白后，检查 quote 是否是子串；
3. 命中 → `ok`；未命中 → `mismatch`；抓取失败 → `unreachable`；
4. 只校验 `only_ids` 指定的来源，其余标 `skipped`（避免整库回抓）。

**绝不把 `unreachable` / `mismatch` 改写成 `ok`。**

---

## 4. 门禁三档

| 模式 | 行为 | 用在哪 |
|---|---|---|
| `off` | 跳过 | 离线/CI 快速路径 |
| `warn` | 记录 `manifest.quotes`，不阻断 | P3 默认（sections / produce） |
| `strict` | 被引用来源有未核验 → `FlowError`，不出报告 | P4 起默认 |

命令：

```bash
# 只看 7 条 claim 来源
python -m core.sources.research_intake gate \
  --project "D:\蛙蛙呱呱\内蒙古水果三城调研_2026-11-16" \
  --refs "S01,S02,S03,S04,S06,S20,S27" --mode warn

# 整份报告
python guagua.py report run --intent "…" \
  --evidence "…\_pack\evidence_pack.json" \
  --draft "…\draft_sections.json" \
  --out out --quote-mode strict
```

---

## 5. 产物

### 5.1 `data/quote_check.json`

```json
{
  "total": 32,
  "checked": 5,
  "ok": 5,
  "mismatch": 0,
  "unreachable": 0,
  "unverified": 27,
  "skipped": 0,
  "grades": {"A": 14, "B": 3, "C": 15, "D": 0},
  "items": [{"id": "S01", "status": "ok", "quote": "富士苹果 14.00"}]
}
```

### 5.2 `manifest.json` 的 `quotes`

```json
{
  "mode": "warn",
  "ok": false,
  "verdict": "FAIL",
  "total": 32,
  "checked": 5,
  "ok_count": 5,
  "mismatch": 0,
  "unreachable": 0,
  "unverified": 27,
  "used_unverified": ["S05", "S06", "…", "S32"]
}
```

### 5.3 `evidence_pack.json` 的 `source_records`

每条带 `id / title / org / type / grade / url / quote / quote_status`。
`brief.md` 会多一张“来源等级与核验”表，模型写稿时能直接看到哪些来源不能当硬证据。

---

## 6. 水果项目当前状态（P3）

| 指标 | 值 |
|---|---|
| 来源 | 32 |
| A / B / C | 14 / 3 / 15 |
| 已回填 quote | 5（S01 / S02 / S03 / S04 / S20） |
| 回抓命中 | 5 / 5 |
| 未回填 | 27（全部 `unverified`） |
| mismatch | 0 |
| S06 / S27 | 政府页，抓取遇 SSL handshake failure；无 quote，仍标 unverified |

**warn 结果：** 报告可渲染，`manifest.quotes.ok=false`。
**strict 结果：** 阻断，点名 27 条未核验来源。

---

## 7. 已知残缺（P4 解决）

`draft_sections.json` 的 `refs` 是**派生量 id**（`D_common6_…`），不是来源 id（`S01`）。
所以 `collect_refs()` 为空，quote 门禁退化为“校验全部 32 条”，strict 会点名 27 条。

**P4 任务：** 建 `derived → source` 映射：

```
D_common6_呼和浩特_mean
  → formula/inputs → D_common6_n / 6品批发价
  → 底层 S01 / S03
```

这样 quote 门禁只校验“这条断言真正引用的 3–5 条来源”，strict 才有意义。

---

## 8. 回填流程（下次做新项目）

1. 每条来源写 `id / title / org / type / grade / url / quote`；
2. 跑 `python -m core.sources.research_intake verify --project <dir> --raw`；
3. 看 `data/quote_check.json`：`ok` / `mismatch` / `unreachable` / `unverified`；
4. `mismatch` 改 quote 或换来源；`unreachable` 换可访问镜像或降级；
5. 没有 quote 的来源，不许支撑头条断言；
6. 跑 `gate --mode strict`，全绿才发布。

---

## 9. 维护规则

- **quote 必须能在原文命中**：不命中就是 mismatch，不改成“大意如此”；
- **一条来源一个 quote**：多数字来源可加多个 quote，但每个 quote 都要能命中；
- **不把 C 级混进 A 级**：跨等级不可相加/相除；
- **抓取失败不伪造**：`unreachable` 就是 `unreachable`，报告写缺口；
- **strict 前先补 quote**：不要为了过门禁把 quote 写成页面标题——标题只能证明页面存在，不能证明数字。
