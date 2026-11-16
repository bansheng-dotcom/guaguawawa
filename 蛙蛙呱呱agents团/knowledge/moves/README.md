# Move 库：把「书里的分析动作」变成可执行、可证伪、可回归的卡片

> 这不是书摘库。**一条 move = 一个在特定数据形状下、能改变结论的分析动作**。
> 书摘只回答「书里说了什么」；move 必须回答「什么时候用、怎么算、什么情况下错、
> 落在哪行代码、用哪个真实项目回归」。

## 一条 move 的五个落点

| 落点 | 在哪 | 不落会怎样 |
|---|---|---|
| 方法 | `core/methods/*.py` 的 `@method` | 只是文档，产线不会执行 |
| 论证 | `core/claims.py` 的 `kind` / 机理函数 | 有数但说不出为什么 |
| 问题链 | `core/frames.py` 或 `report_thesis.THESES` | 报告里没有这一节 |
| 门禁 | `core/report_quality.py` / `check_report_flow.py` | 下次改坏没人拦 |
| 回归 | `tests/test_*.py` 的具体函数 | 无法证明它还在工作 |

## 卡片状态

| 状态 | 含义 | 允许缺什么 |
|---|---|---|
| `draft` | 已读书、已写清动作，但代码未接 | 允许 method 为 `none`，test 可只到文件 |
| `active` | 已接入产线、有真实项目回归 | **method / test 函数 / 验收断言必须全部存在** |
| `retired` | 被更好的 move 替代 | 保留卡片与替代关系，不删 |

## 新增一条 move（10 分钟版）

1. 复制 `_template.json`，按 `M-<域>-<序号>.json` 命名；
2. 填 `source` 到「概念」而不是「整本书」；
3. `procedure` 写成 3—5 个动词开头的步骤，每步能被别人复现；
4. `counterexample` 必须写出「什么数据形状下这条 move 会错」；
5. `landing` 填真实路径；`status=active` 前先写回归；
6. 跑 `python scripts/check_move_cards.py`，全绿才算入库；
7. 在 SOP 的书目表里登记「书 → move → 落点」。

## 校验

```bash
python scripts/check_move_cards.py
python scripts/check_move_cards.py --json
```

校验会拦：缺来源、步骤少于 3、没有反例、结论等级非法、`active` 卡片的
代码路径或测试函数不存在、id 重复或不符合命名。
