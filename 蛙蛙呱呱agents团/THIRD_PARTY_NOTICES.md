# 第三方资产说明

本仓库绝大部分代码与文档是自有实现。以下资产来自公开项目，按原许可使用；
相关品牌名与平台名不构成本项目的归属标识。

| 资产 | 位置 | 来源与许可 |
|---|---|---|
| 品牌设计基线（31 套，已抽取为自有 JSON 预设） | `r10-wachengmei-design/references/brand-presets/presets.json` | 色板/字体等事实数据，来自公开设计系统；仅作设计基线，不替代客户品牌授权 |
| MiniMax H3 提示词规范（已内化为结构规则） | `r10-wachengmei-design/skills/s13_h3prompt.py` | 据公开规范实现的字段顺序/时长/时间戳等校验，无原文拷贝 |
| AI Hive OpenAPI 客户端脚本 | `r10-wachengmei-design/vendor/aihive/imagegen.py` | 上游公开客户端脚本；调用需自行配置 API Key，费用以服务方实时报价为准 |
| 报告/主题等共享模块 | `shared/` | 本团队自有实现 |

若需对外分发，请保留本文件并核对各上游项目的最新许可条款。
