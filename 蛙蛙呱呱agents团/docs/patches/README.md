# docs/patches · 未应用的补丁归档

本目录存放**尚未合入**的补丁草案。合入后请删除对应文件，并在提交信息里注明。

| 文件 | 目标 | 状态 |
|---|---|---|
| `PROTOCOL_PATCH.diff` | `PROTOCOL.md` | **未应用**（2026-11-11 归档） |

## PROTOCOL_PATCH.diff 说明

原文件放在仓库根目录，是一份手写 diff，内容是把 `PROTOCOL.md` 第〇节总原则第 1 条
从「编排器必须瘦（R04 只做四件事）」改写成「编排器必须是大脑（Mission Control）」，
要求 R01 下发任务前先调 `core/dynamic_orchestrator.py` 输出作战阵型，并强制约定产物格式。

**未应用的原因**：

1. 该 diff 是手写片段，`git apply --check` 报 `patch fragment without header`，无法直接套用；
2. 其中描述的 `dynamic_orchestrator` 能力**代码已存在**（`core/dynamic_orchestrator.py`），
   缺的只是 `PROTOCOL.md` 的正文同步；
3. `PROTOCOL.md` 是协同协议权威文件，改它需要与 `core/protocol.py` 和 20 个角色的契约一并核对。

**处置建议**：人工比对后重写 `PROTOCOL.md` 第〇节，再删除本文件；不要直接 `git apply`。
