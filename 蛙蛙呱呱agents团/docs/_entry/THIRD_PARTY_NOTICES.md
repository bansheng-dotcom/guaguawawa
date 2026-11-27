# 第三方资产说明

本仓库绝大部分代码与文档是自有实现。以下资产来自公开项目，按原许可使用；
相关品牌名与平台名不构成本项目的归属标识。

| 资产 | 位置 | 来源与许可 |
|---|---|---|
| 品牌设计基线（31 套，已抽取为自有 JSON 预设） | `r10-wachengmei-design/references/brand-presets/presets.json` | 色板/字体等事实数据，来自公开设计系统；仅作设计基线，不替代客户品牌授权 |
| MiniMax H3 提示词规范（已内化为结构规则） | `r10-wachengmei-design/skills/s13_h3prompt.py` | 据公开规范实现的字段顺序/时长/时间戳等校验，无原文拷贝 |
| AI Hive OpenAPI 客户端脚本 | `r10-wachengmei-design/vendor/aihive/imagegen.py` | 上游公开客户端脚本；调用需自行配置 API Key，费用以服务方实时报价为准 |
| 报告/主题等共享模块 | `shared/` | 本团队自有实现 |
| 第三方品牌设计分析（31 份 markdown 摘录） | `r10-wachengmei-design/references/design-library/` | 公开设计系统的**事实性摘录**（配色/字体/版式观察），用于内部设计基线；不包含原文全文，不主张对上述品牌的任何权利。再分发前请自行核对上游条款 |
| AI Hive 生图客户端（本地脚本） | `r10-wachengmei-design/vendor/aihive/imagegen.py` | 上游公开客户端脚本的本地适配；无随附 LICENSE 文件，调用需自备 API Key。对外分发前必须补齐上游 URL 与许可证，或移除 `vendor/` |

若需对外分发，请保留本文件并核对各上游项目的最新许可条款。

## 机器可读清单与门禁

- 逐项状态：`r10-wachengmei-design/references/design-library/LICENSE_STATUS.json`
  （每项的 upstream_url / license / redistributable）。
- 门禁：`python scripts/check_third_party_licenses.py`（报告）；
  打包/对外分发前跑 `--strict`，存在 `license=unknown` 即退出 1。
- 当前状态：31 份设计分析 + 1 份 AI Hive 客户端均为 `unknown` → **不得进入对外分发包**。
