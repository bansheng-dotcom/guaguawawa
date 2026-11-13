# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/office-plugin/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 2/2`（含 1 个反例）。自检会写 `tests/_out.xlsx` 并在结束后删除。
> 版本：v2.0.0

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 工作表无表头（`headers: []`） | `office.headers` 表头 ≥1 列 | ✅ exit=1（`tests/xlsx-fail.json`） |
| MU-02 | 无数据行 / 行宽与表头不一致 | `office.rows` | ✅ exit=1（同上） |
| MU-03 | 输出扩展名不是 `.xlsx` | `office.ext` | ✅ exit=1（实测 `--out out` 时） |
| MU-04 | 覆盖已有同名文件且无 `--force` | `office.overwrite` | ✅ exit=1（实测） |

## 二、门禁抓不到，靠 §6 自检

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-05 | 表头写 `col1/col2` 或字段名 | 业务人读不懂列 | §6 表头检查 |
| MU-06 | 某些行少一格 | 整列配错，表面"生成成功" | `office.rows` 部分覆盖 |
| MU-07 | 数字列不标单位/含税 | 数字含义不明 | §6 口径检查 |
| MU-08 | 文件名"最终版2" | 无法排序 | §6 命名检查 |
| MU-09 | 缺库却生成空文件 | 空文件比报错更糟 | §6 probe 先行 |
| MU-10 | 一个表塞 30 列 | 不可读 | §6 拆表 |
| MU-11 | 只有表没有口径说明 | 别人不知道数字怎么来的 | §6 |

> **纪律**：Office 交付物要经得起"转发给客户"。表头与口径就是它的体面。
