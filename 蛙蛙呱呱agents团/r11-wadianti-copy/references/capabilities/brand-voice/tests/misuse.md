# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/brand-voice/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 6/6`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | `forbidden_hits: "不是列表"`（字符串而非列表） | `voice.edit.hits` BLOCKER | ✅ exit=1（`examples/edit_dirty.json`） |
| MU-02 | 终稿残留「值得我们深思」 | `voice.edit.residual` BLOCKER | ✅ exit=1（同上） |
| MU-03 | 缺 H2 层级 / 空泛权威 / 无引用 | `seo.structure_h2` / `seo.eeat_hype` / `seo.citations` | ✅ exit=1（`examples/audit_dirty.json`） |
| MU-04 | 术语表缺失 + 语言不一致 | `localize.term.glossary` / `localize.lang` | ✅ exit=1（`examples/term_dirty.json`） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-05 | 清空禁词表让 `residual` 通过 | 作弊；`residual` 查的是终稿残留，清表会暴露 | `residual` 部分覆盖 + §6 |
| MU-06 | `to` 写空以为"待定" | 空字符串语义是**删除** | §6 自检 |
| MU-07 | 替换一半（"抓手"换了"闭环"没换） | 残留检测会抓 | `term_fixes` 覆盖 + §6 |
| MU-08 | 形容词堆叠（"高效便捷智能"） | 空话 | §6 口吻回归三问 |
| MU-09 | 模板开场（"在当今快速发展的时代"） | 模板腔 | §6 |
| MU-10 | 同一概念标题叫 A 正文叫 B | 术语不统一 | `term` 部分覆盖 + §6 |
| MU-11 | 承诺"发了一定有流量" | 越界承诺 | §1 转交表 |
| MU-12 | 中英混排 / 全半角 / 大小写不统一 | 本地化不一致 | `term` 覆盖 + §6 |
| MU-13 | 只做一遍就交付 | 机械项与口吻项混在一遍 | §6 两遍法 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 每次改 `harness.py edit/audit/term` 或 `thresholds.json` 后重跑 `--self-test`
- [ ] 交付前跑了两遍：脚本一遍 + 人读一遍
- [ ] 人工项（形容词堆叠/模板腔/术语选择）都有显式记录

> **纪律**：禁词清零只是"没有硬伤"，离"写得好"还差一次人的通读。
