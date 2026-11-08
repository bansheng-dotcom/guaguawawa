# -*- coding: utf-8 -*-
"""为 R01~R20（跳过 R06）生成「认知注入」资产（META-001 Stage 4）。

每个角色产出四件套，全部可直接被 `case` / `diagnose` 类命令消费：
    1. cases/<case_id>/case.json          业务诊断场景（问题 + 技能 + 产物）
    2. cases/<case_id>/semantic_layer.json 指标语义层（口径 / 门禁 / 边界 / 决策序）
    3. cases/<case_id>/experience/priority_rules.md   多门禁冲突时的优先级
    4. cases/<case_id>.md（角色根 cases/ 下）业务诊断 SOP（逻辑导图 + 分步动作）
    5. configs/<role>.json                角色运行配置（阈值 / 维度 / 数据源 / KPI）

内容严格来自各角色既有能力域与真实示例输入，不复制 R06 私有资产。

用法：
    python agents/scripts/upgrade/inject_knowledge.py --dry-run
    python agents/scripts/upgrade/inject_knowledge.py
"""
from __future__ import annotations

import json
import os
import sys

AGENTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP = {"r06-wadeqing-analyst"}

PROFILES = {
    "r01": {
        "dir": "r01-waquanju-ceo", "name": "蛙全局", "title": "CEO / 战略总控",
        "case_id": "budget-rebalance",
        "display": "季度预算再平衡与不可逆动作授权",
        "question": "本季度自由现金流 8.6 万、单一渠道贡献 62%，是否批准把 40% 预算向该渠道倾斜，并冻结两条边缘业务？",
        "artifacts": ["task_cards", "decision_log", "board_report"],
        "skills": ["intent", "decide", "redteam", "boardroom"],
        "kpis": [
            {"id": "fcf_month", "name": "自由现金流安全月数", "formula": "期末现金 / 近 3 月平均净流出",
             "unit": "月", "target": "≥ 6", "alert": "< 4 立即熔断"},
            {"id": "single_source_share", "name": "单一营收来源占比", "formula": "最大营收线收入 / 总营收",
             "unit": "%", "target": "≤ 70%", "alert": "> 70% 强制第二曲线议题"},
        ],
        "gates": [
            {"id": "G1", "when": "不可逆动作（签约/扣款/裁员）缺人类签字", "verdict": "BLOCKER",
             "action": "拒绝执行，退回补授权"},
            {"id": "G2", "when": "自由现金流安全月数 < 4", "verdict": "BLOCKER",
             "action": "冻结一切新增开支，先出止损方案"},
            {"id": "G3", "when": "决策未写成功标准与杀死标准", "verdict": "WARN",
             "action": "退回补齐标准后再拍板"},
        ],
        "boundary": [
            {"out_of_scope": "替代 CFO 出财务口径", "owner": "R03"},
            {"out_of_scope": "替代业务角色出执行细节", "owner": "R02/R07/R12"},
        ],
        "priority": ["不可逆动作授权 > 现金流安全 > 战略聚焦 > 速度",
                     "现金流熔断触发时，一切增长提案自动降级为观察项",
                     "两个提案冲突时，保留可回收现金更多、可逆性更高者"],
        "sop_steps": [
            "收口意图：把一句话意图写成「成功标准 / 杀死标准 / 可逆性等级」三段。",
            "分级判断：命中不可逆动作即挂起，等创始人书面签字。",
            "交叉质询：让 redteam 出至少 3 条反方意见，逐条给数据回应。",
            "预算再平衡：按边际 ROI 排序，砍最低者，禁止平均主义。",
            "出董事会汇报包：结论先行 + 三档方案 + 熔断线 + 灰度节奏。",
        ],
    },
    "r02": {
        "dir": "r02-wapaibu-coo", "name": "蛙排布", "title": "COO / 运营效能",
        "case_id": "sprint-overload",
        "display": "冲刺容量过载与交付节拍回溯",
        "question": "双 11 渠道冲刺 5 项任务合计 4 人日、最长依赖 5 步，其中 r09 加权负载 112.5%，是砍范围、加人还是拆包？",
        "artifacts": ["sprint_plan", "handoff_pkg", "retro"],
        "skills": ["schedule", "capacity", "handoff", "retro"],
        "kpis": [
            {"id": "overflow_rate", "name": "交付周期溢出率", "formula": "(实际交付天数 − 计划天数) / 计划天数",
             "unit": "%", "target": "≤ 10%", "alert": "> 20% 触发全链路回溯"},
            {"id": "concurrent", "name": "单人并发任务数", "formula": "同一 owner 处于 running 的任务数",
             "unit": "个", "target": "≤ 3", "alert": "> 3 强制委派或拆分"},
        ],
        "gates": [
            {"id": "G1", "when": "WBS kind 越界或 step 断档", "verdict": "BLOCKER",
             "action": "拒绝排期，先修拆解"},
            {"id": "G2", "when": "加权负载 > 100%", "verdict": "CRITICAL",
             "action": "先减负再派工，不允许带病排期"},
            {"id": "G3", "when": "任务 > 8h 未拆分", "verdict": "CRITICAL",
             "action": "按 Σ 恒等拆成 ≤8h 子任务"},
        ],
        "boundary": [
            {"out_of_scope": "替代产品角色定优先级", "owner": "R07"},
            {"out_of_scope": "替代财务核预算", "owner": "R03"},
        ],
        "priority": ["WBS 结构非法 > 一切（拆解错则全盘错）",
                     "容量过载 > 单项目红线 > 派工包完整性",
                     "关键路径冲突优先保资源，浮动任务让路"],
        "sop_steps": [
            "先看 WBS：kind 是否越界、step 是否断档，结构错直接退回。",
            "再看容量：加权负载 > 100% 先减负，不允许靠加班消化。",
            "拆大任务：> 8h 一律拆成 ≤8h 子任务，保证 Σ 恒等。",
            "排关键路径：浮动为 0 的任务优先锁资源。",
            "出交接包：owner / 产物 / 复现步骤 / 验收判据齐全才放行。",
        ],
    },
    "r03": {
        "dir": "r03-washouxian-cfo", "name": "蛙守先", "title": "CFO / 财务风控",
        "case_id": "runway-crisis",
        "display": "现金跑道压缩与渠道止损",
        "question": "模拟期第 5 个月现金耗尽、烧钱倍数 5.03x，四个触发器同时命中，该先融资还是先砍成本？砍哪些渠道？",
        "artifacts": ["compliance_review", "risk_register", "cashflow_plan"],
        "skills": ["cfo", "financial", "audit", "risk"],
        "kpis": [
            {"id": "runway", "name": "现金可支撑月数", "formula": "期末现金 / 月均净烧钱",
             "unit": "月", "target": "≥ 9", "alert": "< 4 启动止损预案"},
            {"id": "burn_multiple", "name": "烧钱倍数", "formula": "净烧钱 / 净新增 ARR",
             "unit": "×", "target": "≤ 2.0", "alert": "> 3.0 冻结扩张"},
            {"id": "cac_payback", "name": "CAC 回收期", "formula": "CAC / 月毛利/客户",
             "unit": "天", "target": "≤ 30", "alert": "> 45 暂停该渠道"},
        ],
        "gates": [
            {"id": "G1", "when": "跨表勾稽差异率 > 0.1%", "verdict": "BLOCKER",
             "action": "阻断结账，先查差异"},
            {"id": "G2", "when": "现金流安全月数 < 4", "verdict": "BLOCKER",
             "action": "启动止损预案并上报 R01"},
            {"id": "G3", "when": "报告出现未标注模拟的财务数字", "verdict": "BLOCKER",
             "action": "作废并重出，标注数据来源"},
        ],
        "boundary": [
            {"out_of_scope": "代客户执行付款/报税", "owner": "人工 + 持牌机构"},
            {"out_of_scope": "解释合同法律效力", "owner": "律师"},
        ],
        "priority": ["合规红线 > 现金流安全 > 增长投入",
                     "同时命中多个触发器时，按「先止血、再融资、后扩张」顺序",
                     "止损与增长冲突时，保留回收期 ≤45 天的渠道"],
        "sop_steps": [
            "先做勾稽：三表差异 > 0.1% 一律先查账，不进入分析。",
            "算跑道：期末现金 / 月均净烧钱，给出耗尽月份。",
            "算烧钱倍数：净烧钱 / 净新增 ARR，> 3x 冻结扩张。",
            "渠道止损：按 CAC 回收期排序，>45 天当日停投。",
            "出决策书：止血方案 + 融资窗口 + 熔断线，交 R01 拍板。",
        ],
    },
    "r04": {
        "dir": "r04-watiaoci-reviewer", "name": "蛙挑刺", "title": "Reviewer / 对抗质检",
        "case_id": "artifact-reject",
        "display": "交付物证据链缺失的驳回裁定",
        "question": "两份交付工件声称已完成，但其中一处只有占位实现，L2 实质性证据不足，应判 PASS 还是有条件驳回？",
        "artifacts": ["pass_fail", "critique_report"],
        "skills": ["artifact", "criteria", "facts", "quality"],
        "kpis": [
            {"id": "l2_completeness", "name": "L2 实质性证据完备度", "formula": "已提供实质证据条目 / 应提供条目",
             "unit": "%", "target": "100%", "alert": "< 100% 即刻驳回"},
            {"id": "stub_hits", "name": "占位实现命中数", "formula": "stub/TODO/NotImplemented 出现次数",
             "unit": "处", "target": "0", "alert": "≥ 1 判不通过"},
        ],
        "gates": [
            {"id": "G1", "when": "L1 存在性通过但 L2 实质性为空", "verdict": "BLOCKER",
             "action": "判 REJECT，退回补证"},
            {"id": "G2", "when": "发现 stub/TODO 占位实现", "verdict": "BLOCKER",
             "action": "判不通过，不得进入下游"},
            {"id": "G3", "when": "结论无来源引用", "verdict": "BLOCKER",
             "action": "驳回并要求标注来源"},
        ],
        "boundary": [
            {"out_of_scope": "替作者改稿", "owner": "原作者"},
            {"out_of_scope": "代替业务方定优先级", "owner": "R07/R01"},
        ],
        "priority": ["证据链完整性 > 表达质量 > 交付速度",
                     "L2 实质性缺失一律驳回，不接受「先过再补」",
                     "多处缺口并存时，先驳硬阻断，再列改进项"],
        "sop_steps": [
            "先查 L1：产物是否真的存在（文件/接口/记录）。",
            "再查 L2：内容是否有实质实现，还是只有占位与声明。",
            "再查 L3：是否真的接到调用链，而不是孤立文件。",
            "抽查事实：抽样 3 条结论回溯到源头，无源即驳。",
            "出裁定：PASS / 有条件 PASS / REJECT，每条附证据位置。",
        ],
    },
    "r05": {
        "dir": "r05-washenyuan-research", "name": "蛙深远", "title": "Research / 商业研究",
        "case_id": "market-sizing",
        "display": "细分市场空间测算与置信区间收敛",
        "question": "两个口径测算出的 TAM 都是 120 亿但上下限完全重合，是巧合还是口径没打通？该不该对外给结论？",
        "artifacts": ["research_report", "evidence_ledger"],
        "skills": ["sizing", "industry", "competitor", "scenario"],
        "kpis": [
            {"id": "ci_width", "name": "市场空间置信区间宽度", "formula": "(上限 − 下限) / 中值",
             "unit": "%", "target": "≤ 40%", "alert": "> 40% 只出方向性结论"},
            {"id": "source_coverage", "name": "结论带来源比例", "formula": "有来源结论数 / 结论总数",
             "unit": "%", "target": "100%", "alert": "< 100% 作废"},
        ],
        "gates": [
            {"id": "G1", "when": "双口径互证偏离 > 40%", "verdict": "WARN",
             "action": "降级为方向性结论，不出具体数字"},
            {"id": "G2", "when": "竞品覆盖 < 3 家", "verdict": "BLOCKER",
             "action": "不得出竞品结论"},
            {"id": "G3", "when": "结论无来源", "verdict": "BLOCKER",
             "action": "作废重写"},
        ],
        "boundary": [
            {"out_of_scope": "替产品定需求", "owner": "R07"},
            {"out_of_scope": "替增长定投放预算", "owner": "R12"},
        ],
        "priority": ["来源可追溯 > 覆盖面 > 结论锐度",
                     "置信区间过宽时只给方向，不给数字",
                     "结论冲突时，以更保守口径对外"],
        "sop_steps": [
            "锁口径：先写清 TAM/SAM/SOM 的定义与数据边界。",
            "双口径互证：自下而上 + 自上而下，偏离 > 40% 即降级。",
            "竞品扫描：至少 5 家，覆盖价格带与打法。",
            "情景推演：乐观/中性/悲观三档，标注假设。",
            "出研报：结论 + 证据台账 + 待验证清单。",
        ],
    },
    "r07": {
        "dir": "r07-wademing-pm", "name": "蛙得名", "title": "PM / 产品规划",
        "case_id": "feature-coldstart",
        "display": "新功能冷启动未过门禁的迭代决策",
        "question": "PRD 八门禁只过 1 项，但业务方要求本周上线抢窗口，是驳回重写还是切最小可用范围？",
        "artifacts": ["prd", "backlog"],
        "skills": ["prd", "priority", "metrics", "roadmap"],
        "kpis": [
            {"id": "prd_grade", "name": "PRD 门禁得分", "formula": "通过门禁数 / 总门禁数 × 100",
             "unit": "分", "target": "≥ 80", "alert": "< 60 禁止进开发"},
            {"id": "jump_loss", "name": "主流程跳失率增幅", "formula": "上线后跳失率 − 上线前跳失率",
             "unit": "%", "target": "≤ 2%", "alert": "> 5% 停止扩量"},
        ],
        "gates": [
            {"id": "G1", "when": "PRD 缺验收判据", "verdict": "BLOCKER",
             "action": "退回补验收标准"},
            {"id": "G2", "when": "北极星指标无法定义", "verdict": "BLOCKER",
             "action": "退回定义指标"},
            {"id": "G3", "when": "需求变更 > 3 次", "verdict": "WARN",
             "action": "冻结迭代"},
        ],
        "boundary": [
            {"out_of_scope": "替代工程估时", "owner": "R09"},
            {"out_of_scope": "替代视觉定稿", "owner": "R10"},
        ],
        "priority": ["验收判据缺失 > 内容不完整 > 排版问题",
                     "抢窗口与门禁冲突时，先切最小可用范围，不带病全量",
                     "多需求竞争时按 RICE 排序，Top1 优先"],
        "sop_steps": [
            "过八门禁：定位未过项，判断是缺判据还是缺数据。",
            "切 MVP：把范围砍到能验证核心假设的最小集。",
            "定指标：北极星 + 过程指标 + 反指标三件套。",
            "排优先级：RICE 打分，解释每个因子取值依据。",
            "出 PRD：用户故事 + 验收 + 埋点清单。",
        ],
    },
    "r08": {
        "dir": "r08-wajiancheng-mvp", "name": "蛙建成", "title": "MVP / 敏捷交付",
        "case_id": "mvp-launch",
        "display": "MVP 切片上线与首屏性能权衡",
        "question": "落地页切片已可用，但首屏 3.2s、核心路径报错率 0.6%，要不要先上线再优化？",
        "artifacts": ["mvp", "page_assets"],
        "skills": ["slice", "landing", "prototype", "qa"],
        "kpis": [
            {"id": "error_rate", "name": "核心路径报错率", "formula": "报错会话 / 总会话",
             "unit": "%", "target": "≤ 0.1%", "alert": "> 0.5% 回滚"},
            {"id": "tti", "name": "移动端首屏可交互时间", "formula": "Performance TTI 中位数",
             "unit": "s", "target": "≤ 2", "alert": "> 3 不得放量"},
        ],
        "gates": [
            {"id": "G1", "when": "核心路径报错率 > 0.5%", "verdict": "BLOCKER",
             "action": "回滚上一版本"},
            {"id": "G2", "when": "功能点数 > 8", "verdict": "WARN",
             "action": "退回做减法"},
            {"id": "G3", "when": "无可用回滚路径", "verdict": "BLOCKER",
             "action": "禁止上线"},
        ],
        "boundary": [
            {"out_of_scope": "长期架构演进", "owner": "R09"},
            {"out_of_scope": "持续监控告警建设", "owner": "R20"},
        ],
        "priority": ["可回滚 > 稳定性 > 性能 > 功能数量",
                     "报错率破线一律先回滚再排查",
                     "首屏超标优先做减法，不加机器"],
        "sop_steps": [
            "切最小切片：只保留验证核心假设所需的功能点。",
            "先跑通再优化：确保有回滚路径与开关。",
            "压首屏：图片压缩、懒加载、关键 CSS 内联。",
            "验核心路径：主流程点击全链路走一遍。",
            "出交接：给 R09 补工程债清单，给 R20 补探活清单。",
        ],
    },
    "r09": {
        "dir": "r09-wawenma-engineer", "name": "蛙稳码", "title": "Engineer / 架构工程",
        "case_id": "refactor-capacity",
        "display": "核心系统重构的容量与测试覆盖门禁",
        "question": "重构后单测覆盖率 87%、跳过 0 条，但 P99 从 180ms 涨到 420ms，能否合并主干并扩容上线？",
        "artifacts": ["production_code", "test_report"],
        "skills": ["testing", "debug", "ops", "spec"],
        "kpis": [
            {"id": "p99", "name": "API P99 延时", "formula": "P99 响应时间（压测）",
             "unit": "ms", "target": "≤ 200", "alert": "> 500 熔断降级"},
            {"id": "coverage", "name": "单元测试覆盖率", "formula": "已覆盖行 / 总行",
             "unit": "%", "target": "≥ 80", "alert": "< 60 禁止合并"},
            {"id": "skipped", "name": "跳过用例数", "formula": "skip/xfail 计数",
             "unit": "条", "target": "0", "alert": "≥ 1 判假通过"},
        ],
        "gates": [
            {"id": "G1", "when": "存在 skip/xfail 掩盖失败", "verdict": "BLOCKER",
             "action": "判假通过，拒绝合并"},
            {"id": "G2", "when": "P99 > 500ms", "verdict": "BLOCKER",
             "action": "熔断降级，回滚变更"},
            {"id": "G3", "when": "无回滚脚本", "verdict": "BLOCKER",
             "action": "禁止发布"},
        ],
        "boundary": [
            {"out_of_scope": "线上持续监控与告警", "owner": "R20"},
            {"out_of_scope": "快速原型验证", "owner": "R08"},
        ],
        "priority": ["不跳过测试 > 性能 > 覆盖率 > 交付速度",
                     "性能破线优先定位热点，不加机器掩盖",
                     "覆盖率不足时先补关键分支，不追数字"],
        "sop_steps": [
            "先跑测试：确认无 skip、无假通过。",
            "看覆盖率：关键分支是否覆盖，缺口列清单。",
            "压性能：定位 P99 热点，给出优化或回滚方案。",
            "备回滚：迁移脚本必须可逆，且有验证步骤。",
            "出报告：变更点 + 风险 + 回滚路径 + 观察指标。",
        ],
    },
    "r10": {
        "dir": "r10-wachengmei-design", "name": "蛙成美", "title": "Design / 创意视觉",
        "case_id": "brand-refresh",
        "display": "品牌视觉改版与渲染性能权衡",
        "question": "新 VI 三套方案中 A 方案转化最好但首屏渲染阻滞 380ms，B 方案快 40ms 但识别度弱，选哪个？",
        "artifacts": ["visual_assets", "vi"],
        "skills": ["logo", "uiux", "brand", "render"],
        "kpis": [
            {"id": "render_block", "name": "视觉资源渲染阻滞", "formula": "首屏视觉资源阻塞主线程时长",
             "unit": "ms", "target": "≤ 150", "alert": "> 300 优化图层"},
            {"id": "token_coverage", "name": "设计 Token 覆盖率", "formula": "使用 Token 的属性 / 总属性",
             "unit": "%", "target": "100%", "alert": "< 80% 禁止交付前端"},
        ],
        "gates": [
            {"id": "G1", "when": "对比度 < 3:1", "verdict": "BLOCKER",
             "action": "判定不可用，重做配色"},
            {"id": "G2", "when": "渲染阻滞 > 300ms", "verdict": "WARN",
             "action": "优化图层或降级素材"},
            {"id": "G3", "when": "Token 覆盖率 < 80%", "verdict": "BLOCKER",
             "action": "禁止交付前端"},
        ],
        "boundary": [
            {"out_of_scope": "替代文案定语调", "owner": "R11"},
            {"out_of_scope": "替代前端实现交互", "owner": "R08/R09"},
        ],
        "priority": ["可读性 > 一致性 > 视觉冲击 > 文件体积",
                     "性能与美感冲突时，先保性能再降复杂度",
                     "改版验证前不删除旧素材，保留回滚"],
        "sop_steps": [
            "定 Token：颜色/字号/间距先出规范，再出稿。",
            "查对比度：正文 ≥4.5:1，大字 ≥3:1。",
            "压资源：图片转 WebP、控制首屏体积。",
            "出三套方案：附转化假设与验证方式。",
            "交付：Token + 切图 + 动效说明，交 R08/R09 落地。",
        ],
    },
    "r11": {
        "dir": "r11-wadianti-copy", "name": "蛙点题", "title": "Copy / 文案操盘",
        "case_id": "headline-test",
        "display": "爆款标题测试与跳失率归因",
        "question": "标题 A 点击率 8.2% 但进店跳失 18%，标题 B 点击率 5.4% 跳失 6%，该主推哪条？",
        "artifacts": ["content_draft", "publish_list"],
        "skills": ["topic", "hook", "copy", "seo"],
        "kpis": [
            {"id": "bounce", "name": "进店后首跳跳失率", "formula": "首跳离开会话 / 进店会话",
             "unit": "%", "target": "≤ 8%", "alert": "> 15% 修正标题歧义"},
            {"id": "forbidden", "name": "违禁词命中数", "formula": "命中平台违禁词表次数",
             "unit": "处", "target": "0", "alert": "≥ 1 禁止发布"},
        ],
        "gates": [
            {"id": "G1", "when": "违禁词命中", "verdict": "BLOCKER",
             "action": "禁止发布，改写"},
            {"id": "G2", "when": "标题承诺与正文不符", "verdict": "BLOCKER",
             "action": "判为标题党，退回重写"},
            {"id": "G3", "when": "字数超出平台区间", "verdict": "WARN",
             "action": "按平台重剪"},
        ],
        "boundary": [
            {"out_of_scope": "替代设计出视觉", "owner": "R10"},
            {"out_of_scope": "替代投放定预算", "owner": "R12"},
        ],
        "priority": ["合规 > 承诺一致性 > 点击率 > 文采",
                     "高点击高跳失时判为标题歧义，立即改写",
                     "多版本并存时用 A/B 显著性决定，不靠感觉"],
        "sop_steps": [
            "定选题：先确认人群与场景，不写泛泛主题。",
            "写钩子：前 3 秒给出冲突或利益点。",
            "查合规：过违禁词表与平台规则。",
            "做 A/B：同选题两条标题，看点击与跳失双指标。",
            "定稿归档：把有效钩子结构写回选题库。",
        ],
    },
    "r12": {
        "dir": "r12-wayingliu-growth", "name": "蛙引流", "title": "Growth / 增长黑客",
        "case_id": "channel-attribution",
        "display": "多渠道获客归因与预算再分配",
        "question": "抖音渠道 ROI 1:3.2 但伪泛粉 42%，小红书 ROI 1:1.8 但次留 31%，预算该往哪边加？",
        "artifacts": ["growth_plan", "channel_assets"],
        "skills": ["diagnose", "paid", "retention", "revops"],
        "kpis": [
            {"id": "fake_ratio", "name": "伪泛粉占比", "formula": "无效互动用户 / 新增用户",
             "unit": "%", "target": "≤ 20%", "alert": "> 40% 立即调整定向"},
            {"id": "roi", "name": "渠道 ROI", "formula": "渠道毛利 / 渠道花费",
             "unit": "×", "target": "≥ 2", "alert": "< 1.5 连续 3 天停投"},
            {"id": "d1", "name": "次留率", "formula": "次日回访用户 / 新增用户",
             "unit": "%", "target": "≥ 25", "alert": "< 15 判定渠道无效"},
        ],
        "gates": [
            {"id": "G1", "when": "伪泛粉 > 40%", "verdict": "BLOCKER",
             "action": "停机复审定向"},
            {"id": "G2", "when": "归因窗口不一致", "verdict": "WARN",
             "action": "统一归因口径后再比较"},
            {"id": "G3", "when": "单位经济为负仍加投", "verdict": "BLOCKER",
             "action": "立即停投"},
        ],
        "boundary": [
            {"out_of_scope": "替代财务算毛利", "owner": "R03"},
            {"out_of_scope": "替代产品改承接页", "owner": "R07/R08"},
        ],
        "priority": ["单位经济为正 > 留存质量 > 规模速度",
                     "伪泛粉破线时先停投再谈优化",
                     "多渠冲突时按「回收期 × 次留」综合排序"],
        "sop_steps": [
            "统一口径：先对齐归因窗口与去重规则。",
            "拆漏斗：曝光→点击→进店→注册→付费，找最大损失节点。",
            "查质量：伪泛粉、次留、复购三项一起看。",
            "算单位经济：ROI 与回收期双指标。",
            "出预算表：加投/维持/停投三档，附熔断线。",
        ],
    },
    "r13": {
        "dir": "r13-wakecheng-csm", "name": "蛙客成", "title": "CSM / 客户成功",
        "case_id": "churn-warning",
        "display": "高净值客户流失预警与挽回",
        "question": "4 名客户平均健康分 66.4、1 名 at_risk、NDR 94%，是否启动专项挽回？先救谁？",
        "artifacts": ["crm_record", "voc"],
        "skills": ["health", "voc", "support", "pipeline"],
        "kpis": [
            {"id": "ndr", "name": "月度活跃净留存", "formula": "(期初 MRR + 扩张 − 流失 − 降级) / 期初 MRR",
             "unit": "%", "target": "≥ 100", "alert": "< 95 启动挽回"},
            {"id": "health", "name": "平均健康分", "formula": "加权（使用频次/工单/续约意愿）",
             "unit": "分", "target": "≥ 70", "alert": "< 60 全量排查"},
        ],
        "gates": [
            {"id": "G1", "when": "NDR < 95%", "verdict": "BLOCKER",
             "action": "启动专项挽回并上报 R01"},
            {"id": "G2", "when": "P1 工单首响 > 8h", "verdict": "WARN",
             "action": "升级值班，补 SLA"},
            {"id": "G3", "when": "续约前 30 天无触达记录", "verdict": "WARN",
             "action": "强制排期触达"},
        ],
        "boundary": [
            {"out_of_scope": "承诺产品功能排期", "owner": "R07"},
            {"out_of_scope": "承诺价格折扣", "owner": "R01/R03"},
        ],
        "priority": ["高价值客户 > 高流失概率 > 工单紧急度",
                     "NDR 破线时先救 ARR 最大的 at_risk 客户",
                     "VOC 高频问题优先转化为产品需求"],
        "sop_steps": [
            "算健康分：使用深度、工单情绪、续约意愿三项加权。",
            "筛 at_risk：分数 < 60 或使用断崖式下滑。",
            "排优先级：按 ARR × 流失概率排序，先救大头。",
            "定挽回动作：48h 内一对一触达，出书面方案。",
            "闭环：VOC 进需求池，SLA 缺口进流程整改。",
        ],
    },
    "r14": {
        "dir": "r14-wajiaoyi-commerce", "name": "蛙交易", "title": "Commerce / 电商操盘",
        "case_id": "funnel-pricing",
        "display": "单品漏斗诊断与定价决策",
        "question": "单品订单总额 1046 元、支付成功率 96%、退款率上升 1.8%，该降价冲量还是提价保毛利？",
        "artifacts": ["order", "payment_status", "revenue"],
        "skills": ["order", "catalog", "payment", "revenue"],
        "kpis": [
            {"id": "refund_rate", "name": "退款率增幅", "formula": "本期退款率 − 基期退款率",
             "unit": "%", "target": "≤ 1.0", "alert": "> 1.5 暂停活动"},
            {"id": "pay_success", "name": "支付成功率", "formula": "支付成功单 / 下单单",
             "unit": "%", "target": "≥ 98", "alert": "< 95 回滚支付配置"},
            {"id": "aov", "name": "客单价", "formula": "GMV / 订单数",
             "unit": "元", "target": "环比不降 3%", "alert": "降 > 3% 强制回滚"},
        ],
        "gates": [
            {"id": "G1", "when": "到手价低于成本线", "verdict": "BLOCKER",
             "action": "立即下架"},
            {"id": "G2", "when": "退款率增幅 > 1.5%", "verdict": "BLOCKER",
             "action": "暂停活动并排查"},
            {"id": "G3", "when": "退款额度 > 原支付金额", "verdict": "BLOCKER",
             "action": "拒绝，退回补正"},
        ],
        "boundary": [
            {"out_of_scope": "实际发起退款/扣款", "owner": "人工授权后执行"},
            {"out_of_scope": "财务口径与税务处理", "owner": "R03"},
            {"out_of_scope": "实物退货入库", "owner": "R15"},
        ],
        "priority": ["合规与不破价 > 履约质量 > 支付成功率 > 转化率",
                     "退款破线时先停活动再查描述一致性",
                     "定价冲突时先保毛利，再谈规模"],
        "sop_steps": [
            "算漏斗：曝光→详情→加购→下单→支付，找最大损失节点。",
            "查价格：到手价是否破成本线，是否与竞品拉开。",
            "查履约：退款率与描述一致性、物流时效相关性。",
            "做定价实验：小流量 A/B，看转化与毛利双指标。",
            "出决策：定价方案 + 熔断线 + 灰度节奏。",
        ],
    },
    "r15": {
        "dir": "r15-wagongying-erp", "name": "蛙供应", "title": "ERP / 供应链",
        "case_id": "stockout-risk",
        "display": "核心品类安全库存与断货预警",
        "question": "核心物料再订货点 120、在库 90、在途 40，周转天数 62 天，是先补货还是先清库？",
        "artifacts": ["purchase_order", "inventory_ledger"],
        "skills": ["inventory", "procurement", "fulfillment", "report"],
        "kpis": [
            {"id": "safety_days", "name": "安全库存天数", "formula": "可用库存 / 日均消耗",
             "unit": "天", "target": "≥ 14", "alert": "< 7 紧急补货"},
            {"id": "turnover", "name": "库存周转天数", "formula": "平均库存 / 日均销货成本",
             "unit": "天", "target": "≤ 45", "alert": "> 60 清库"},
        ],
        "gates": [
            {"id": "G1", "when": "安全库存 < 7 天", "verdict": "BLOCKER",
             "action": "当日下补货单"},
            {"id": "G2", "when": "三单匹配率 < 95%", "verdict": "BLOCKER",
             "action": "暂停付款"},
            {"id": "G3", "when": "周转 > 60 天", "verdict": "WARN",
             "action": "启动清库与促销"},
        ],
        "boundary": [
            {"out_of_scope": "资金审批", "owner": "R03"},
            {"out_of_scope": "定价与促销策略", "owner": "R14"},
        ],
        "priority": ["不断货 > 不压资金 > 采购价格",
                     "低库存与高周转冲突时，先保核心品类供给",
                     "多物料竞争预算时按毛利贡献排序"],
        "sop_steps": [
            "算安全库存：可用 + 在途 vs 日均消耗。",
            "查三单匹配：PO / 收货 / 发票是否一致。",
            "算周转：识别慢动销 SKU。",
            "出补货单：核心品类优先，附到货时间。",
            "自动化：补货触发做成流水线，带人工审批。",
        ],
    },
    "r16": {
        "dir": "r16-warenshi-hr", "name": "蛙人事", "title": "HR / 组织赋能",
        "case_id": "productivity-review",
        "display": "人效评估与编制决策",
        "question": "在册 1 人、人均产值增速 4%、人力成本增速 6%，是加编还是提效？关键岗位是否单点依赖？",
        "artifacts": ["roster", "payroll_input"],
        "skills": ["people", "performance", "recruit", "report"],
        "kpis": [
            {"id": "productivity_gap", "name": "人均产值增速差", "formula": "人均产值增速 − 人力成本增速",
             "unit": "个百分点", "target": "≥ 0", "alert": "转负触发预警"},
            {"id": "single_point", "name": "关键岗位单点依赖数", "formula": "无备份人选的 key role 数",
             "unit": "个", "target": "0", "alert": "≥ 1 立即补备份"},
        ],
        "gates": [
            {"id": "G1", "when": "合同/证照到期未续", "verdict": "BLOCKER",
             "action": "立即整改"},
            {"id": "G2", "when": "薪酬核算差错", "verdict": "BLOCKER",
             "action": "48h 内全量复核"},
            {"id": "G3", "when": "人效增速差转负", "verdict": "WARN",
             "action": "冻结新增编制"},
        ],
        "boundary": [
            {"out_of_scope": "替代业务定编制需求", "owner": "R01/R02"},
            {"out_of_scope": "替代财务算薪酬总额", "owner": "R03"},
        ],
        "priority": ["合规 > 人效 > 编制扩张",
                     "人效转负时先提效，不先加人",
                     "关键岗位单点依赖优先补备份"],
        "sop_steps": [
            "算人效：人均产值与人效增速差。",
            "查合规：合同、证照、社保是否齐全。",
            "盘关键岗位：是否有备份人选与文档。",
            "出编制建议：加编/维持/优化三档，附成本。",
            "闭环：能力模型与培训计划落地。",
        ],
    },
    "r17": {
        "dir": "r17-wazhiwang-automation", "name": "蛙织网", "title": "Automation / 自动化",
        "case_id": "workflow-reliability",
        "display": "自动化流水线吞吐与异常自愈",
        "question": "线索同步工作流 3 节点 1 触发器、悬空边 0，但死信重试已达 3 次，是否继续放量？",
        "artifacts": ["workflow", "audit_log"],
        "skills": ["integration", "webhook", "retry", "audit"],
        "kpis": [
            {"id": "dlq_retry", "name": "死信重试次数", "formula": "同一消息重试计数",
             "unit": "次", "target": "≤ 1", "alert": "> 3 报警停工单"},
            {"id": "dangling", "name": "悬空连线数", "formula": "指向不存在节点的边数",
             "unit": "条", "target": "0", "alert": "≥ 1 禁止发布"},
        ],
        "gates": [
            {"id": "G1", "when": "出现悬空连线或未接失败分支", "verdict": "BLOCKER",
             "action": "禁止发布"},
            {"id": "G2", "when": "凭据明文出现在流程定义", "verdict": "BLOCKER",
             "action": "立即轮换密钥"},
            {"id": "G3", "when": "涉及资金/删除无人工审批", "verdict": "BLOCKER",
             "action": "补审批门"},
        ],
        "boundary": [
            {"out_of_scope": "线上告警与值守", "owner": "R20"},
            {"out_of_scope": "业务规则定义", "owner": "R02/R12"},
        ],
        "priority": ["安全 > 可观测 > 吞吐量",
                     "死信超限时先停流程，不靠加机器硬扛",
                     "涉资金动作一律加人工审批"],
        "sop_steps": [
            "画流程图：节点、触发器、失败分支三件套齐全。",
            "查连线：悬空边清零，异常分支必须有出口。",
            "加重试：指数退避 + 死信队列。",
            "护凭据：密钥走环境变量或密钥库。",
            "上线：先灰度一条业务线，观察 3 天再扩。",
        ],
    },
    "r18": {
        "dir": "r18-washucang-dataeng", "name": "蛙数仓", "title": "DataEng / 数仓架构",
        "case_id": "metric-reconcile",
        "display": "跨表口径对账与数据资产健康度",
        "question": "orders 表 1000 行质量检查通过，但与上游对账差异 0.12%，下游看板是否必须阻断？",
        "artifacts": ["dataset", "data_catalog"],
        "skills": ["quality", "transform", "pipeline", "catalog"],
        "kpis": [
            {"id": "reconcile_diff", "name": "跨表对账差异率", "formula": "|A − B| / A",
             "unit": "%", "target": "≤ 0.05", "alert": "> 0.1 阻断下游"},
            {"id": "freshness", "name": "数据延迟", "formula": "当前时间 − 最新分区时间",
             "unit": "h", "target": "≤ 1", "alert": "> 6 标记不可用"},
        ],
        "gates": [
            {"id": "G1", "when": "对账差异 > 0.1%", "verdict": "BLOCKER",
             "action": "阻断下游消费"},
            {"id": "G2", "when": "主键唯一率 < 99.9%", "verdict": "BLOCKER",
             "action": "停止入仓"},
            {"id": "G3", "when": "血缘缺失", "verdict": "WARN",
             "action": "补血缘后再发布"},
        ],
        "boundary": [
            {"out_of_scope": "业务口径定义权", "owner": "R06/R03"},
            {"out_of_scope": "看板呈现设计", "owner": "R06"},
        ],
        "priority": ["口径一致性 > 新鲜度 > 完整性 > 成本",
                     "对账破线一律阻断，不靠人工解释",
                     "上游变更未通知时先冻结下游"],
        "sop_steps": [
            "查质量：主键唯一、空值率、枚举越界。",
            "查新鲜度：分区时间与调度延迟。",
            "做对账：与上游源表逐字段比对。",
            "补血缘：字段级上下游关系登记。",
            "发布：先影子表并行 3 天，再切主表。",
        ],
    },
    "r19": {
        "dir": "r19-wazhimo-ml", "name": "蛙智模", "title": "ML / 算法模型",
        "case_id": "model-gain",
        "display": "推荐模型增益评估与多样性守护",
        "question": "新召回模型离线 AUC +0.8%，但推荐多样性下降 12%，是否推全量？",
        "artifacts": ["experiment_log", "evaluation"],
        "skills": ["tracking", "evaluation", "release", "monitor"],
        "kpis": [
            {"id": "diversity_drop", "name": "推荐流多样性降幅", "formula": "(基期类目熵 − 本期) / 基期",
             "unit": "%", "target": "≤ 5", "alert": "> 10 重新加权召回"},
            {"id": "gain", "name": "实验组转化增益", "formula": "实验组 CVR − 对照组 CVR",
             "unit": "%", "target": "> 0 且显著", "alert": "显著负向即回滚"},
        ],
        "gates": [
            {"id": "G1", "when": "多样性降幅 > 10%", "verdict": "BLOCKER",
             "action": "重新加权召回，不得推全"},
            {"id": "G2", "when": "实验参数未记录完整", "verdict": "BLOCKER",
             "action": "实验作废"},
            {"id": "G3", "when": "对照组出现显著负向", "verdict": "BLOCKER",
             "action": "立即回滚"},
        ],
        "boundary": [
            {"out_of_scope": "业务指标口径定义", "owner": "R06"},
            {"out_of_scope": "线上容量与稳定性", "owner": "R09/R20"},
        ],
        "priority": ["不劣化 > 增益显著性 > 增益幅度",
                     "多样性破线时先调权重，不硬推",
                     "实验不可复现一律作废"],
        "sop_steps": [
            "锁实验：参数、数据版本、评估集全部记录。",
            "算增益：A/B 显著性 + 置信区间。",
            "看护栏：多样性与负向指标一起看。",
            "小流量验证：5% → 20% → 50%。",
            "归档：模型卡 + 复现步骤 + 失效条件。",
        ],
    },
    "r20": {
        "dir": "r20-washouzhi-sre", "name": "蛙守直", "title": "SRE / 稳定性",
        "case_id": "sla-incident",
        "display": "可用性跌破 SLA 的故障演练复盘",
        "question": "本月可用性 99.93%、RTO 实测 47 分钟，下一次演练该压哪条链路、要不要启动 P0 整改？",
        "artifacts": ["monitor_config", "backup_repo"],
        "skills": ["monitor", "alert", "restore", "postmortem"],
        "kpis": [
            {"id": "sla", "name": "系统可用性", "formula": "(总分钟 − 不可用分钟) / 总分钟",
             "unit": "%", "target": "≥ 99.95", "alert": "跌出 99.95 启动 P0"},
            {"id": "rto", "name": "RTO 实测值", "formula": "演练恢复耗时",
             "unit": "分钟", "target": "≤ 30", "alert": "超时判不可恢复"},
        ],
        "gates": [
            {"id": "G1", "when": "核心路径无探活", "verdict": "BLOCKER",
             "action": "禁止上线"},
            {"id": "G2", "when": "备份不可验证恢复", "verdict": "BLOCKER",
             "action": "视为无备份"},
            {"id": "G3", "when": "RTO 超目标", "verdict": "CRITICAL",
             "action": "立项整改并压缩目标"},
        ],
        "boundary": [
            {"out_of_scope": "业务功能实现", "owner": "R09/R08"},
            {"out_of_scope": "发布决策", "owner": "R01"},
        ],
        "priority": ["可用性 > 恢复速度 > 成本",
                     "SLA 破线立即 P0，先止血再复盘",
                     "演练发现的问题优先于新功能"],
        "sop_steps": [
            "定 SLA：核心路径可用性目标与统计口径。",
            "铺探活：HTTP/TCP 探活 + 业务探活双覆盖。",
            "配告警：分级升级链，P0 直达值班。",
            "做演练：按月恢复演练，记录 RTO/RPO。",
            "复盘：改进项挂责任人与验收时间。",
        ],
    },
}


def write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def build_case(p: dict, steps: list | None = None) -> dict:
    data = {
        "case_id": p["case_id"],
        "display_name": p["display"],
        "description": p["question"],
        "default_question": p["question"],
        "artifact_type": p["artifacts"][0],
        "summary": p["display"],
        "semantic_layer": "semantic_layer.json",
        "experience_dir": "experience",
        "artifacts": p["artifacts"],
        "skills": p["skills"],
        "required_gates": [g["id"] for g in p["gates"]],
        "scope_boundary": [b["out_of_scope"] for b in p["boundary"]],
    }
    if steps:
        data["steps"] = steps
    return data


STEPS: dict[str, list] = {
    "r01": [{"skill": "intent", "action": "brief", "input": "examples/brief.json",
             "expect": {"gate": "G1", "expect": "brief_fields 非空且 option_count ≥ 2"}}],
    "r02": [{"skill": "schedule", "action": "wbs", "input": "examples/wbs.json",
             "expect": {"item_count": 5, "total_cost": 4.0}}],
    "r03": [{"skill": "cfo", "action": "runway", "input": "examples/cfo_runway.json",
             "expect": {"burn_multiple": 5.03, "trigger_count": 4}}],
    "r04": [{"skill": "artifact", "action": "verify", "input": "examples/artifact_verify.json",
             "expect": {"verdict": "COMPLETE", "artifact_count": 2}}],
    "r05": [{"skill": "sizing", "action": "size", "input": "examples/sizing_size.json",
             "expect": {"verdict": "PASS", "variance": 0.0}}],
    "r07": [{"skill": "prd", "action": "prd", "input": "examples/prd.json",
             "expect": {"passed_gates": 1}}],
    "r08": [{"skill": "slice", "action": "slice", "input": "examples/slice.json",
             "expect": {"verdict": "PASS", "artifact_type": "landing"}}],
    "r09": [{"skill": "testing", "action": "suites", "input": "examples/testing_suites.json",
             "expect": {"coverage": 0.87, "skipped": 0}}],
    "r10": [{"skill": "logo", "action": "logo", "input": "examples/logo.json",
             "expect": {"verdict": "PASS", "tests_passed": 3}}],
    "r11": [{"skill": "copy", "action": "article", "input": "examples/article.json",
             "expect": {"verdict": "PASS", "forbidden_count": 0}}],
    "r12": [{"skill": "diagnose", "action": "diagnose", "input": "examples/diagnose.json",
             "expect": {"verdict": "PASS", "signal_count": 4}}],
    "r13": [{"skill": "health", "action": "health", "input": "examples/health.json",
             "expect": {"avg_health": 66.4, "at_risk_count": 1}}],
    "r14": [{"skill": "order", "action": "order", "input": "examples/order.json",
             "expect": {"payment_status": "captured", "total": 1046.0}}],
    "r15": [{"skill": "inventory", "action": "item", "input": "examples/item.json",
             "expect": {"verdict": "PASS"}}],
    "r16": [{"skill": "people", "action": "employee", "input": "examples/employee.json",
             "expect": {"employee_count": 1, "status": "Active"}}],
    "r17": [{"skill": "integration", "action": "workflow", "input": "examples/workflow.json",
             "expect": {"dangling_edges": 0, "node_count": 3}}],
    "r18": [{"skill": "quality", "action": "check", "input": "examples/quality_check.json",
             "expect": {"verdict": "PASS", "row_count": 1000}}],
    "r19": [{"skill": "tracking", "action": "run", "input": "examples/tracking_run.json",
             "expect": {"metric_count": 3, "param_count": 3}}],
    "r20": [{"skill": "monitor", "action": "monitor", "input": "examples/monitor.json",
             "expect": {"verdict": "PASS", "monitor_count": 1}}],
}


def build_semantic(p: dict) -> dict:
    terms = []
    for k in p["kpis"]:
        terms.append({
            "term": k["id"],
            "meaning": f"{k['name']} = {k['formula']}（单位 {k['unit']}，"
                       f"目标 {k['target']}，越界判定：{k['alert']}）",
            "source": "configs/ 阈值外置定义",
        })
    for g in p["gates"]:
        terms.append({
            "term": g["id"],
            "meaning": f"门禁：{g['when']} → {g['verdict']}，处置 {g['action']}",
            "source": "semantic_layer.gates",
        })
    facts = {k["id"]: {"name": k["name"], "formula": k["formula"],
                       "unit": k["unit"], "target": str(k["target"]),
                       "alert": k["alert"]} for k in p["kpis"]}
    role = p["dir"][:3]
    # r02 的案例校验器要求 terms 为「术语 → 释义」映射，其余角色要求为列表。
    terms_field = ({t["term"]: t["meaning"] for t in terms} if role == "r02" else terms)
    return {
        "_note": (f"{p['name']}（{p['title']}）业务语义层：指标口径 + 门禁 + 边界 + 决策顺序。"
                  "全部阈值可在 configs/ 内覆盖，改口径不改代码。"),
        "role": role,
        "case_id": p["case_id"],
        "artifact_type": p["artifacts"][0],
        "terms": terms_field,
        "facts": facts,
        "kpis": p["kpis"],
        "gates": p["gates"],
        "boundary": p["boundary"],
        "scope_boundary": [b["out_of_scope"] for b in p["boundary"]],
        "decision_order": p["priority"],
    }


def build_sop_md(p: dict) -> str:
    lines = [
        f"# SOP：{p['display']}（{p['dir'][:3].upper()} {p['name']}）",
        "",
        "## 1. 逻辑导图",
        "",
        "```text",
        f"[异常/诉求输入] → [L1 数据与证据真实性] → [L2 维度下钻：{p['kpis'][0]['name']}]",
        "                → [L3 外部锚点对齐] → [决策指令] → [护栏熔断] → [阶梯灰度]",
        "```",
        "",
        "## 2. 核心指标口径",
        "",
        "| 指标 | 公式 | 单位 | 目标 | 告警 |",
        "| :--- | :--- | :---: | :---: | :--- |",
    ]
    for k in p["kpis"]:
        lines.append(f"| {k['name']} | `{k['formula']}` | {k['unit']} | {k['target']} | {k['alert']} |")
    lines += ["", "## 3. 分步诊断动作", ""]
    for i, s in enumerate(p["sop_steps"], 1):
        lines.append(f"{i}. {s}")
    lines += ["", "## 4. 门禁（不满足即阻断）", "",
              "| 编号 | 触发条件 | 判定 | 处置 |", "| :---: | :--- | :---: | :--- |"]
    for g in p["gates"]:
        lines.append(f"| {g['id']} | {g['when']} | {g['verdict']} | {g['action']} |")
    lines += ["", "## 5. 归因路径", "",
              "- **L1 数据层**：先排除脏数据、断流、重复计数，确认是真实异动。",
              f"- **L2 经营层**：按维度下钻，锁定贡献度 ≥70% 的因子（本角色主维度见 KPI 表）。",
              f"- **L3 商业层**：对齐外部锚点，区分内因外因；未接入外部数据时只声明口径，不虚构大盘数字。",
              "", "## 6. 禁用词与反例", "",
              "- ❌「大幅提升」「表现良好」「值得期待」等无数据锚定的形容词。",
              "- ❌ 只给建议不给阈值；只给阈值不给回滚动作。",
              "- ❌ 把历史个案当通用结论，不做样本量说明。",
              ""]
    return "\n".join(lines)


def build_rules_md(p: dict) -> str:
    lines = [f"# {p['case_id']} 优先级规则（多门禁同时报警时）", ""]
    for i, r in enumerate(p["priority"], 1):
        lines.append(f"{i}. {r}")
    lines.append("")
    return "\n".join(lines)


def build_summaries_md(p: dict) -> str:
    lines = [f"# {p['case_id']} 好的决策摘要（一句话 = 判断 + 依据 + 数字）", ""]
    for i, k in enumerate(p["kpis"], 1):
        lines.append(f"{i}. {k['name']}：目标 {k['target']}{k['unit']}，"
                     f"越界即「{k['alert']}」——结论必须带这条线。")
    lines.append(f"{len(p['kpis']) + 1}. 结论必须区分「真实异动」与「脏数据/断流」，"
                 "并给出下一步动作与责任人。")
    lines.append("")
    return "\n".join(lines)


def build_thresholds(p: dict) -> dict:
    return {
        "_note": (f"{p['case_id']} 案例级阈值：覆盖角色全局阈值，未列出的沿用以 "
                  "experience/thresholds.json 为底。"),
        "kpis": {k["id"]: {"name": k["name"], "formula": k["formula"],
                           "unit": k["unit"], "target": k["target"],
                           "alert": k["alert"]} for k in p["kpis"]},
        "gates": {g["id"]: {"when": g["when"], "verdict": g["verdict"],
                            "action": g["action"]} for g in p["gates"]},
    }


def build_config(p: dict) -> dict:
    return {
        "_note": (f"{p['name']}（{p['title']}）运行配置：阈值/维度/数据源外置，"
                  "改规则不改代码（META-001 Stage 3）。"),
        "role": p["dir"][:3],
        "language": "zh",
        "enable_cache": True,
        "enable_vector": False,
        "report": {
            "engine": "agents/shared/report_engine.py",
            "generator": "agents/shared/report_generator.py",
            "doc_type": p["title"],
            "formats": ["html", "md"],
            "sections": ["决策指令", "KPI 格栅", "三级归因", "护栏熔断", "灰度+下一步"],
        },
        "kpis": p["kpis"],
        "gates": p["gates"],
        "guardrails": [
            {"dim": k["name"], "metric": k["name"], "base": str(k["target"]),
             "threshold": k["alert"]} for k in p["kpis"]
        ],
        "data_sources": [
            {"name": "examples/", "type": "local_json", "permission": "read_only",
             "note": "本轮真实执行所用输入，报告页脚记录 SHA256"},
        ],
        "case": p["case_id"],
    }


def main() -> int:
    dry = "--dry-run" in sys.argv
    created = 0
    for rid, p in PROFILES.items():
        role_root = os.path.join(AGENTS, p["dir"])
        case_root = os.path.join(role_root, "cases", p["case_id"])
        targets = {
            os.path.join(case_root, "case.json"): build_case(p, STEPS.get(rid)),
            os.path.join(case_root, "semantic_layer.json"): build_semantic(p),
            os.path.join(case_root, "experience", "thresholds.json"): build_thresholds(p),
            os.path.join(role_root, "configs", f"{rid}.json"): build_config(p),
        }
        texts = {
            os.path.join(case_root, "experience", "priority_rules.md"): build_rules_md(p),
            os.path.join(case_root, "experience", "good_summaries.md"): build_summaries_md(p),
            os.path.join(role_root, "cases", f"{p['case_id']}.md"): build_sop_md(p),
        }
        cfg = os.path.join(role_root, "configs", f"{rid}.json")
        for path, data in targets.items():
            if dry:
                print(f"[DRY] json {path}")
            else:
                write_json(path, data)
        for path, text in texts.items():
            if dry:
                print(f"[DRY] md   {path}")
            else:
                write_text(path, text)
        created += 1
    print(f"--- {'预演' if dry else '已生成'} {created} 个角色的认知注入资产")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
