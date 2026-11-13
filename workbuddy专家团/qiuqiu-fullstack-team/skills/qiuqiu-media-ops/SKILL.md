---
name: qiuqiu-media-ops
description: "自媒体经营工作台（内置 self-media-data-console 完整方法包）：小红书/抖音/B站/知乎/公众号多平台数据接入、规范化、准确性校验、经营看板、日报推送与归因分析。当用户要接入平台数据、生成经营看板和日报、核对数据准确性、做发布复盘或看板改版时使用。Self-media ops: multi-platform data onboarding, normalization, accuracy validation, dashboards, daily reports and attribution across Xiaohongshu, Douyin, Bilibili, Zhihu and WeChat Official Account."
---

# 自媒体经营工作台（高雅人士天团 · 运营中控）

本技能内置 **self-media-data-console 完整工程包**（`upstream/`）：数据契约与规范化脚本、本地看板前后端、每日流水线、准确性校验、归因脚本、皮肤系统、飞书推送方案与字段映射表，全部原样保留。

**核心认知：日报结论由确定性规则生成，不由 AI 自由改写。** AI 负责接入引导、异常解释与建议；数值、状态、结论模板必须可复现。

---

## 一、什么时候启用

- 「接入我的小红书/抖音/B站/知乎/公众号数据」
- 「生成经营看板和日报」「今天的数据怎么样」
- 「数据为什么对不上 / 采集准不准」——口径与新鲜度核对
- 「做一次发布复盘」「找出增长驱动」——归因与经营分析
- 看板改版、皮肤、字段映射、飞书推送

**不启用**：纯方法论分析报告（qiuqiu-data-analysis）、图表选型美化（qiuqiu-data-viz）、写稿（qiuqiu-content）。

---

## 二、启动必读

| 顺序 | 文件 | 用途 |
|---|---|---|
| 1 | `upstream/agents/self-media-console-director.md` | 首次接入引导、默认判断、运行阶段与失败处理、文本结论规则（**全文**） |
| 2 | `upstream/docs/架构与数据链路.md` | 采集 → 规范化 → 校验 → 看板 → 日报 的全链路 |
| 3 | `upstream/.trae/skills/self-media-console-workflow/SKILL.md` | 变更纪律：改哪一层、哪些字段必须稳定 |

相关：`upstream/docs/自媒体看板字段映射对照表.md`（字段口径唯一事实源）、`upstream/docs/每日采集准确性.md`（准确性判定）、`upstream/docs/数据目录结构说明.md`（目录契约）。

---

## 三、数据链路与阶段

| 阶段 | 脚本 | 失败处理 |
|---|---|---|
| `sync_server` 拉取采集结果 | `upstream/scripts/sync_server_data.py` | 记失败原因，日报置 `failed`，不出正常日报 |
| `normalize` 生成统一契约 | `upstream/scripts/normalize-self-media-dashboard.py` | 记 stderr 与缺失文件 |
| `validate_accuracy` 校验平台/日期/新鲜度/核心指标 | `upstream/scripts/check-self-media-dashboard-contract.py` | 标出缺失平台与异常指标，日报置 `partial` |
| `build_workbench` 生成本地看板 | `upstream/scripts/build_compact_dashboard.py` + `upstream/console/` | 不影响数据，影响截图 |
| `capture_screenshot` 截首页 | `upstream/scripts/capture_console_screenshot.js` | 截图失败仍可发文字 |
| `send_lark` 推送结论与截图 | 见 `upstream/docs/飞书推送方案.md` | 记录发送结果 |

一键流水线：`upstream/scripts/daily_pipeline.py`（`--stage report` / `--stage screenshot` 等）。本地看板：`upstream/scripts/launch_console.py` 或 `console_server.py`（API：`/api/dashboard`、`/api/meta`、`/api/hotlist`、`/api/refresh`、`/api/report`）。

**日报状态判定**：同步失败 → `failed`；有平台数据过期 → `partial`；业务校验失败 → `failed`；全部通过 → `ready`。

---

## 四、字段契约与稳定性（改任何东西前先看这条）

平台字段必须稳定，不得随意改名：`platform`、`platform_name`、`month_net_followers`、`month_net_revenue`、`month_content_count`、`month_views`。新增字段要**先加到样例数据再接线 UI**。

口径纪律：
- 总粉丝取**结束日前最新快照**，不按日期范围求和。
- 收入只统计有可靠来源的平台（小红书、B 站优先）。
- 内容类数据保留快照历史，不覆盖原始采集文件。
- 缺失值不补零，标缺失并说明缺哪一项导出。
- 个人模式未通过契约校验时，不得与模拟数据拼接。

---

## 五、首次接入（AI-first，用户只说人话）

1. 明确告知当前是 `demo` 模拟数据还是个人数据。
2. 用中文询问：用哪些平台、看板展示名称、平台公开别名、可选目标（时区 / 月度净增粉丝目标 / 月度收入目标 / AI 接口 / 飞书接收人）。
3. 由 Agent 直接生成本机 `config.json`、建 `data/user/`、整理用户提供的导出文件并跑脚本——**不让用户填 JSON、不用命令行术语**。
4. 给官方后台让用户自行导出（登录/扫码/验证码/导出确认由用户完成）：小红书 `creator.xiaohongshu.com`、抖音 `creator.douyin.com`、B 站 `member.bilibili.com`、知乎 `zhihu.com/creator`、公众号 `mp.weixin.qq.com`。
5. 缺失数据按「平台 + 官方后台 + 缺哪个导出项」说明。
6. **禁止索取**密码、Cookie、验证码、浏览器 Profile、token、SSH 密钥、平台登录态；未获明确路径不扫描个人目录。

---

## 六、核心资源索引

| 需要什么 | 路径 |
|---|---|
| 看板前端（结构/渲染/图表/样式） | `upstream/console/index.html`、`app.js`、`charts.js`、`styles.css` |
| 本地服务与 API | `upstream/scripts/console_server.py` |
| 归因分析 | `upstream/scripts/build_attribution.py`、`upstream/.trae/skills/self-media-attribution/SKILL.md` |
| 去 AI 味（复盘文案） | `upstream/.trae/skills/de-ai-polish/SKILL.md` |
| 模拟数据与目录样例 | `upstream/scripts/generate_demo_data.py`、`upstream/data/demo/`、`upstream/data/user/` |
| 皮肤规范 | `upstream/docs/皮肤系统开发规范.md` |
| 经营分析模块规格 | `upstream/docs/经营分析模块_产品规格.md` |
| 采集指南 | `upstream/docs/数据采集指南.md` |
| 公开安全自检 | `upstream/scripts/check_public_safety.py` |
| 环境依赖 | `upstream/requirements.txt`、`upstream/config.example.json` |

---

## 七、硬性规则

- 默认使用模拟/匿名数据演示；真实数据只进用户本地目录，不进仓库。
- 绝不写入或提交 token、cookie、`open_id`、`chat_id`、本地绝对路径。
- 日报数值与状态用确定性规则；AI 只写解释与建议，且标注哪句是解释、哪句是事实。
- 不把模拟数据与个人数据混拼；不静默补零、不静默丢平台。
- 改看板走最小层：结构改 `index.html`，映射改 `app.js`，图形改 `charts.js`，布局配色改 `styles.css`。
- 每个指标都要能回溯到 `data/demo` 或用户授权数据根，否则不写进结论。

## 八、输出规范

日报固定包含：**今日状态（ready/partial/failed）→ 数据日期范围 → 各平台采集新鲜度 → 核心指标（总粉丝、新增粉丝、收入、发布数、播放/阅读、互动）→ 异常说明 → 后续处理（需人工重登 / 检查服务器任务 / 调整字段映射）**。

复盘输出：结论先行 → 增长/下滑驱动（按平台、内容、时间三维）→ 可执行动作（做什么、谁做、看什么指标验证）。
