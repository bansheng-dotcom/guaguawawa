# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/miniapp-builder/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 2/2`（含 1 个反例）。版本：v2.0.0

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 工程名用中文（"报价小工具"） | `miniapp.name` 合法标识符 | ✅ exit=1（`tests/miniapp-fail.json`） |
| MU-02 | 页数 <2 | `miniapp.pages` 页数 2–20 | ✅ exit=1（同上） |
| MU-03 | 页面无标题 | `miniapp.page.title` | ✅ exit=1（同上） |
| MU-04 | tabbar 指向未定义页面 | tabbar 差集校验 | ✅ exit=1（同上） |

## 二、门禁抓不到，靠 §6 自检

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-05 | 路径写 `pages/list`（非两段式） | 找不到文件 | `miniapp.page.path` 部分覆盖 |
| MU-06 | 手写 `app.json` | 漏 tabbar list / 页面注册 | §6 用 scaffold |
| MU-07 | 页面 25 个 | 该拆分包 | §6 页数检查 |
| MU-08 | 只跑 plan 不导入验证 | 不知道真能不能开 | §6 导入实测 |
| MU-09 | 页面路径用中文 | 打包失败 | §7 EX-10 |
| MU-10 | tabbar 6 个 | 小程序 tab 一般 ≤5 | §8 降级 |
| MU-11 | 需要后端接口却只出骨架 | 交付不完整 | §8 明确不做 |

> **纪律**：tabbar 悬空是小程序"点了白屏"的头号原因，门禁会直接拦。
