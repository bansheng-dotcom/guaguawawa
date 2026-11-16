# -*- coding: utf-8 -*-
"""把 20 角色领域包里的 120 条方法，映射到现有技能/动作。

原则：
1. 已有技能能覆盖的，必须映射到「角色 · 技能 · 动作」，不另造实现；
2. 只能部分覆盖的，标 partial，并写清缺什么；
3. 没有对应技能的，标 new，写清为什么必须新增、落到哪；
4. 映射必须可校验：技能/动作在 `knowledge/skills_inventory.json` 里不存在就 FAIL。

输出：knowledge/roles/skill_map.json
运行：python scripts/build_skill_map.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

ROOT = Path(__file__).resolve().parent.parent
INV = ROOT / "knowledge" / "skills_inventory.json"
OUT = ROOT / "knowledge" / "roles" / "skill_map.json"

# (技能角色, 技能, 动作, fit, 说明)
# fit: exact=技能已做同一件事；partial=同域但需扩字段/口径；new=现有技能没有
MAP: Dict[str, Dict[str, Tuple[str, str, str, str, str]]] = {
    "r01": {
        "战略内核": ("r01", "decide", "", "partial", "决策卡可承载诊断/方针/动作，需补战略内核模板"),
        "五力": ("r05", "industry", "", "partial", "行业分析技能可承载，需补五力打分表"),
        "价值链": ("r05", "business", "", "partial", "商业模式技能可承载，需补逐段加价"),
        "情景规划": ("r05", "scenario", "", "exact", "情景技能已做两轴四情景"),
        "取舍矩阵": ("r01", "decide", "", "partial", "决策卡可承载，需补做/不做/何时做"),
        "北极星与护栏": ("r01", "decompose", "", "partial", "任务卡可承载指标树，需补护栏"),
    },
    "r02": {
        "约束理论": ("r02", "capacity", "", "partial", "产能技能可算瓶颈，需补鼓-缓冲-绳"),
        "价值流图": ("r02", "process", "", "partial", "流程技能可画价值流，需补增值比"),
        "OEE": ("r02", "capacity", "", "partial", "产能技能可算，需补可用率/性能/良率"),
        "标准作业": ("r02", "schedule", "", "exact", "排程技能已做节拍与作业顺序"),
        "鼓-缓冲-绳": ("r02", "schedule", "", "partial", "排程可承载，需补缓冲与投料控制"),
        "排队模型": ("r02", "queue", "", "exact", "排队技能已做等待时间"),
    },
    "r03": {
        "杜邦分解": ("r03", "financial", "", "partial", "财务技能可算比率，需补三因子分解"),
        "现金流折现": ("r03", "cfo", "", "partial", "CFO 技能可承载，需补 WACC 与终值"),
        "三表勾稽": ("r03", "financial", "", "exact", "财务技能已做三表勾稽"),
        "敏感性/情景": ("r03", "risk", "", "exact", "风险技能已做敏感性"),
        "单位经济": ("r03", "cfo", "", "partial", "CFO 可承载，需补单位定义"),
        "营运资金周期": ("r03", "financial", "", "partial", "财务技能可算，需补 DSO/DIO/DPO"),
    },
    "r04": {
        "证据链": ("r04", "facts", "trace", "exact", "facts trace 已做来源追踪"),
        "反例测试": ("r04", "criteria", "review", "partial", "评审判据可承载，需补反例样本"),
        "抽样": ("r04", "artifact", "", "new", "现有评审技能无 Wilson 抽样，需新增"),
        "交叉复核": ("r04", "facts", "check", "exact", "facts check 已做交叉核对"),
        "评分卡": ("r04", "criteria", "review", "partial", "判据可承载，需补权重与证据等级"),
        "红队": ("r04", "criteria", "delta", "partial", "差异评审可承载，需补指定反方"),
    },
    "r05": {
        "五力": ("r05", "industry", "", "exact", "行业技能已做五力"),
        "PESTEL": ("r05", "scenario", "", "partial", "情景技能可承载，需补六类外部变量"),
        "规模三路径": ("r05", "sizing", "", "exact", "规模技能已做 TAM/SAM/SOM 多路径"),
        "集中度": ("r05", "industry", "", "partial", "行业技能可承载，需补 CR/HHI"),
        "价值链": ("r05", "business", "", "exact", "商业模式技能已做价值链"),
        "情景": ("r05", "scenario", "", "exact", "情景技能已做两轴四情景"),
    },
    "r06": {
        "量价/结构归因": ("r06", "rootcause", "decompose", "partial", "贡献分解可承载，需补率效应/结构效应"),
        "DiD": ("r06", "did", "", "exact", "DID 技能已做 2×2/TWFE/事件研究/安慰剂"),
        "A/B 检验": ("r06", "abtest", "", "exact", "A/B 技能已做 lift/显著性/SRM"),
        "回归": ("r06", "regression", "", "exact", "回归技能已做 OLS/Logit/聚类 SE"),
        "队列留存": ("r06", "explore", "cohort", "exact", "explore cohort 已做留存矩阵"),
        "弹性": ("r06", "elasticity", "", "exact", "弹性技能已做 log-log OLS"),
    },
    "r07": {
        "JTBD": ("r07", "discover", "", "partial", "发现技能可承载，需补 JTBD 访谈模板"),
        "机会解决方案树": ("r07", "ost", "", "exact", "OST 技能已做机会-方案树"),
        "RICE": ("r07", "rice", "", "exact", "RICE 技能已做四因子打分"),
        "用户故事地图": ("r07", "prd", "", "partial", "PRD 技能可承载，需补任务链"),
        "漏斗": ("r07", "metrics", "", "partial", "指标技能可承载，需补漏斗"),
        "留存": ("r07", "metrics", "", "partial", "指标技能可承载，需补队列"),
    },
    "r08": {
        "假设卡": ("r08", "slice", "mvp", "partial", "MVP 切片可承载，需补假设/判据字段"),
        "MVP 切片": ("r08", "slice", "mvp", "exact", "slice mvp 已做最小切片"),
        "预注册": ("r08", "qa", "", "new", "现有技能无预注册实验协议，需新增"),
        "五天冲刺": ("r08", "prototype", "", "partial", "原型技能可承载，需补五天节奏"),
        "漏斗": ("r08", "qa", "", "partial", "QA 可承载验证漏斗，需补转化"),
        "停止规则": ("r07", "decision", "", "partial", "产品决策技能可承载，需补杀死标准"),
    },
    "r09": {
        "契约测试": ("r09", "testing", "", "exact", "测试技能已做契约测试"),
        "分层架构": ("r09", "spec", "", "partial", "规格技能可承载，需补分层图"),
        "性能预算": ("r09", "ops", "", "partial", "运维技能可承载，需补预算阈值"),
        "可观测性": ("r09", "ops", "", "exact", "运维技能已做日志/指标/追踪"),
        "灰度发布": ("r09", "ops", "", "partial", "运维技能可承载，需补分批策略"),
        "技术债台账": ("r09", "spec", "", "partial", "规格技能可承载，需补债务/利息"),
    },
    "r10": {
        "设计令牌": ("r10", "designsys", "audit", "exact", "设计系统审计已做令牌"),
        "对比度": ("r10", "brandcheck", "check", "exact", "品牌检查已做对比度"),
        "栅格与间距": ("r10", "uiux", "ux", "partial", "UX 技能可承载，需补 8pt 刻度"),
        "五态": ("r10", "designsys", "apply", "partial", "设计系统可承载，需补五态"),
        "可用性测试": ("r10", "uiux", "screen", "partial", "界面技能可承载，需补任务测试"),
        "视觉层级": ("r10", "uiux", "screen", "partial", "界面技能可承载，需补三级层级"),
    },
    "r11": {
        "AIDA": ("r11", "copy", "article", "partial", "文案技能可承载，需补 AIDA 结构"),
        "钩子矩阵": ("r11", "hook", "hook", "exact", "钩子技能已做标题矩阵"),
        "卖点翻译": ("r11", "copy", "article", "partial", "文案技能可承载，需补 FAB"),
        "内容日历": ("r11", "topic", "plan", "exact", "选题技能已做内容计划"),
        "转化文案": ("r11", "copy", "script", "exact", "文案技能已做转化脚本"),
        "渠道适配": ("r11", "platform", "adapt", "exact", "平台技能已做渠道适配"),
    },
    "r12": {
        "AARRR": ("r12", "diagnose", "diagnose", "exact", "增长诊断已做漏斗/渠道"),
        "漏斗": ("r12", "diagnose", "diagnose", "exact", "增长诊断已做漏斗"),
        "队列留存": ("r06", "explore", "cohort", "exact", "跨角色复用留存技能"),
        "RFM": ("r06", "explore", "rfm", "exact", "跨角色复用 RFM"),
        "增量实验": ("r06", "abtest", "", "exact", "跨角色复用 A/B"),
        "渠道归因": ("r12", "revops", "attribution", "exact", "归因技能已做渠道归因"),
    },
    "r13": {
        "健康分": ("r13", "health", "health", "exact", "健康分技能已做四维加权"),
        "续约风险": ("r13", "health", "risk", "exact", "续约风险技能已做"),
        "NPS/CSAT": ("r13", "voc", "survey", "exact", "VOC 技能已做 NPS/CSAT"),
        "队列留存": ("r06", "explore", "cohort", "exact", "跨角色复用留存"),
        "QBR": ("r13", "activity", "log", "partial", "活动技能可承载，需补 QBR 模板"),
        "流失归因": ("r13", "voc", "voc", "partial", "VOC 可承载，需补流失归因编码"),
    },
    "r14": {
        "交易三态": ("r14", "workflow", "state", "exact", "工作流技能已做状态机"),
        "履约漏斗": ("r14", "order", "order", "partial", "订单技能可承载，需补履约漏斗"),
        "选品 ABC": ("r14", "selection", "score", "exact", "选品技能已做评分"),
        "定价带": ("r14", "catalog", "price", "partial", "目录技能可承载，需补价格带"),
        "复购": ("r14", "revenue", "events", "partial", "收入事件可承载，需补复购队列"),
        "退款归因": ("r14", "payment", "refund", "partial", "退款技能可承载，需补归因"),
    },
    "r15": {
        "TCO": ("r15", "tco", "compare", "exact", "TCO 技能已做落地成本"),
        "EOQ": ("r15", "safety-stock", "", "partial", "库存技能可承载，需补 EOQ 公式"),
        "安全库存": ("r15", "safety-stock", "", "exact", "安全库存技能已做 z×σ×√LT"),
        "供应商评分": ("r15", "procurement", "", "partial", "采购技能可承载，需补五维评分"),
        "牛鞭": ("r15", "fulfill-sim", "", "partial", "履约仿真可承载，需补牛鞭"),
        "卡拉杰克矩阵": ("r15", "procurement", "", "partial", "采购技能可承载，需补品类矩阵"),
    },
    "r16": {
        "招聘评分卡": ("r16", "recruit", "", "exact", "招聘技能已做评分卡"),
        "人效模型": ("r16", "people", "", "exact", "人效技能已做人均产出"),
        "编制测算": ("r16", "people", "", "partial", "人效技能可承载，需补工作量法"),
        "离职归因": ("r16", "people", "", "partial", "人效技能可承载，需补归因编码"),
        "OKR": ("r16", "performance", "", "exact", "绩效技能已做 OKR"),
        "九宫格": ("r16", "performance", "", "partial", "绩效技能可承载，需补绩效×潜力"),
    },
    "r17": {
        "流程挖掘": ("r17", "audit", "audit", "partial", "流程审计可承载，需补事件日志"),
        "RPA": ("r17", "integration", "workflow", "exact", "集成技能已做工作流"),
        "幂等/重试": ("r17", "retry", "retry", "exact", "重试技能已做幂等/退避/死信"),
        "编排": ("r17", "integration", "workflow", "exact", "工作流技能已做编排"),
        "SLA": ("r17", "audit", "audit", "partial", "审计可承载，需补 SLA 指标"),
        "异常队列": ("r17", "retry", "errorflow", "exact", "异常流技能已做"),
    },
    "r18": {
        "维度建模": ("r18", "transform", "", "exact", "转换技能已做维度建模"),
        "分层": ("r18", "pipeline", "", "exact", "管道技能已做 ODS/DWD/DWS/ADS"),
        "质量六维": ("r18", "quality", "", "exact", "质量技能已做六维"),
        "血缘": ("r18", "catalog", "", "exact", "目录技能已做血缘"),
        "增量/全量": ("r18", "incremental", "", "exact", "增量技能已做 CDC/拉链"),
        "SCD": ("r18", "transform", "", "partial", "转换技能可承载，需补 SCD 类型"),
    },
    "r19": {
        "交叉验证": ("r19", "evaluation", "", "exact", "评测技能已做交叉验证"),
        "校准": ("r19", "evaluation", "", "partial", "评测技能可承载，需补 ECE/Brier"),
        "漂移": ("r19", "monitor", "", "exact", "监控技能已做漂移"),
        "A/B": ("r06", "abtest", "", "exact", "跨角色复用 A/B"),
        "评测集": ("r19", "eval-ci", "", "exact", "评测 CI 已做回归集"),
        "特征重要性": ("r19", "trace", "", "partial", "追踪技能可承载，需补置换/SHAP"),
    },
    "r20": {
        "SLO/错误预算": ("r20", "slo", "", "exact", "SLO 技能已做错误预算"),
        "故障复盘": ("r20", "postmortem", "", "exact", "复盘技能已做时间线/根因"),
        "容量规划": ("r20", "monitor", "", "partial", "监控技能可承载，需补容量模型"),
        "混沌": ("r20", "dr", "", "partial", "容灾技能可承载，需补混沌注入"),
        "变更管理": ("r09", "ops", "", "partial", "复用工程运维的发布/变更能力"),
        "黄金指标": ("r20", "monitor", "", "exact", "监控技能已做四件套"),
    },
}


def main() -> int:
    inv = json.loads(INV.read_text(encoding="utf-8"))
    out = {"schema": "dsh.skill_map/v1", "source_inventory": "knowledge/skills_inventory.json",
           "roles": {}}
    missing = []
    for role, methods in MAP.items():
        for method, (sr, sk, act, fit, note) in methods.items():
            node = inv.get(sr, {}).get(sk)
            if node is None:
                missing.append(f"{role}.{method} -> {sr}.{sk}（技能不存在）")
                continue
            if act and act not in node.get("actions", []):
                missing.append(f"{role}.{method} -> {sr}.{sk} {act}（动作不存在）")
                continue
            out["roles"].setdefault(role, {})[method] = {
                "skill_role": sr, "skill": sk, "action": act,
                "fit": fit, "note": note,
                "command": f"python guagua.py call {sr} -- {sk}"
                           + (f" {act}" if act else ""),
            }
    # 未映射的方法：标 new，写清为什么
    for p in sorted((ROOT / "knowledge" / "roles").glob("r*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        role = d["role"]
        for m in d["methods"]:
            if m["name"] in out["roles"].get(role, {}):
                continue
            out["roles"].setdefault(role, {})[m["name"]] = {
                "skill_role": "", "skill": "", "action": "",
                "fit": "new",
                "note": "现有技能无对应动作，需按 Move 卡新增并接产线",
                "command": "",
            }
    if missing:
        print("映射失败：")
        for x in missing:
            print(" -", x)
        return 2
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n = sum(len(v) for v in out["roles"].values())
    exact = sum(1 for v in out["roles"].values() for x in v.values() if x["fit"] == "exact")
    partial = sum(1 for v in out["roles"].values() for x in v.values() if x["fit"] == "partial")
    new = sum(1 for v in out["roles"].values() for x in v.values() if x["fit"] == "new")
    print(f"wrote {OUT}：{n} 条方法 | exact {exact} / partial {partial} / new {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
