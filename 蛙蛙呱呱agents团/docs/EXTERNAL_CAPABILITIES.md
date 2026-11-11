# 外部能力目录（26 项）

> 来源：Trae 官方插件市场 24 个插件 + WorkBuddy 2 个技能。
> 登记表：`shared/external_capabilities/catalog.json`；读取器：`shared/external_capabilities.py`。
> 入口文档已按「负责角色」拷入 `rXX-*/references/external/<能力>/`（共 212 个文件，约 1.5 MB）。

## 为什么要做这件事

这 26 项里有三种东西，处理方式必须分开：

| 类型 | 例子 | 本质 | 本团队怎么用 |
|---|---|---|---|
| `skill` / `multi` | 小红书笔记、学术写作、用户研究 | **提示词规范**（SKILL.md + references） | 入口文档入库，按其中 Workflow 执行 |
| `mcp` | 美图、火山数据集、AgentEarth、Taro 小程序 | **需要 MCP 客户端 + 凭据** | 登记接入配方（`.mcp.json`），本 CLI 不直连 |
| `app`-ish | 部分插件带脚本/模板 | 依赖其源目录 | 以 catalog 的 `source` 为准，文档里注明 |

把它们混成"都能直接调用"是吹牛；这里只承诺三件可验证的事：**归属清楚、文档落地、就绪可查**。

## 一、按角色归属

| 角色 | 负责的外部能力 | 消费方 |
|---|---|---|
| **R01** CEO | `strategic-growth-compass` 战略与增长罗盘 | R07 / R12 |
| **R02** COO | `business-ops-analysis` 经营运营分析 | R06 / R12 |
| **R05** 研究 | `tashan-research-skills`（20 技能）、`industry-panorama-research`、`market-intelligence-radar`、`volcengine-pro-dataset`(MCP)、`agent-earth`(MCP) | R01/R06/R11/R12/R14/R19 |
| **R06** 数据 | `build-web-data-visualization`（18 技能）、`data-processing` | R08/R09/R10 |
| **R07** 产品 | `user-research-toolkit` 用户研究 | R05 / R11 |
| **R08** MVP | `rapid-prototype-craft`、`ppt-generator` | R10 / R09 / R02 |
| **R09** 工程 | `web-app-development`(uicraft)、`frontend-design`、`miniapp-builder`(MCP) | R08 / R10 / R17 |
| **R10** 设计 | `meitu-local-mcp`(MCP)、`trae-design`（4 技能）、`whiteboard`、`brand-guardian`、`ecommerce-designer` | R04/R07/R08/R09/R11/R12/R14 |
| **R11** 内容 | `rednote-post`、`xhs-content-skills`（9 技能） | R10 / R12 / R03 |
| **R12** 增长 | `marketing-toolkit` 营销全链路 | R10 / R11 |
| **R14** 交易 | `omnichannel-commerce-assistant`、`smart-product-selector` | R01/R02/R06/R12 |
| **R15** 供应链 | `analyze-procurement` 采购分析 | R03 / R14 |

R03/R04/R13/R16/R17/R18/R19/R20 没有领到外部能力，但作为消费方出现在上表（如 R04 做品牌审查会读 R10 的 `brand-guardian` 文档）。

## 一.5 已落地为可执行技能（不是只登记）

登记只是第一步；下面 3 个能力已经把上游的规则表变成角色里可直接跑、可回归的确定性技能：

| 能力 | 落点 | 命令 | 实现的规则 | 上游问题 |
|---|---|---|---|---|
| `xhs-content-skills` + `rednote-post` | R11 `xhs` | `xhs note` / `score` / `compliance` | 标题 ≤20 字且前 10 字含核心词；正文 550–650 字；标签 3–8 且埋词闭环；8 项质量快检 ≥7 通过；CES 基准；CTA 黑名单（6 类）+ 四类诱导互动 + 绝对化用语/收入表述/联系方式；AI 内容须带 `#AI辅助创作` | 无 |
| `smart-product-selector` | R14 `selection` | `selection score` / `profit` | 五维 1–5 打分；推荐等级四档；**SP-09 假设卡缺预期指标即 FAIL**；毛利率 <30% 警告、<15% 放弃；每品须标数据来源类型 | 文档五维权重写作 30/20/25/30/15（**合计 120%**），实现按 100% 归一化并在 checks 显式提示 |
| `analyze-procurement` | R15 `tco` | `tco compare` / `lifecycle` | landed cost 九项加总；`landed_unit = landed / 可用数量`；资金占用按账期折算；MOQ/交期/不良率旗标；TCO 至少 3 类成本非零才算 TCO（仅货值+运费不算） | 无 |

这三个技能都已接进各自角色的 `harness` 门禁与 `contract` 契约，并有单独的跨角色回归
`tests/test_capability_fusions.py`（8 例）。

其余 23 项为什么还没做成可执行技能，分两类：
- **纯提示词规范**（如 `tashan-research-skills`、`user-research-toolkit`）：没有可判定的规则表，
  强行写"校验"就是编造标准；正确用法是按其 Workflow 执行，由角色 harness 验收产物。
- **需要运行时**（4 个 MCP + lark 等）：需 MCP 客户端/凭据，CLI 不直连，只能给接入配方。

## 二、怎么查、怎么用

```bash
# 全部能力 + 就绪状态（本地只读，不联网）
python guagua.py capabilities --probe
# 只看某个角色（负责或可消费）
python guagua.py capabilities --role r11 --probe
# 搜关键词
python guagua.py capabilities --q 小红书
# 看单项详情：文档目录、源目录、就绪检查、接入配方
python guagua.py capabilities --id meitu-local-mcp
```

角色内部：打开 `rXX-*/references/external/README.md` 有索引；每项能力的入口是
`references/external/<能力>/skills/<技能>/SKILL.md`。

## 三、MCP 类怎么接（重要）

四个 MCP（美图、火山数据集、AgentEarth、Taro 小程序）都需要 MCP 客户端，**本团队 CLI 不直连**。
`python guagua.py capabilities --id <id>` 会打印脱敏后的 `.mcp.json` 片段：

| 能力 | 传输 | 关键配置 |
|---|---|---|
| `meitu-local-mcp` | 本地 stdio | `node ./dist/server.cjs` + `MEITU_OAUTH_ACCESS_TOKEN` |
| `volcengine-pro-dataset` | HTTP | `https://datapro.hqd.cn-beijing.volces.com/mcp` + `X-Hqd-Api-Key` |
| `agent-earth` | HTTP | `https://agentearth.ai/mcp-server/r/...` + `Authorization: Bearer` |
| `miniapp-builder` | 本地 stdio | `node ./app/core/index.js` |

接法：把片段里的 `${connector.*.ACCESS_TOKEN}` 换成真实凭据，粘到 Trae / Claude Desktop 的
MCP 配置里；就绪探测只判断"配置项是否齐"，不会替你验证凭据有效性。

## 四、边界与维护

- **不伪造能力**：`skill` 类是规范不是程序，R10/R11 等按文档执行并由本角色 harness 验收；
  `mcp` 类在客户端未接入前一律标 `partial`，不写"已调用"。
- **文档会过期**：入口文档是 26 个插件当前版本的快照；插件升级后重跑
  `python -c "..."` 的摄取脚本或直接替换 `references/external/<id>/`（详见下节）。
- **源目录可能变**：catalog 里 `source` 是绝对路径，换机器后会 `blocked`，这是预期行为。
- **授权**：这些插件各自带 LICENSE（部分已随文档拷入），商用前按各自许可证确认。

## 五、重新摄取

```bash
# 入口文档重新拷贝 + 目录重建（脚本在仓库外，按需重跑）
python scripts/ingest_external_capabilities.py
```

> 若源插件升级，先确认 `SKILL.md` 结构未变，再更新 `catalog.json` 里的 version 与 skills 清单。
