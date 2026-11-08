"""20 个角色的注册表：能力的唯一事实来源。

每个角色 = 一个独立的本地 Agent；其能力域下整合升级了来源仓库中的多个
技能(skill)，而非整包复制。`capabilities` 列出该角色整合后的统一能力，
`inputs`/`outputs` 是它参与协作时的交接端口契约。

状态：
    implemented —— 已生成可运行 agent.py（r01..r20 全部）
    pending     —— 已登记，待生成 agent.py（当前无）
"""
from __future__ import annotations

from typing import Any, Dict, List

AGENTS_ROOT = None  # 运行时由 runner 注入绝对路径，避免目录耦合


ROLES: List[Dict[str, Any]] = [
    {
        "id": "r01", "name": "蛙全局", "title": "CEO 主理人 / 编排器",
        "dir": "r01-waquanju-ceo", "status": "implemented",
        "capabilities": ["意图识别与任务分级", "跨部门拆解", "经营与硬决策",
                         "反方质询", "公司OS与治理", "决策留痕与复盘",
                         "高层汇报与创始人陪练", "编排与验收"],
        "inputs": ["intent", "decision_memo"],
        "outputs": ["task_cards", "decision_log", "board_report"],
        "integrated_from": ["ognjengt__founder-skills",
                            "microsoft__agent-governance-toolkit",
                            "open-gsd__gsd-core", "wshobson__agents",
                            "Jeffallan__claude-skills"],
    },
    {
        "id": "r02", "name": "蛙排布", "title": "COO 首席运营官",
        "dir": "r02-wapaibu-coo", "status": "implemented",
        "capabilities": ["工作拆解与排期", "容量与委派", "交接与验收追踪",
                         "复盘与事故分析", "流程与SOP", "知识运营",
                         "项目群与Agent编排"],
        "inputs": ["goal", "task_cards"], "outputs": ["sprint_plan", "handoff_pkg"],
        "integrated_from": ["anthropics__knowledge-work-plugins",
                            "virgiliojr94__book-to-skill",
                            "tobi__qmd", "safishamsi__graphify"],
    },
    {
        "id": "r03", "name": "蛙守线", "title": "财务合规官 / 红线负责人",
        "dir": "r03-washouxian-cfo", "status": "implemented",
        "capabilities": ["报表月结", "CFO诊断", "税务边界", "合同政策",
                         "隐私数据安全", "AI治理", "审计留痕",
                         "广告/KYC-AML/投资风控"],
        "inputs": ["financials", "contracts", "data_flows"],
        "outputs": ["compliance_review", "risk_register"],
        "integrated_from": ["financial-services", "finance_skills",
                            "cfo-advisor", "compliance-os", "general-counsel-advisor"],
    },
    {
        "id": "r04", "name": "蛙挑刺", "title": "独立评审官",
        "dir": "r04-watiaoci-reviewer", "status": "implemented",
        "capabilities": ["成品核验", "硬门禁复核", "外置判据", "质量评价",
                         "事实来源检查", "保留优点复评", "人工评审工作流"],
        "inputs": ["artifact", "acceptance_criteria"],
        "outputs": ["pass_fail", "critique_report"],
        "integrated_from": ["petergyang__human-review",
                            "Intense-Visions__harness-engineering"],
    },
    {
        "id": "r05", "name": "蛙深远", "title": "战略研究官",
        "dir": "r05-washenyuan-research", "status": "implemented",
        "capabilities": ["深度研究", "行业扫描", "竞品情报", "商业模式",
                         "市场规模测算", "宏观情景", "研究自动化"],
        "inputs": ["topic", "scope"], "outputs": ["research_report", "evidence_ledger"],
        "integrated_from": ["karpathy__autoresearch",
                            "K-Dense-AI__scientific-agent-skills"],
    },
    {
        "id": "r06", "name": "蛙得清", "title": "数据分析师",
        "dir": "r06-wadeqing-analyst", "status": "implemented",
        "capabilities": ["指标语义建模", "数据清洗质量", "探索与产品分析",
                         "根因贡献度", "统计因果实验", "科学计算NLP",
                         "专业领域分析", "可视化报告", "自媒体数据运营"],
        "inputs": ["dataset", "metrics_spec"], "outputs": ["dataset", "analysis_report"],
        "integrated_from": ["nimrodfisher__data-analytics-skills", "py-why__dowhy",
                            "statsmodels__statsmodels", "scipy__scipy",
                            "explosion__spaCy", "Starlitnightly__omicverse",
                            "plotly__plotly.py", "data-analysis-report-agent",
                            "ai-data-visualization-prompts", "self-media-data-console"],
    },
    {
        "id": "r07", "name": "蛙得明", "title": "产品经理",
        "dir": "r07-wademing-pm", "status": "implemented",
        "capabilities": ["产品发现JTBD", "机会树用户研究", "用户故事PRD",
                         "优先级Backlog", "路线图发布", "愿景指标",
                         "技术翻译代码反推", "经验检索决策汇报"],
        "inputs": ["research_report", "voc"], "outputs": ["prd", "backlog"],
        "integrated_from": ["deanpeters__Product-Manager-Skills", "phuryn__pm-skills",
                            "phuryn__product-engineering",
                            "bzwh321__product-manager-agent-project-public",
                            "product-manager", "lihanglogan__code-to-prd",
                            "deanpeters__product-manager-prompts",
                            "Lucky2024-pllove__product-to-delivery-lifecycle-skills"],
    },
    {
        "id": "r08", "name": "蛙建成", "title": "产品实现官 (MVP)",
        "dir": "r08-wajiancheng-mvp", "status": "implemented",
        "capabilities": ["产品切片MVP", "Spec转仓库", "落地页H5",
                         "SaaS邮件脚手架", "跨平台原型", "组件设计实现", "质量验证交接"],
        "inputs": ["prd", "ui_brief"], "outputs": ["mvp", "page_assets"],
        "integrated_from": ["coreyhaines31__makerskills", "flutter__flutter",
                            "duncan-buildroom__freeskills", "product-manager"],
    },
    {
        "id": "r09", "name": "蛙稳码", "title": "代码工程官",
        "dir": "r09-wawenma-engineer", "status": "implemented",
        "capabilities": ["技术规格架构", "数据库API", "前后端全栈",
                         "跨端生产工程", "测试浏览器验证", "调试性能重构",
                         "迁移CI/CD安全", "特殊技术载体"],
        "inputs": ["mvp", "spec"], "outputs": ["production_code", "test_report"],
        "integrated_from": ["KarmenLoop__fullstack-web-delivery",
                            "wshobson__agents", "Jeffallan__claude-skills",
                            "mattpocock__skills", "browser-use__browser-use",
                            "snarktank__ralph", "open-gsd__gsd-core",
                            "obra__superpowers",
                            "godotengine__godot-demo-projects"],
    },
    {
        "id": "r10", "name": "蛙成美", "title": "视觉设计官",
        "dir": "r10-wachengmei-design", "status": "implemented",
        "capabilities": ["AI生图插画", "Logo图标VI", "产品UI/UX",
                         "交互原型动效", "修图图像工程", "视频音频处理",
                         "转写字幕", "数据视觉营销物料"],
        "inputs": ["brand_brief", "content"], "outputs": ["visual_assets", "vi"],
        "integrated_from": ["design-skills", "brand-toolkit", "logo-design-skill",
                            "Pillow", "opencv", "rembg", "FFmpeg", "faster-whisper"],
    },
    {
        "id": "r11", "name": "蛙点题", "title": "内容主笔",
        "dir": "r11-wadianti-copy", "status": "implemented",
        "capabilities": ["内容策略选题", "SEO/AEO", "钩子提纲",
                         "文案长文", "品牌语调编辑", "广告公关",
                         "多平台适配", "持续本地化"],
        "inputs": ["topic", "audience"], "outputs": ["content_draft", "publish_list"],
        "integrated_from": ["alirezarezvani__aeo-box",
                            "bzwh321__article-director-public",
                            "WeblateOrg__weblate"],
    },
    {
        "id": "r12", "name": "蛙引流", "title": "增长运营官",
        "dir": "r12-wayingliu-growth", "status": "implemented",
        "capabilities": ["增长诊断基线", "增长循环自然获客", "冷启动外联",
                         "红人合作增长", "ASO发布", "付费投放CRO",
                         "激活留存推荐", "归因RevOps", "自媒体运营"],
        "inputs": ["content_draft", "product"], "outputs": ["growth_plan", "channel_assets"],
        "integrated_from": ["coreyhaines31__marketingskills",
                            "retieedra-profound__skills-marketing-library",
                            "bzwh321__self-media-data-console-bzwh"],
    },
    {
        "id": "r13", "name": "蛙客成", "title": "客户成功与销售运营官",
        "dir": "r13-wakecheng-csm", "status": "implemented",
        "capabilities": ["客户与联系人管理", "销售管道", "销售活动与跟进",
                         "全渠道客服", "客户反馈VOC", "客户健康续约",
                         "服务知识与升级", "客户运营自动化接口"],
        "inputs": ["lead", "order_status"], "outputs": ["crm_record", "voc"],
        "integrated_from": ["twentyhq__twenty", "chatwoot__chatwoot",
                            "formbricks__formbricks"],
    },
    {
        "id": "r14", "name": "蛙交易", "title": "交易与收入履约官",
        "dir": "r14-wajiaoyi-commerce", "status": "implemented",
        "capabilities": ["商品电商后端", "订阅计量计费", "支付集成",
                         "电子签审计", "服务预约", "交易状态编排",
                         "收入数据接口", "交易自动化接口"],
        "inputs": ["package", "quotation"], "outputs": ["order", "payment_status"],
        "integrated_from": ["medusajs__medusa", "getlago__lago", "stripe__stripe-node",
                            "documenso__documenso", "alextselegidis__easyappointments"],
    },
    {
        "id": "r15", "name": "蛙供应", "title": "ERP 与供应链运营官",
        "dir": "r15-wagongying-erp", "status": "implemented",
        "capabilities": ["采购供应商", "库存仓库", "销售履约记录",
                         "生产服务资源", "ERP财务接口", "主数据权限", "运营报表"],
        "inputs": ["order", "sop"], "outputs": ["purchase_order", "inventory_ledger"],
        "integrated_from": ["frappe__erpnext"],
    },
    {
        "id": "r16", "name": "蛙人事", "title": "人员与组织运营官",
        "dir": "r16-warenshi-hr", "status": "implemented",
        "capabilities": ["招聘与入职", "人员与合同档案", "考勤与休假",
                         "绩效与目标", "薪酬准备", "费用与福利业务", "组织运营报表"],
        "inputs": ["org_decision", "roles"], "outputs": ["roster", "payroll_input"],
        "integrated_from": ["frappe__hrms", "frappe__erpnext", "frappe-ui"],
    },
    {
        "id": "r17", "name": "蛙织网", "title": "自动化与集成工程师",
        "dir": "r17-wazhiwang-automation", "status": "implemented",
        "capabilities": ["SaaS/API集成", "Webhook事件", "字段身份映射",
                         "定时批处理", "人工审批", "失败重试", "AI工作流", "审计"],
        "inputs": ["rules", "fields"], "outputs": ["workflow", "audit_log"],
        "integrated_from": ["n8n-io__n8n"],
    },
    {
        "id": "r18", "name": "蛙数仓", "title": "数据工程与管道官",
        "dir": "r18-washucang-dataeng", "status": "implemented",
        "capabilities": ["数据连接ELT", "数仓转换", "管道调度",
                         "数据质量门禁", "批流增量", "数据目录", "人工审批运维"],
        "inputs": ["source", "metrics_spec"], "outputs": ["dataset", "data_catalog"],
        "integrated_from": ["airbytehq__airbyte", "dbt-labs__dbt", "apache__airflow"],
    },
    {
        "id": "r19", "name": "蛙智模", "title": "模型工程与 AI 评估官",
        "dir": "r19-wazhimo-ml", "status": "implemented",
        "capabilities": ["实验追踪", "模型注册与版本", "评估数据集与评分器",
                         "Agent Trace 与调试", "回归与发布候选", "模型监控接口",
                         "模型资产说明"],
        "inputs": ["dataset", "model"], "outputs": ["experiment_log", "evaluation"],
        "integrated_from": ["mlflow__mlflow"],
    },
    {
        "id": "r20", "name": "蛙值守", "title": "可靠性与恢复官",
        "dir": "r20-washouzhi-sre", "status": "implemented",
        "capabilities": ["可用性监控", "告警升级", "状态页沟通",
                         "加密增量备份", "恢复演练", "灾难恢复回滚", "运行复盘"],
        "inputs": ["topology", "asset_list"], "outputs": ["monitor_config", "backup_repo"],
        "integrated_from": ["restic__restic", "louislam__uptime-kuma"],
    },
]


def by_id(role_id: str) -> Dict[str, Any]:
    for r in ROLES:
        if r["id"] == role_id:
            return r
    raise KeyError(f"未知角色: {role_id}")


def implemented() -> List[Dict[str, Any]]:
    return [r for r in ROLES if r["status"] == "implemented"]


def all_summary() -> str:
    lines = ["id   角色     状态        标题"]
    for r in ROLES:
        lines.append(f"{r['id']}  {r['name']:　<4}  {r['status']:<11} {r['title']}")
    return "\n".join(lines)