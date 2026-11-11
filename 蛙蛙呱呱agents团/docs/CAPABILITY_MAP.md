# 能力映射目录

> 由 `shared/capabilities/catalog.json` 生成（75 个技能包 + 4 merged + 1 deprecated，目录版本 v45）。
> 形态：**代码** = 有确定性命令与门禁；**规范** = 按能力卡规则执行，产物走角色 harness 验收。

## 一、总览

- 技能包总数：**75**（knowledge 41 / skill 34），旧能力卡已全部处置完毕
- **75 个技能包全部 A 级 100 分**，覆盖 20 个角色（每角色至少 1 个）：
  `decision-gate`(r01) `handoff-acceptance`(r02) `model-audit`(r03) `review-anti-collusion`(r04)
  `evidence-ledger`(r05) `data-validation`(r06) `prd-authoring`(r07) `rapid-prototype`(r08)
  `tdd-review-pair`(r09) `ecommerce-designer`(r10) `brand-voice`(r11) `campaign-plan`(r12)
  `qbr-health`(r13) `order-lifecycle`(r14) `po-validate`(r15) `hiring-scorecard`(r16)
  `webhook-retry`(r17) `dbt-unit-test`(r18) `eval-report`(r19) `incident-response`(r20)
- **20 份角色技能卡全部 A 级 100 分**（原工程细节迁至各角色 `references/engineering-notes.md`）

## 二、映射

| 角色 | 能力 | 形态 | 用法 | 能力卡 |
|---|---|---|---|---|
| r01 | `decision-gate` | 代码 | `decide reversibility/card/escalate` | `r01-waquanju-ceo/references/capabilities/decision-gate/SKILL.md`（已升级技能包，v2.0.0） |
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
| r10 | `ecommerce-designer` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/ecommerce-designer/SKILL.md`（已升级技能包，v2.0.0） |
| r10 | `image-ops` | 代码 | `imgops info/resize/crop/compress/pad/watermark` | `r10-wachengmei-design/references/capabilities/image-ops/README.md` |
| r10 | `whiteboard` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/whiteboard/README.md` |
| r11 | `rednote-post` | 规范 | 按卡执行 | `r11-wadianti-copy/references/capabilities/rednote-post/README.md` |
| r11 | `xhs-content-skills` | 代码 | `xhs note/score/compliance` | `r11-wadianti-copy/references/capabilities/xhs-content-skills/README.md` |
| r12 | `marketing-toolkit` | 规范 | 按卡执行 | `r12-wayingliu-growth/references/capabilities/marketing-toolkit/README.md` |
| r14 | `omnichannel-commerce-assistant` | 规范 | 按卡执行 | `r14-wajiaoyi-commerce/references/capabilities/omnichannel-commerce-assistant/README.md` |
| r14 | `smart-product-selector` | 代码 | `selection score/profit` | `r14-wajiaoyi-commerce/references/capabilities/smart-product-selector/README.md` |
| r15 | `analyze-procurement` | 代码 | `tco compare/lifecycle` | `r15-wagongying-erp/references/capabilities/analyze-procurement/README.md` |

## 二·六、旧能力卡处置（v2.8.0 · 27 张定级）

> 口径：不是"全部升级"，而是先判**新包是否已覆盖其方法**。三分法，可回滚（只改 `status` 字段，不删文件）。

| 状态 | 数量 | 含义 | 后续 |
|---|---|---|---|
| `pack` | 20 | 已升级技能包 | 已达标，按 CI 维护 |
| `active` | 22 | 无新包覆盖，**方法独立** | 保留待升级，按 P4 逐张处理 |
| `merged` | 4 | 方法已被新包覆盖 | 不再单独升级，指向 `superseded_by` |
| `deprecated` | 1 | 明确不接入 | 保留作边界说明，默认清单标「停用」 |

**并入明细（4 张）**

| 旧卡 | 归属 | 并入 | 理由 |
|---|---|---|---|
| `rapid-prototype-craft` | r08 | `rapid-prototype` | 同名同义，纯重复 |
| `marketing-toolkit` | r12 | `campaign-plan` | 营销全链路 ⊂ campaign 设计（渠道/预算/实验/停止） |
| `data-processing` | r06 | `data-validation` | 数据处理 ⊂ 数据校验（六维质量 + 口径） |
| `omnichannel-commerce-assistant` | r14 | `order-lifecycle` | 全渠道诊断 ⊂ 订单三态与履约 |

**停用（1 张）**：`lark` —— 不接 SaaS、无 OAuth 客户端，保留作能力边界说明。

**保留待升级（22 张）及理由**

| 角色 | 保留的旧卡 | 为什么不能并入现有新包 |
|---|---|---|
| r01 | `strategic-growth-compass` | 战略取舍 ≠ 决策闸门（一个管方向，一个管可逆性） |
| r02 | `business-ops-analysis` | 经营分析 ≠ 交接验收 |
| r05 | `tashan-research-skills` / `industry-panorama-research` / `market-intelligence-radar` / `deep-research-assistant` | 都是**具体研究方法**；`evidence-ledger` 只给流程与来源分级，不替代方法 |
| r06 | `build-web-data-visualization` | 可视化呈现 ≠ 数据校验 |
| r07 | `user-research-toolkit` | 用户研究 ≠ PRD 撰写 |
| r08 | `ppt-generator` / `html-report-presentation` / `office-plugin` / `miniapp-builder` | 都是可执行产物生成器，新包不覆盖 |
| r09 | `web-app-development` / `frontend-design` | 构建与前端实现 ≠ TDD 与评审流程 |
| r10 | `brand-guardian` / `design-system` / `whiteboard` / `image-ops` | 品牌/设计系统/白板/图像处理，均与电商视觉设计正交 |
| r11 | `rednote-post` / `xhs-content-skills` | 小红书结构与发布 ≠ 品牌语调 |
| r14 | `smart-product-selector` | 选品评分 ≠ 订单生命周期 |
| r15 | `analyze-procurement` | 采购 TCO ≠ 单据校验 |

**查看方式**

```bash
python guagua.py capabilities --status merged      # 看已并入的 4 张
python guagua.py capabilities --status deprecated  # 看停用的 1 张
python guagua.py capabilities --status active      # 看待升级的 0 张（已全部升级）
python guagua.py capabilities --observed           # 看「日志里真实发生、但尚无能力卡」的 34 组调用
```

## 二·六之二、已观测但无能力卡的调用（observed_actions）

> 见 `docs/CAPABILITY-USAGE-AUDIT.md`。这是"下一批升级的真实候选"，不是凭空拟的名单。

| 项 | 数量 | 口径 |
|---|---|---|
| `observed_actions` | **34** | 运行日志里调用量 ≥10、但目录尚无对应能力卡的 `(角色, skill, action)` |
| `entry_mismatch` | **3** | 已登记能力的 entry 声明与实际调用名不一致 |

Top 5（按真实调用量）：`r18 quality.check` 185 次、`r17 integration.workflow` 86 次、
`r07 prd.prd` 68 次（48 通过/20 失败）、`r17 approval.publish` 66 次、`r18 incremental.backfill` 65 次。

**维护命令**

```bash
python scripts/sync_catalog_observed.py     # 从日志重算并刷新 observed_actions
python scripts/capability_usage.py --check  # CI 漂移门禁：有未备案高频调用则 exit 1
```

> 为什么单列一段而不塞进 `capabilities`：它们还没有能力卡，混进去会让"能力数"虚增、
> 均值失真，也会让 `--probe` 报一堆"缺能力卡"。单列既修好测量仪器，又不污染口径。

## 二·五、技能层升级（v2.7.0 · 全 20 包 + 20 角色卡收官）

> 见 `docs/SKILL-MD-UPGRADE-PLAN.md` 与 `docs/SKILL-LAYER-SPEC.md`。

- **判定口径**：能力卡优先读 `SKILL.md`（技能包），无则回落 `README.md`（`shared/capabilities.py::card_path()`）。
- **选型索引**：`python guagua.py skills [--role|--id|--json|--broken]`，只读 frontmatter，正文不加载。
- **16 个技能包全部 A 级（100 分）**，合计 **104 项自检断言**、**48 个反例**实测被拦：

| 批次 | 包（归属） | 自检 |
|---|---|---|
| P0 | `decision-gate`(r01) `model-audit`(r03) `review-anti-collusion`(r04) `prd-authoring`(r07) `ecommerce-designer`(r10) `order-lifecycle`(r14) | 4/6/6/5/3/11 |
| P1 | `handoff-acceptance`(r02) `data-validation`(r06) `brand-voice`(r11) `campaign-plan`(r12) `qbr-health`(r13) | 7/5/6/7/7 |
| **P2** | `evidence-ledger`(r05) `hiring-scorecard`(r16) `dbt-unit-test`(r18) `eval-report`(r19) `incident-response`(r20) | 6/6/6/6/**8** |

- **新增共享工具**：`scripts/gate_wrap.py`（通用门禁包装器），判定规则 9 条 + 解析 3 条自检全部通过。
- **体检基线**：20 份角色卡均分 **12**；43 张能力卡均分 **46**（16 张 A 级，27 张 E 级待升级）。
- **CI 门禁**：`python scripts/check_skill_gate.py`（门槛 75 + 黄金快照回归 + 悬空指针）；快照 92 个对象。

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
| 28 张能力卡未升级为技能包 | 缺 frontmatter / 触发语 / 九节正文；按 `SKILL-MD-UPGRADE-PLAN.md` 分四批（P0 6 包✅、P1 5 包、P2 5 包、P3 4 包）推进 |
| 20 份角色 `SKILL.md` | 均分 12/100，13 份无 frontmatter；建议先做"选项 B"统一升级为角色技能卡（约 10h） |
| **两个角色门禁的退出码缺陷（均已修复）** | **r03**：`harness.py` 曾恒 exit 0 → 已由 `model-audit/scripts/audit_gate.py` 包装；**r06**：`agent.py quality audit` 恒 exit 0 → 已由共享 `scripts/gate_wrap.py` 包装。**r02 `harness.py` 缺 `__main__`（假绿）已于 2026-11-11 补齐 CLI + 退出码** |
| 归档 | zip 已从 git 跟踪中移出，改为本地产物 |
