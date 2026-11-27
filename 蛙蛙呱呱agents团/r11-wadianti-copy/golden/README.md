# R11 黄金成品（3 份）

三份 HTML 都由七段链真实跑 fixtures 后直接落盘，不是手写样例。
重生成命令（在 `r11-wadianti-copy/` 下）：

```bash
python -c "from content_chain import runner; runner.run('fixtures/knowledge.json', 'out/knowledge')"
python -c "from content_chain import runner; runner.run('fixtures/tutorial.json', 'out/tutorial')"
python -c "from content_chain import runner; runner.run('fixtures/opinion.json', 'out/opinion')"
```

每次运行会在输出目录生成 `topic_candidates.json`、`research_pack.json`、`outline.json`、
`drafts.json`、`review.json`、`rewrite.json`、`final_audit.json`、`final.md`、`final.html`
与 `chain_manifest.json`。

## 1. knowledge-compounding.html · 知识科普长文

- 输入：`fixtures/knowledge.json`
- 主题：内容复利：把一次生产变成可重复调用的资产
- 平台约束：公众号，1200–4000 字
- 验收：
  - 选题 10 个，三维分数齐，Top3 有理由；
  - 来源 8 条（一手 3 / 二手 3 / 三手 2），每条 URL、日期、原文齐；
  - 5 节，每节 6 字段齐，草稿三候选多样性 ≥0.6、分数 ≥85；
  - 改写覆盖率 100%，数字与专名未变；
  - 终检 PASS：1349 字，套话密度 0.00，数字全部可追 claims。

## 2. tutorial-content-chain.html · 工具教程

- 输入：`fixtures/tutorial.json`
- 主题：把写作拆成七道工序：R11 内容链实操
- 平台约束：公众号，1200–4000 字
- 验收：
  - 5 节分别覆盖选题、证据、草稿、改写、终检；
  - 专名 `R11` 中的数字不参与 claims 核对，但正文事实数字全部可追；
  - 终检 PASS：1351 字，套话密度 0.00；
  - 门禁链全部 PASS，`chain_manifest.json` 跨段一致。

## 3. opinion-solo-content-hub.html · 观点文

- 输入：`fixtures/opinion.json`
- 主题：一人公司要不要做内容中台：先算清这三笔账
- 平台约束：公众号，1200–4000 字
- 验收：
  - 观点文按“判断—成本—反方—边界—动作”组织；
  - 每节含数字与边界句，论证流门禁 PASS；
  - 终检 PASS：1336 字，套话密度 0.00；
  - 改写候选数字/专名与选中稿一致。

## 统一验收口径

| 项 | 口径 |
|---|---|
| 结构 | H1 + 5 个 H2 + “边界与后续” |
| 论证流 | 每节含数字、含“边界”句、≥2 句 |
| AI 味 | 每千字套话命中 ≤0.5 |
| 事实 | 正文数字 ⊆ claims 数字 ∪ 专名数字 |
| 长度 | 落在 brief.constraints 的 min/max 内 |
| 留痕 | 7 个 JSON + `chain_manifest.json` 均有 sha256 |
