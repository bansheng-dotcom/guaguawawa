# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/ppt-generator/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 2/2`（含 1 个反例）。版本：v2.0.0

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 只有 2 页（<6） | `deck.count` 页数 6–30 | ✅ exit=1（`tests/deck-fail.json`） |
| MU-02 | deck 标题为空 | `deck.title` | ✅ exit=1（同上） |
| MU-03 | 封面不在第 1 页 | `deck.cover` | ✅ exit=1（同上） |
| MU-04 | 收尾不在最后一页 | `deck.closing` | ✅ exit=1（同上） |

## 二、门禁抓不到，靠 §6 自检

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-05 | message 写主题不写结论 | 讲的时候现编，前后矛盾 | §6 结论句检查 |
| MU-06 | 单页 8 条 bullets | 听众开始读而不是听 | §6 密度检查 |
| MU-07 | 产出多文件工程 | 投屏现场少一个 css 就白屏 | §6 单文件检查 |
| MU-08 | 依赖外部 CDN | 断网就白屏 | §6 无外链 |
| MU-09 | 只在笔记本分辨率看 | 投屏字号小到看不见 | §6 投屏检查 |
| MU-10 | 时间不够就加速讲 | 讲不清 | §6 时长估算 |
| MU-11 | 30+ 页硬塞 | 讲不完 | `deck.count` 部分覆盖 |

> **纪律**：deck 的验收不在设计稿上，在"10 分钟能不能讲完、听众记住哪三句"。
