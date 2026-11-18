# 报告产线 feature flags（REPORT-FEATURE-FLAGS.md · v11）

> 2026-11-18（P1 后重写）。**先说结论：现在真正生效的开关只有 2 个，其余随死代码一起删了。**
> 旧版本把「曾经写过的环境变量」当成了「可用开关」，这是漂移的来源；本版按「有没有消费者」重列。

## 1. 仍然生效

| 变量 | 取值 | 默认 | 作用 | 消费者 |
|---|---|---|---|---|
| `REPORT_QUOTE_GATE` | `0` / `1` | `1` | `0` = 关闭 quote 门禁（等同 `--quote-mode off`） | `core/report_flow.py`（evidence+draft 路径） |
| `KEEP_TMP` | `0` / `1` | `0` | `1` = 保留 `<out>/_work/` 中间产物，便于排障 | `core/decision_report.py` |

## 2. 已删除（P1）

| 变量 | 为什么删 | 原消费者 |
|---|---|---|
| `REPORT_ENGINE` | v8/v9 引擎已不存在，只剩一条路 | `core/report_build.py`（已删） |
| `REPORT_CLAIM_GATE` | 它只控制 `report_compose.build()` 的头条门禁，而该路径已删 | `core/report_compose.py`（已删） |
| `REPORT_CLAIM_CARD_GATE` | 同上 | `core/claim_gate.py`（已无调用方） |
| `ALLOW_LEGACY_COMPOSE` | P1.3 的临时封口开关；`report_compose` 已整份删除，开关随之失效 | — |

**回滚方式不再是环境变量**：用 git tag。P1 的基线 tag 是 `pre-P1-20261118`。

## 3. 用法

```powershell
# 临时关闭 quote 门禁（只用于排障）
$env:REPORT_QUOTE_GATE="0"
python guagua.py report run-line --intent "…" --dir <项目> --out <目录>
Remove-Item Env:REPORT_QUOTE_GATE

# 保留中间产物
$env:KEEP_TMP="1"
python guagua.py report run-line ...
```

## 4. 纪律

- 新增开关必须同时具备：**消费者代码 + 一行验收命令 + 默认值说明**，否则不许写进本文；
- 开关只允许「降级到更保守的行为」，不允许「跳过门禁拿绿灯」；
- 每删一个消费者，必须同步删本文对应行（P1 就是欠了这一条才长出 4 个假开关）。
