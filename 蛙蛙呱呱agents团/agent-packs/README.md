# 蛙蛙呱呱agents团 · 专家团包（agent-packs）

> 由 `scripts/gen_agent_packs.py` 从 `core/registry.py`、`configs/*.yaml`、
> `*/prompt_profile.json`、`ORG.md` 单向渲染生成。**不要手改。**

## 内容

- `plugin.json` — 专家团清单，`20` 个成员，主理人 `蛙全局`（`r01-waquanju-ceo`）
- `manifest.yaml` — 极简声明（`type: expert`）
- `agents/*.md` — 20 份角色定义（frontmatter + 正文）
- `avatars/*.png` — 头像副本（宿主要求路径在包内）
- 角色团根目录的 `AGENTS.md` — 跨宿主通用入口（不在本目录内，因它引用根目录的 `ORG.md`/`docs/`）

## 三种宿主的加载方式

| 宿主 | 怎么用 |
|---|---|
| **WorkBuddy / CodeBuddy** | 整个 `agent-packs/` 作为 plugin 目录导入；入口 `plugin.json`，团员在 `agents/` |
| **Claude Code** | 把 `agents/*.md` 复制或软链到 `.claude/agents/`，文件名即子代理名 |
| **通用（AGENTS.md 标准）** | 宿主按 nearest-file 规则读取 `AGENTS.md`，由它指向权威文档 |

## 重新生成

```bash
python scripts/gen_agent_packs.py            # 生成 / 覆盖
python scripts/gen_agent_packs.py --check    # 只校验是否与源漂移（CI 用）
```

## 成员一览

| ID | 代号 | 职位 | 明确不做 |
|---|---|---|---|
| `r01-waquanju-ceo` | 蛙全局 | CEO 主理人 / 编排器 | 不替专业部门生产、不签质量结论、不签合同/动资金 |
| `r02-wapaibu-coo` | 蛙排布 | COO 首席运营官 | 不实现自动化（R17）、不生产业务、不定公司方向 |
| `r03-washouxian-cfo` | 蛙守线 | 财务合规官 / 红线负责人 | 不出持牌意见、不执行支付/签约（R14） |
| `r04-watiaoci-reviewer` | 蛙挑刺 | 独立评审官 | 不生产、不改稿、无成品不做猜测评价 |
| `r05-washenyuan-research` | 蛙深远 | 战略研究官 | 不替你拍板、无来源标待核实 |
| `r06-wadeqing-analyst` | 蛙得清 | 数据分析师 | 不制造确定性、正式财务/统计意见交 R03 |
| `r07-wademing-pm` | 蛙得明 | 产品经理 | 不写生产代码（R09） |
| `r08-wajiancheng-mvp` | 蛙建成 | 产品实现官 (MVP) | 不做生产级工程质量（R09） |
| `r09-wawenma-engineer` | 蛙稳码 | 代码工程官 | 不监控备份（R20）、不快速原型（R08） |
| `r10-wachengmei-design` | 蛙成美 | 视觉设计官 | 不写代码（R09） |
| `r11-wadianti-copy` | 蛙点题 | 内容主笔 | 不投放（R12） |
| `r12-wayingliu-growth` | 蛙引流 | 增长运营官 | 不写稿（R11） |
| `r13-wakecheng-csm` | 蛙客成 | 客户成功与销售运营官 | 不处理支付/履约（R14） |
| `r14-wajiaoyi-commerce` | 蛙交易 | 交易与收入履约官 | 不出财务意见（R03） |
| `r15-wagongying-erp` | 蛙供应 | ERP 与供应链运营官 | 不出财务意见（R03） |
| `r16-warenshi-hr` | 蛙人事 | 人员与组织运营官 | 薪酬输入交 R03 复核 |
| `r17-wazhiwang-automation` | 蛙织网 | 自动化与集成工程师 | 不实现业务逻辑（R09） |
| `r18-washucang-dataeng` | 蛙数仓 | 数据工程与管道官 | 不做分析结论（R06） |
| `r19-wazhimo-ml` | 蛙智模 | 模型工程与 AI 评估官 | 模型监控接口归 R20 |
| `r20-washouzhi-sre` | 蛙值守 | 可靠性与恢复官 | 不做应用实现（R09） |

> 边界与升级路径的权威说明见 `ORG.md` §三 编制表。
