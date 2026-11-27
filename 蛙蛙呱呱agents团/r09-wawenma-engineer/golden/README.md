# R09 黄金样例（golden）

三份 HTML 不是手写 mock，而是 `eng_chain.runner` 真实跑 fixtures 后，
按段级工件渲染出来的交付页。每份页脚的阶段指纹来自对应 `*.json` 的 sha256 前缀。

| 文件 | 夹具 | 演示重点 |
|---|---|---|
| `tiny-notes-delivery.html` | `eng_chain/fixtures/tiny-notes.json` | 十段全链 PASS：ADR 取舍、OpenAPI/RFC 7807、验收→E2E、发布流水线与回滚 |
| `incident-review.html` | `eng_chain/fixtures/incident-outage.json` | 故障复盘：时间线、根因、行动项、SLO/错误预算、MTTD/MTTR |
| `security-audit.html` | `eng_chain/fixtures/security-audit.json` | 安全审计：STRIDE 六类、ASVS 8 项、依赖/密钥扫描、错误码对齐 |

复现命令（在 `r09-wawenma-engineer/` 下）：

```bash
python -m eng_chain.runner --brief eng_chain/fixtures/tiny-notes.json --out-dir out/tiny-notes
python -m eng_chain.runner --brief eng_chain/fixtures/incident-outage.json --out-dir out/incident
python -m eng_chain.runner --brief eng_chain/fixtures/security-audit.json --out-dir out/security
```

每份运行目录含 10 个 `*.json`、10 个 `*.md` 与 `eng_manifest.json`。
三份 HTML 只需保证可独立打开、数据与夹具一致；不在页面里写入时间戳，
便于 diff 复核。
