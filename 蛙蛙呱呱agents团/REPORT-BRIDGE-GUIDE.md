# 接入唯一报告产线（REPORT-BRIDGE-GUIDE）

> 2026-11-15 起，原来的「结果 → contract → 渲染」桥（`core/report_bridge.emit`）
> 已删除。角色不再出报告，只交证据；报告由 R01 在 `core/report_flow.py` 统一出具。
> 本文是给「新增角色 / 新增报告类型」维护者看的三步接入说明。

---

## 0. 一句话原理

```
技能真实运行 → result JSON
        │
        ▼
role_runtime.emit()          ← 执行角色的唯一出口：落 result.json + evidence.json
        │
        ▼
R01 s09 解读（judge）        ← 决定这份报告说什么（带数字的结论/驱动/边界/动作）
        │
        ▼
core/report_flow.build_contract()
        │
        ▼
core/report_renderer.py      ← 唯一渲染器（HTML + MD + manifest）
```

角色侧**没有任何**报告模板、报告 spec、报告引擎；只有 `result`。

---

## 1. 新增角色要做的两件事

### 第 1 步：结尾调 `role_runtime.emit`

```python
from agents.shared import role_runtime  # 顶部

# run_task 末尾：把本次技能真实结果交出去
outputs.extend(role_runtime.emit(
    role=ROLE, name="蛙得清", title="数据分析师",
    result=result, skill=skill_name, action=action, intent=intent,
    out_dir=out_dir, md_name="analysis_report"))
```

`emit` 会写两个文件并返回一个 data Port：

- `<out_dir>/result.json` —— 本次技能结果（报告的唯一数据源）
- `<out_dir>/evidence.json` —— 谁、用什么技能、产出于何时、结果哈希

`dataset / data / specialist / chart_dir` 这些历史参数仍然接受，但**不再影响出报告**，
只把 `data` 另存为 `input.json` 供 R01 取用。

### 第 2 步：不要写报告

- 不要拼 markdown、不要生成 HTML、不要调用渲染器。
- 不要新增 `report_contract.py` / 角色专属模板。
- 有结论想表达，写进 `result` 的 `conclusion` / `insight` 字段——R01 解读时会引用它，
  但**必须带数字**，否则这条结论不会进报告。

---

## 2. R01 解读怎么用你的 result

`s09_interpret` 会：

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

```bash
# ① 角色入口不回归
python guagua.py check

# ② 让该角色真跑一次，拿到 result
python <role>/agent.py run --task <task_id>
ls <out_dir>            # 期望：result.json + evidence.json，不应有 report.html

# ③ 用它跑产线
python guagua.py report run --intent "<意图>" \
    --results <out_dir>/result.json --out /tmp/flow_check

# ④ 过门禁
python guagua.py report check --html /tmp/flow_check/report.html
```

判据：
- 角色目录下**不应**出现 `.html` / `.md` 报告；
- `manifest.json` 里 `producer=r01`、`branch` 与参与角色数一致；
- 门禁九条全过。

---

## 5. 一页速查

```
新增角色：1) run_task 末尾调 role_runtime.emit   2) 不写任何报告
新增报告类型：改 build_contract + 门禁，不新开产线
铁律：报告只有一个作者（R01）；数字必须来自 result；渲染器只有 core 一份
历史：旧 report_bridge.emit / report_pipeline / report_engine 已删除
      （归档见 workspace/_archive/report-lines-2026-11-15.tar.gz）
```
