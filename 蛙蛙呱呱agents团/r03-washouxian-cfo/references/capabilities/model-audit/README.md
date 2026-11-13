# 财务模型审计（capability: model-audit）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/model-audit-checklist.md`（范围卡 / 三表勾稽 / 问题日志六列 / 只读红线）
- 正例骨架：`tests/healthcheck-pass.json` / `recon-pass.json` / `evidence-pass.json`
- 门禁包装器：`scripts/audit_gate.py`（**补齐原生 harness 恒 exit 0 的缺口**，`--self-test` 6 项）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `harness.py`（`cfo healthcheck` / `financial recon` / `audit evidence` 等），本包不重复实现
