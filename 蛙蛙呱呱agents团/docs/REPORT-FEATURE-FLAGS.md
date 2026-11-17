# 报告产线 feature flags（REPORT-FEATURE-FLAGS.md）

> 版本：v0.1 · 2026-11-17（P9）
> 目的：出问题时能降级，而不是只能回滚整个 commit。

## 1. 开关

| 变量 | 取值 | 默认 | 作用 |
|---|---|---|---|
| `REPORT_ENGINE` | `v9` / `v10` | `v9` | 当前唯一引擎；`v8` 已下线，传 `v8` 直接报错 |
| `REPORT_QUOTE_GATE` | `0` / `1` | `1` | `0` = 临时关闭 quote 门禁（等同 `--quote-mode off`） |
| `REPORT_CLAIM_GATE` | `0` / `1` | `1` | `0` = 临时关闭 ClaimCard 头条门禁 |

## 2. 用法

```bash
# 临时关闭 quote 门禁（只用于排障/回滚）
REPORT_QUOTE_GATE=0 python guagua.py report build --intent "…" --dir <项目> --out <目录>

# 临时关闭 claim 头条门禁
REPORT_CLAIM_GATE=0 python guagua.py report build --intent "…" --dir <项目> --out <目录>
```

PowerShell：

```powershell
$env:REPORT_QUOTE_GATE="0"
python guagua.py report build --intent "…" --dir <项目> --out <目录>
Remove-Item Env:REPORT_QUOTE_GATE
```

## 3. 回滚

- `REPORT_ENGINE=v8` **不可用**：v8 代码已删除；回滚用 git tag：
  ```bash
  git checkout report-line-v10-pre-delete
  ```
- quote/claim 开关只影响门禁，不改数据、不改报告结构。

## 4. 旧 CLI 别名（P9 起保留一个版本）

| 旧命令 | 现在 | 行为 |
|---|---|---|
| `report produce` | `build --lens` | 打印 deprecation，按旧 `--thesis` 映射 lens |
| `report pack` | `report build` 内部的证据包 | 仍产出 evidence_pack + brief |
| `report research` | `build --lens market` | 打印 deprecation |
| `report run` | 仅 `evidence + draft` | 无 evidence 直接报错，提示用 build |

别名不是长期 API；下一个大版本删除。
