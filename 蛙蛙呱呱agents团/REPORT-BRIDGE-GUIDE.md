# 接入唯一报告产线（REPORT-BRIDGE-GUIDE）

> **P1/v11（2026-11-18）**：唯一入口是
> `python guagua.py report run-line --intent "…" --dir <项目> --out <目录>`；
> `build / decide` 为过渡别名（P5 删除），`run / pack / produce / research` 与 `--lens / --thesis` 已删除。
> 新角色/新能力的接入方式是：**在专家卡（`configs/experts.yaml`）里声明「能答什么、要什么数据」**，
> 由编排器决定是否出场——不再各自写报告。
> 本文件以下内容是旧接入说明，保留作历史对照。

> 2026-11-15 产线收敛；2026-11-17 校正本文与实际代码的偏差。
> 现实是三层，不是两层：
>
> ```
> 技能真实运行 → result.json
>         │
>         ▼
> role_runtime.emit()          ← 执行角色唯一出口：落 result.json + evidence.json（不写报告）
>         │
>         ▼
> R01 s09 解读（judge）        ← 决定这份报告说什么（带数字的结论/驱动/边界/动作）
>         │
>         ▼
> core/report_flow.build_contract()
>         │
>         ▼
> core/report_bridge.py        ← 渲染薄层：render_html / write_markdown / render_pdf
>         │
>         ▼
> core/report_renderer.py      ← 唯一 HTML 渲染器（48 型图 + 主题）
> ```
>
> `report_bridge.emit` **确实已删除**；但 `core/report_bridge.py` 作为「渲染薄层」仍在，
> 由 `core/report_flow.py` 调用。不要再新增第二套渲染/排版实现。

---

## 1. 新增角色要做的两件事

### 第 1 步：结尾调 `role_runtime.emit`

```python
from agents.shared import role_runtime  # 顶部

# run_task / 技能执行末尾：把本次真实结果交出去
outputs.extend(role_runtime.emit(
    role=ROLE, name=role["name"], title=role["title"],
    result=result, skill=skill_name, action=action, intent=intent,
    out_dir=out_dir, md_name="result"))
```

`emit` 写两个文件并返回一个 data Port：

- `<out_dir>/result.json` —— 本次技能结果（报告的唯一数据源）
- `<out_dir>/evidence.json` —— 谁、用什么技能、产出于何时、结果哈希

`md_name / html_name / dataset / data / report_slug` 这些历史参数仍然接受，但**不产报告**：
`data` 会另存为 `input.json` 供 R01 取用。

### 第 2 步：不要写报告

- 不要拼 markdown、不要生成 HTML、不要调用渲染器、不要新增角色专属模板。
- 有结论想表达，写进 `result` 的 `conclusion` / `insight` 字段——R01 解读时会引用它，
  但**必须带数字**，否则这条结论不会进报告。
- 角色目录里出现 `report.py` / `generate_html_report*.py` / `*.html` 成品，都是产线收敛前的残留，
  应删除（R03 的 `report.py` 已在 2026-11-17 移除）。

---

## 2. R01 解读怎么用你的 result

`r01/skills/s09_interpret.py` 会：

1. 递归收集 result 里的数值叶子，记下 `path`（如 `gmv.delta_pct`）与来源（`r06/semantics`）；
2. 优先引用你 `conclusion` 里点到的那个数字（按数值比对，符号/格式不敏感）；
3. 没有结论句时，用该 result 中绝对值最大的可复算数字兜底；
4. 每个数字都要能在结果里找到，找不到的数字会被校验驳回。

所以角色侧最该做的一件事：**在 `conclusion` 里写一句带数字的结论**。

```json
{
  "ok": true,
  "conclusion": "2月GMV环比下降 3.2%，主要由订单量下滑拖累",
  "gmv": {"feb": 512300, "jan": 529200, "delta_pct": -3.2}
}
```

---

## 3. 新增报告类型（不是新增产线）

报告只有一种结构（见 `REPORT-STANDARD.md` §五）。如果某类报告需要额外章节：

1. 在 `core/report_flow.build_contract()` 里加一节（带 `question` 与数字）；
2. 在 `scripts/check_report_flow.py` 里补对应判据；
3. 不要新开 CLI 子命令、不要新写渲染器。

---

## 4. 接入后的验收

> **2026-11-19 更正**：`report run --results` 自 v11 起已删除，仓内也没有任何模块读取
> 角色 `result.json` 进报告。**当前 `result.json` 只作审计留痕，不进报告产线**；
> 要把角色结论送进报告，走两条现役路径之一：
> ① 数据线 `report "指令" --dir <项目> --out <目录>`（方法库从原始数据作答）；
> ② 写稿线 `report "指令" --claims <claims.json> --out <目录>`（专家调研稿，含引文/来源）。
> 真桥接（result.json → evidence_pack）列入 P2，见 `交付/专家团产线体检-2026-11-19.md`。

```bash
# ① 角色入口不回归
python guagua.py check

# ② 让该角色真跑一次，拿到 result
python <role>/agent.py run --task <task_id>
ls <out_dir>            # 期望：result.json + evidence.json，不应有 report.html / report.md

# ③ 用现役产线出报告（二选一）
python guagua.py report "<意图>" --dir <数据项目> --out /tmp/flow_check        # 数据线
python guagua.py report "<意图>" --claims <claims.json> --out /tmp/flow_check  # 写稿线

# ④ 过唯一门禁
python guagua.py report check --html /tmp/flow_check/report.html
```

判据：

- 角色目录下**不应**出现 `.html` / `.md` 报告；
- `manifest.json` 里 `producer=r01`，`branch` 与参与角色数一致；
- `report check` 与 `python -m core.report_quality` 对同一文件给出**同一结论**
  （2026-11-17 起二者共用 `core/report_quality.PROFILES`，research / baseline 两档）。

---

## 5. 一页速查

```
新增角色：1) run_task 末尾调 role_runtime.emit   2) 不写任何报告
新增报告类型：改 build_contract + 门禁，不新开产线
铁律：报告只有一个作者（R01）；数字必须来自 result；HTML 渲染器只有 core 一份
历史：旧 report_bridge.emit / report_pipeline / report_engine 已删除
      （代码归档未随仓提供；需要时从 git 历史取）
```
