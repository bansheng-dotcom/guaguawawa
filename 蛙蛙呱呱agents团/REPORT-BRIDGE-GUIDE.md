# 报告桥接入指导（REPORT-BRIDGE-GUIDE）

> 适用对象：任何**新增角色**、或**要把某个角色接入统一报告渲染**的维护者。
> 目标：让 20 个角色产出的每一份报告，都从「技能真实运行结果」确定性生成
> **HTML（正式稿）+ Markdown（快读稿）**，而不是把 result JSON 裸拍成 markdown。

---

## 0. 一句话原理

```
技能真实运行 → result JSON
        │
        ▼
  report_bridge.emit()          ← 每个角色 run_task 末尾只调这一个函数
        │
        ├─ specialist(result,…)  → report contract（精细映射，可选）
        └─ generic_contract(…)   → report contract（保底通用映射）
        │
        ▼
  core/report_renderer.py       ← 唯一的确定性渲染器（HTML）
        │
        ├─ .html  正式稿（带图表 / 排版 / 可追溯）
        └─ .md    结论先行快读稿
```

**为什么要有这一层**：过去 19/20 个角色在 `run_task` 末尾把 result 直接
`## 字段名` + ```json 代码块拍出去——那是日志，不是汇报。编辑器级报告
（`REPORT-STANDARD.md` 要求的五件套）只存在于手工写的样例里，没接进运行时。
报告桥就是补上这条「result → contract → 渲染」的缺失管道。

---

## 0.1 引擎路由（2026-11-12 起，必读）

`emit()` 现在按角色**自动选引擎**，两者共用一个渲染器：

| 条件 | 引擎 | 产物特征 |
|---|---|---|
| 有 `report_specs/roles/<role>.yaml` 且不在 `configs/legacy_roles.txt` | **内核**（`core/report_kernel`） | 规格校验 + 保真分数 + 版式四规则 + 记录层折叠，可 `seal`/`diff` |
| 否则（或内核抛错） | REP-001 五段式（`shared/report_engine.py`） | 三级归因 + 熔断三档 + provenance |

```bash
GUAGUA_REPORT_ENGINE=legacy python agent.py ...   # 强制回滚旧引擎
GUAGUA_REPORT_ENGINE=kernel python agent.py ...   # 强制内核（缺 spec 会回落并留 WARN 日志）
```

- 每次出报告都会在 `workspace/logs/<role>.jsonl` 记一行 `report_emitted`，`payload.engine` 写明走了哪条；
  内核失败回落时额外记 `report_kernel_fallback`（WARN）并带 `kernel_error`，**不静默**。
- 两个引擎都只调用 `core/report_renderer.py`，所以「唯一渲染器」不变。
- 新角色接入仍按本文 §2 三步走；有 spec 的角色会自动走内核，不需要额外代码。

---

## 1. 三件东西，先认脸

| 文件 | 角色 | 谁该改 |
|---|---|---|
| `core/report_bridge.py` | 报告桥本体，**全组织共享，一般不动** | 只在扩展能力时动 |
| `core/report_renderer.py` | 唯一渲染器，contract → HTML | 一般不动 |
| `<role>/report_contract.py` | **该角色的精细映射**（可选） | 新角色按需新建 |
| `<role>/agent.py` | 在 `run_task` 末尾调 `report_bridge.emit` | **必改** |

---

## 2. 接入三步（新角色 / 未接入角色）

### 第 1 步：在 `agent.py` 顶部导入

在已有的 `from core import …` 附近加两行（保持 `# noqa: E402` 风格一致）：

```python
from core import report_bridge  # noqa: E402
import report_contract          # noqa: E402   ← 若本角色有精细映射才加这行
```

### 第 2 步：替换 `run_task` 末尾的报告块

**删除**原来手拼报告的那几行（典型长这样，四种反模式之一）：

```python
# ❌ 反模式 A：裸转 JSON（R01/R07/R08/R10-R20 旧代码）
_write_report(result, "标题", report_path)

# ❌ 反模式 B：列表拼行，正文只有五个短横线（R04/R05/R09 旧代码）
report = [
    f"# R04 run --task {task_id}",
    f"- intent: {intent}",
    f"- 路由: {skill}/{action}",
    f"- verdict: {out.get('verdict')}",
    f"- 结论: {out.get('next')}",
]
c.write_text(report_path, "\n".join(report) + "\n")

# ❌ 反模式 C：f-string 拼描述，无证据无指标（R02 旧代码）
content = (
    f"# 蛙排布 · {title}\n\n"
    f"- 任务：{t.intent}\n"
    f"- 路由技能：{skill}（{note}）\n")
with open(artifact_path, "w", encoding="utf-8") as f:
    f.write(content)
```

**换成**（以 R06 为例，标准写法）：

```python
ports = report_bridge.emit(
    role=ROLE, name="蛙得清", title="数据分析师",
    result=result, skill=skill_name, action=action, intent=intent,
    out_dir=out_dir, md_name="analysis_report",
    specialist=report_contract.r06_contract,   # ← 有精细映射才传
    chart_dir=_HERE,                           # ← 要出图才传（目录内须有 chart_lib.py）
)
outputs.extend(ports)
```

只有一个技能产出、没有精细映射的简单角色（如 R01/R08/R10-R20）：

```python
ports = report_bridge.emit(
    role=ROLE, name="蛙全局", title="CEO 主理人编排器",
    result=result, skill=skill_name, action=action, intent=intent,
    out_dir=out_dir, md_name="ceo_report")
outputs.extend(ports)
```

### 第 3 步：把 ports 落进 task outputs

`emit()` 返回的是 `[Port(md), Port(html)]` 两个 Port。已有的 `outputs` 列表
`extend` 进去即可，后面原有的 `ws.update_task(...)` / `ws.emit(...)` 不用动：

```python
outputs: List[protocol.Port] = []
outputs.append(protocol.Port(f"{skill_name}.json", "data"))
ports = report_bridge.emit(...)     # 新增
outputs.extend(ports)               # 新增
ws.update_task(task_id, {"outputs": [p.to_dict() for p in outputs], "status": "done"})
```

---

## 3. `report_bridge.emit()` 参数表

```python
emit(role, name, title, result, skill, action, intent, out_dir,
     md_name, html_name=None, specialist=None, chart_dir=None,
     data=None, doc_type="角色报告") -> List[Port]
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `role` | ✓ | 角色 id，如 `"r06"` |
| `name` | ✓ | 角色名，如 `"蛙得清"` |
| `title` | ✓ | 职位，如 `"数据分析师"` |
| `result` | ✓ | 技能的 result dict（`run_task` 里那个） |
| `skill` / `action` | ✓ | 技能名 / 动作名 |
| `intent` | ✓ | 任务卡意图文本 |
| `out_dir` | ✓ | 产物目录（`ws.artifact(task_id)`） |
| `md_name` | ✓ | md 基名（不带 `.md`），如 `"analysis_report"` |
| `html_name` | ✗ | 默认 `md_name + ".html"` |
| `specialist` | ✗ | 精细映射函数，见 §4 |
| `chart_dir` | ✗ | 含 `chart_lib.py` 的目录（出图时传，通常 `_HERE`） |
| `data` | ✗ | **技能的输入 JSON**。仅 PRD 类角色需要（内容在输入不在 result） |
| `doc_type` | ✗ | 报告品类，默认 `"角色报告"` |

---

## 4. 精细映射 `report_contract.py`（可选，但推荐给"结论型"角色）

**什么时候需要**：result 里已经是结构化的业务对象（趋势序列、分组、漏斗、
贡献分解、AB 实验、PRD 各字段……），通用映射摊出来的表不够"像人写的汇报"。

**契约签名**（两种，桥都兼容）：

```python
def rXX_contract(result, skill, action, intent, data=None) -> dict | None:
    ...
```

- 返回 `None` → 自动回退 `generic_contract`（保底，永不出空报告）。
- 桥内部先按 5 参调用；若函数只接受 4 参（抛 `TypeError`），自动退回 4 参。
- 函数内部抛任何异常都会被吞掉并回退通用映射，**桥不会因映射失败而挂**。

**返回的 contract 必须满足** `core/report_renderer.py` 的 schema：
```python
REQUIRED_TOP     = ["doc_type","title_lines","standfirst","metric_strip",
                    "summary","sections","notes","footer"]
REQUIRED_METRIC  = ["label","value","note"]     # note 不能是空串！
REQUIRED_SECTION = ["index","title","question"]
```

**踩坑备忘**：
- `metric` 的 `note` **不能为空**——渲染器用 `not m.get(k)` 判缺，空串会报错。
  保底写 `"note": "输出字段"`。
- section 里图表结构随类型不同（`chart` / `table` / `reading` / `boundary`），
  照 `r06/report_contract.py`（数据类）和 `r07/report_contract.py`（PRD 类）抄。

**已实现的精细映射**（照抄范本）：

| 角色 | 文件 | 覆盖动作 | 图表 |
|---|---|---|---|
| R06 蛙得清 | `r06/report_contract.py` | trend/groupby/funnel/decompose/abtest | line / hbar / funnel / vbar |
| R07 蛙得明 | `r07/report_contract.py` | prd/story、rice/ice、northstar | 表格为主 |
| R03 蛙守贤 | `r03/report.py`（`recon_contract`） | 财务对账 | 桥的前身，模式参考 |

---

## 5. 通用保底映射 `generic_contract()` 行为（不用你写）

任何 result 进来，都会得到一个**能读**的报告：

1. **结论先行**：依次找 `conclusion/next/summary/insight/finding/
   recommendation/message/answer` 等人话字段；找不到就用门禁汇总合成
   （`门禁通过：N/M`）。
2. **metric_strip**：第一个永远放「门禁 PASS/FAIL + N/M 项」，
   再挑最多 3 个顶层标量字段。
3. **sections**：逐个非元字段成节；`list[dict]` 自动摊成证据表，
   标量摊成 reading。
4. **元字段过滤**：`ok/checks/runtime_ms/task_id/skill/action/type/note/
   verdict/error/raw…` 不进正文，避免把日志拍进报告。

---

## 6. 接入后的验收清单

对每个接线后的角色跑一遍：

```bash
cd <repo>/<role>
export PYTHONUTF8=1

# ① 冒烟：manifest 不报错
python agent.py manifest >/dev/null && echo OK-manifest

# ② 真跑一个任务卡
python agent.py run --task <存在且归属该角色的 task_id>

# ③ 看产物：目录下应同时有 .md 和 .html
ls workspace/artifacts/<task_id>/
#   期望：xxx_report.md（结论先行，有指标表）
#         xxx_report.html（正式稿，字节数明显 >  md）

# ④ HTML 不能是空壳：至少含标题 / 指标条 / 至少一节
grep -c "metric" <out>.html

# ⑤ 回归
python run_tests.py
```

**判据**（对齐 `REPORT-STANDARD.md`）：
- md 第一屏是「结论」+ 关键指标表，**不是** JSON 代码块。
- html 大小通常 **> 15KB**（含内嵌 SVG/图表）；几百字节 = 渲染失败。
- `.contract.json` 中间文件若残留，属正常调试产物，可清理。

---

## 7. 全局渲染器与本地副本（务必避免）

**唯一真渲染器** 是 `core/report_renderer.py`。历史上有角色目录里带了
本地副本（如 `r06/report_renderer.py`），会造成"改了一份、另一份没改"的
分叉。**接入时一律走 `report_bridge`**，它内部 `subprocess` 调用 core 版；
**不要在角色目录里再放渲染器副本**。若发现副本，删除之。

---

## 8. 一页速查

```
新增/未接入角色要做的：
1) agent.py 顶部  import report_bridge（+ report_contract）
2) run_task 末尾   删掉手拼报告 → 调 report_bridge.emit(…) → outputs.extend(ports)
3) （可选）写 report_contract.py 精细映射，返回 None 即自动保底
4) 跑 manifest / run / run_tests，确认 .md 结论先行 + .html >15KB

铁律：
· contract 的 metric.note 不能为空串
· 图表目录（chart_dir）里要有 chart_lib.py
· 渲染器只有 core 一份，角色目录不放副本
· result 里是业务结构化对象时，才值得写 specialist
```

---
_文档版本：v1 · 依 `REPORT-STANDARD.md` 与 `core/report_bridge.py` 现状编写。_
