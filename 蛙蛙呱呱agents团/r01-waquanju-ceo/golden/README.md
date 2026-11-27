# R01 黄金成品（golden）：经营决策包 + 运行账本

两份 HTML 都不是手写稿，由 `run_manifest.py` 跑一遍 8 阶段账本产线后导出；
`golden/artifacts/` 里是账本登记的真实工件（来自 `examples/`，确定性、无联网）。

```bash
cd r01-waquanju-ceo
python run_manifest.py goldens                      # 重建两份 HTML + run-manifest.json
python run_manifest.py verify --file golden/run-manifest.json --dir golden   # 重算 sha256
python run_manifest.py trace  --file golden/run-manifest.json                # 逐步追踪
```

| 文件 | 内容 | 验收点 |
|---|---|---|
| `decision-pack.html` | 经营决策包：结论先行、决策链、工件与可追性、边界 | 标题层级不跳级；表头 `<thead>/<th>` 齐；结论含代价与灰度回滚 |
| `run-manifest.html` | 运行账本：8 阶段 × 输入 × 工件 sha256 × 决策 × 签名位 | 每个工件有 sha256；不可逆阶段有签名位；M02/M04/M05/M06 门禁明细 |
| `run-manifest.json` | 机器可读账本（`guagua.run-manifest/v1`） | `verify --dir golden` 全过；工件被手改会以 M05 失败 |

## 账本产线（8 阶段）

`intent → decompose → decide → redteam → companyos → decisionlog → boardroom → deliver`

- 每阶段必须有决策（M03）；输入必须由更早阶段产出（M04）；工件必须有 64 位 sha256（M02）；
- 不可逆阶段（boardroom 动资金）必须有签名位且已签字（M06）；
- 账本自身不登记自己的哈希（自引用），所以 `run-manifest.html` 由账本渲染、而非账本条目。

## 误用样本（misuse/）

| 文件 | 故意违规 | 期望错误码 |
|---|---|---|
| `manifest-missing-sha.json` | 抹掉某工件 sha256 | `M02_MISSING_SHA256` |
| `manifest-untraceable-and-unsigned.json` | 输入早于产出 + 不可逆未签字 | `M04_UNTRACEABLE_INPUT`、`M06_MISSING_SIGNOFF` |
