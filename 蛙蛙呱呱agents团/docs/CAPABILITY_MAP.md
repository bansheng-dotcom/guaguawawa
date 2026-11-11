# 能力映射目录

> 由 `shared/capabilities/catalog.json` 生成（29 项，目录版本 v3）。
> 形态：**代码** = 有确定性命令与门禁；**规范** = 按能力卡规则执行，产物走角色 harness 验收。

## 一、总览

- 能力总数：**29**（代码 10 / 规范 19）
- 代码技能：brandcheck、deck、htmlreport、imgops、miniapp、office、prdguard、selection、tco、xhs

## 二、映射

| 角色 | 能力 | 形态 | 用法 | 能力卡 |
|---|---|---|---|---|
| r01 | `strategic-growth-compass` | 规范 | 按卡执行 | `r01-waquanju-ceo/references/capabilities/strategic-growth-compass/README.md` |
| r02 | `business-ops-analysis` | 规范 | 按卡执行 | `r02-wapaibu-coo/references/capabilities/business-ops-analysis/README.md` |
| r02 | `lark` | 规范 | 按卡执行 | `r02-wapaibu-coo/references/capabilities/lark/README.md` |
| r05 | `deep-research-assistant` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/deep-research-assistant/README.md` |
| r05 | `industry-panorama-research` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/industry-panorama-research/README.md` |
| r05 | `market-intelligence-radar` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/market-intelligence-radar/README.md` |
| r05 | `tashan-research-skills` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/tashan-research-skills/README.md` |
| r06 | `build-web-data-visualization` | 规范 | 按卡执行 | `r06-wadeqing-analyst/references/capabilities/build-web-data-visualization/README.md` |
| r06 | `data-processing` | 规范 | 按卡执行 | `r06-wadeqing-analyst/references/capabilities/data-processing/README.md` |
| r07 | `prd-authoring` | 代码 | `prdguard check/render` | `r07-wademing-pm/references/capabilities/prd-authoring/README.md` |
| r07 | `user-research-toolkit` | 规范 | 按卡执行 | `r07-wademing-pm/references/capabilities/user-research-toolkit/README.md` |
| r08 | `html-report-presentation` | 代码 | `htmlreport plan/html` | `r08-wajiancheng-mvp/references/capabilities/html-report-presentation/README.md` |
| r08 | `miniapp-builder` | 代码 | `miniapp plan/scaffold` | `r08-wajiancheng-mvp/references/capabilities/miniapp-builder/README.md` |
| r08 | `office-plugin` | 代码 | `office probe/xlsx/docx` | `r08-wajiancheng-mvp/references/capabilities/office-plugin/README.md` |
| r08 | `ppt-generator` | 代码 | `deck plan/html` | `r08-wajiancheng-mvp/references/capabilities/ppt-generator/README.md` |
| r08 | `rapid-prototype-craft` | 规范 | 按卡执行 | `r08-wajiancheng-mvp/references/capabilities/rapid-prototype-craft/README.md` |
| r09 | `frontend-design` | 规范 | 按卡执行 | `r09-wawenma-engineer/references/capabilities/frontend-design/README.md` |
| r09 | `web-app-development` | 规范 | 按卡执行 | `r09-wawenma-engineer/references/capabilities/web-app-development/README.md` |
| r10 | `brand-guardian` | 代码 | `brandcheck check` | `r10-wachengmei-design/references/capabilities/brand-guardian/README.md` |
| r10 | `design-system` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/design-system/README.md` |
| r10 | `ecommerce-designer` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/ecommerce-designer/README.md` |
| r10 | `image-ops` | 代码 | `imgops info/resize/crop/compress/pad/watermark` | `r10-wachengmei-design/references/capabilities/image-ops/README.md` |
| r10 | `whiteboard` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/whiteboard/README.md` |
| r11 | `rednote-post` | 规范 | 按卡执行 | `r11-wadianti-copy/references/capabilities/rednote-post/README.md` |
| r11 | `xhs-content-skills` | 代码 | `xhs note/score/compliance` | `r11-wadianti-copy/references/capabilities/xhs-content-skills/README.md` |
| r12 | `marketing-toolkit` | 规范 | 按卡执行 | `r12-wayingliu-growth/references/capabilities/marketing-toolkit/README.md` |
| r14 | `omnichannel-commerce-assistant` | 规范 | 按卡执行 | `r14-wajiaoyi-commerce/references/capabilities/omnichannel-commerce-assistant/README.md` |
| r14 | `smart-product-selector` | 代码 | `selection score/profit` | `r14-wajiaoyi-commerce/references/capabilities/smart-product-selector/README.md` |
| r15 | `analyze-procurement` | 代码 | `tco compare/lifecycle` | `r15-wagongying-erp/references/capabilities/analyze-procurement/README.md` |

## 三、本轮收口（v2.2.0）

- 品牌基线改为自有 JSON 预设（`brand-presets/presets.json`），删除第三方原文；DESIGN.md 按需生成。
- 删除 H3 规范原文：规则内化在 `s13_h3prompt.py`。
- 新增 `office`（xlsx/docx）与 `lark`/`deep-research-assistant` 能力卡。
- 能力卡统一为执行步骤 + 验收 + 常见错误 + 变更记录；目录加 version。
- `.gitignore` 收口 workspaces 与 zip；删除仓库根平台残留目录。
- 端到端用例：`run --task` 意图路由 → `deck` 通过验收。

## 四、仍未完成（诚实清单）

| 项 | 现状 |
|---|---|
| `volcengine-pro-dataset` / `agent-earth` | 外部数据检索服务，离线无法自建替代；不纳入目录 |
| `lark` 真实接入 | 仅能力卡（不接 SaaS 账号），无 OAuth 客户端 |
| `aihive generate` 真实链路 | 无 API Key，只有 blocked/preview 分支验证 |
| 19 张规范卡 | 已有执行步骤/验收/常见错误，但上游多文件模板未逐条吸收 |
| 归档 | zip 已从 git 跟踪中移出，改为本地产物 |
