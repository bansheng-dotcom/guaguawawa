# 高雅人士天团（Elegant Elite Squad）

把经营问题拆成「产品判断 → 数据洞察 → 图表表达 → 内容生产 → 自媒体运营」的全链路交付，输出可决策、可执行、可复盘的成果。

## 类型

Team 型（多角色协作团队）

## 团队成员

| 成员 | 名字 | 职责 |
|---|---|---|
| qiuqiu-fullstack-team-team-lead | 渭领领 | 全链路编排、跨域整合、最终决策建议 |
| product-strategist | 渭产品 | 需求澄清、问题定界、产品策略、指标与验收 |
| data-insight-analyst | 渭分析 | 假设驱动分析、取数计划、归因、证据链 |
| data-visualization-designer | 渭作图 | 图表选型、指标编码、可视化审查、阅读路径 |
| content-director | 渭编编 | 选题、大纲、多 Agent 写作、审查、终稿收口 |
| media-ops-operator | 渭媒体 | 多平台数据接入、经营看板、日报与发布复盘 |

## 使用示例

- 请把我的经营问题拆成产品判断、数据分析、内容与运营的完整方案。
- 帮我从数据里找到增长原因，并做成能直接汇报的图表和报告。
- 帮我写一篇知识科普文章，并规划多平台发布与数据复盘。

## 内置技能包（满血版）

5 个成员技能不是摘要，而是把上游开源方法包**整包内置**在 `skills/<skill>/upstream/`，并各自配一份 `SKILL.md` 作为入口与路由表。

| 技能 | 分配成员 | 上游来源 | 内置内容 |
|---|---|---|---|
| qiuqiu-product | 渭产品 | github.com/bzwh321/product-manager-agent-project-public | 15 个目录化 workflow、library 能力地图 9 篇、experience 经验 RAG、templates 注册表、user 偏好模板 |
| qiuqiu-data-analysis | 渭分析 | github.com/bzwh321/data-analysis-report-agent | 主契约 SKILL.md、6 个专职子 Agent、7 个确定性校验器、7 篇报告/图表契约、2 套页面风格 + 配色系统、案例包 |
| qiuqiu-data-viz | 渭作图 | github.com/bzwh321/ai-data-visualization-prompts | 48 条人工审核提示词全文、prompts/index.json 索引、六问审查清单 |
| qiuqiu-content | 渭编编 | github.com/bzwh321/article-director-public | 22 个 Agent 定义、lean-v1 拓扑与 3 道人工闸门、prompts 注册表、2 种策略契约、3 层确定性校验、去 AI 味规则与作者风格档案 |
| qiuqiu-media-ops | 渭媒体 | github.com/bzwh321/self-media-data-console-bzwh | 数据契约与规范化/校验/流水线脚本、本地看板前后端、归因脚本、字段映射表、皮肤与飞书推送规范、5 平台模拟数据 |

引入时间：2026-11-03。每个成员 Agent MD 的「预加载技能」章节写明启动第一步加载技能及必读文件；主理人 MD 的「成员技能分配」含调度硬要求。

未打包的部分（体积原因）：visualization 仓库的 `gallery/` 静态图廊与 echarts 依赖、media-ops 的测试目录与看板截图。

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
C:\Users\18238\.workbuddy\plugins\marketplaces\my-experts\plugins/qiuqiu-fullstack-team/
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
zip -r qiuqiu-fullstack-team.zip qiuqiu-fullstack-team/
```
