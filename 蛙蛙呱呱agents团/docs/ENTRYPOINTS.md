# 入口清单（ENTRYPOINTS）

> 对外只承诺**一个**入口。其余命令与模块都是内部实现或诊断工具，随重构调整，不承诺兼容。

## 一、唯一对外入口

```bash
# 已有干净数据（CSV/JSON）的快捷路
python guagua.py report "你的问题" --dir <项目数据目录> --out <输出目录> [--pdf]

# 显式写法（等价）
python guagua.py report run-line --intent "你的问题" --dir <项目> --out <目录>
```

判定与产物：

- 输入模式写入 `<out>/input_mode.json`
- 报告写出 `<out>/report.html`、`report.md`（`--pdf` 时另有 `report.pdf`）
- 审计单 `<out>/manifest.json`：producer、门禁结论、降级、文件清单
- **门禁结论只认 `manifest.gate` / `report attest`**，不在对话里口头宣布通过

## 二、拆卡线（默认产线，最短路径）

需要外部取证时，不走上面的快捷路，按四步走：

```bash
python guagua.py report clarify --intent "…" --out <项目>
python guagua.py report clarify --dir <项目> --confirm --user-said "用户原话"
python guagua.py report brief   --dir <项目> --plan --confirm --ack-cards
python guagua.py report collect --dir <项目> --out <输出目录>
python guagua.py report run-line --source cards --claims <merged.json> --out <输出目录>
```

硬门：brief 未签不拆卡；DoR 未过不发卡；没有 nonce/签名的卡不收；`--source cards`
必须带 `--claims`，`--source data` 不接受 `--claims`。

## 三、内部 / 诊断入口（不承诺兼容）

| 入口 | 用途 | 稳定性 |
|---|---|---|
| `python guagua.py roles / info / skills` | 看 20 角色与技能目录 | 内部 |
| `python guagua.py check` | 20 角色入口体检 | 内部 |
| `python guagua.py audit --full` | 报告线 + 升级线 CI | 内部 |
| `python guagua.py report capabilities / plan / gaps / charts` | 诊断，不出报告 | 内部 |
| `python guagua.py report attest --out <目录>` | 交付口径回填 | 内部（门禁结论用） |
| `python guagua.py report check --html <报告>` | 验一份成品 | 内部 |
| `python guagua.py report flow --project <项目>` | 项目自带 facts/charts 的加载器 | 内部 |
| `python scripts/ci_report_checks.py` | 全量 CI 闸门 | 内部（CI 用） |

`core/*` 下所有模块都是实现细节：import 路径以真子包为准（`core/report`、`core/data`、
`core/cards`、`core/claims`、`core/charts`、`core/sources`、`core/base`、`core/prose`），
不要引用已删除的平铺旧路径。

## 四、最小示例

```bash
python guagua.py report "区域市场经营分析" \
  --dir workspace/projects/demo/data \
  --out workspace/projects/demo/out \
  --pdf
```

产物：

```
out/
├── report.html
├── report.md
├── report.pdf
├── manifest.json
└── input_mode.json
```

## 五、新手先读

| 想知道 | 读 |
|---|---|
| 词是什么意思 | `docs/GLOSSARY.md` |
| 产线七个阶段 | `docs/REPORT-LINES.md` |
| 哪些门禁在跑 | `docs/GATES.md` |
| 模块接线真相 | `docs/_migration/wiring-truth.md` |
| 架构世代与删除条件 | `docs/ARCHITECTURE-LEDGER.md` |
