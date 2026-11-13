# -*- coding: utf-8 -*-
"""数据端口：把「框架说需要什么」和「系统里实际有什么」对上号。

一个端口 = 一份契约（字段）+ 一份样例数据 + 一个装载器。
装载器只做三件事：文件在不在、字段齐不齐、能不能说出「这份数据能满足哪些 needs」。
满足不了的，继续留在报告「数据缺口」里——不假装有。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

ROOT = Path(__file__).resolve().parent.parent
PORT_DIR = ROOT / "datasets" / "ports"

# 端口 → 能满足的 needs（必须与 frames 里的 needs 字符串逐字一致）
PORTS: Dict[str, Dict[str, Any]] = {
    "task_cards": {
        "name": "任务卡与依赖", "file": "task_cards.json",
        "schema": ["tasks"],
        "needs": ["任务卡", "依赖", "依赖状态", "WBS", "关键路径", "人力负载",
                  "任务工时", "排期", "范围", "可并行度", "owner", "验收标准"],
        "owners": ["r01", "r02"],
    },
    "handoff": {
        "name": "交接包与验收", "file": "handoff.json",
        "schema": ["packages"],
        "needs": ["交接包", "验收记录", "交付清单", "文件存在性", "复评记录", "保留清单"],
        "owners": ["r02", "r04"],
    },
    "voc": {
        "name": "VOC 与访谈", "file": "voc.json",
        "schema": ["feedback"],
        "needs": ["VOC", "访谈", "用户分层", "痛度", "行为数据", "现有流程"],
        "owners": ["r07", "r11", "r13"],
    },
    "api_contract": {
        "name": "接口契约", "file": "api_contract.json",
        "schema": ["services"],
        "needs": ["架构图", "模块职责", "接口契约", "调用方", "测试用例", "覆盖率",
                  "压测数据", "P95", "复杂度", "缺陷密度"],
        "owners": ["r09", "r17"],
    },
    "quality_check": {
        "name": "数据质量检查", "file": "quality_check.json",
        "schema": ["tables"],
        "needs": ["质量检查", "空值率", "重复率", "调度记录", "延迟", "血缘", "下游表",
                  "模型分层", "依赖", "增量策略", "历史量"],
        "owners": ["r18"],
    },
    "eval_set": {
        "name": "评测集与门禁", "file": "eval_set.json",
        "schema": ["cases"],
        "needs": ["基线", "主指标", "显著性", "loss 曲线", "超参", "失败样本", "错误类型",
                  "评测集", "评分器", "监控指标", "漂移检测"],
        "owners": ["r19"],
    },
    "slo_backup": {
        "name": "SLO 与备份", "file": "slo_backup.json",
        "schema": ["services"],
        "needs": ["可用性", "错误预算", "事件", "MTTR", "备份记录", "恢复演练", "RPO/RTO",
                  "告警量", "误报率", "状态页", "影响面"],
        "owners": ["r20"],
    },
    "crm": {
        "name": "CRM 与客户健康", "file": "crm.json",
        "schema": ["customers"],
        "needs": ["使用活跃", "工单", "VOC", "合同到期", "四维健康分", "归因", "管道阶段",
                  "加权金额", "SLA 记录", "CSAT", "客户分层", "负责人"],
        "owners": ["r13"],
    },
    "decision_log": {
        "name": "决策库", "file": "decision_log.json",
        "schema": ["decisions"],
        "needs": ["意图", "资源", "依赖", "选项", "可逆性分级", "预算", "人力", "排期",
                  "阈值", "熔断条件", "owner", "验收标准"],
        "owners": ["r01"],
    },
    "requirement_pool": {
        "name": "需求池", "file": "requirement_pool.json",
        "schema": ["items"],
        "needs": ["VOC", "访谈", "行为数据", "用户分层", "痛度", "现有流程", "方案对比",
                  "RICE 输入", "依赖", "北极星", "基线", "目标"],
        "owners": ["r07"],
    },
    "gate_records": {
        "name": "门禁与评审记录", "file": "gate_records.json",
        "schema": ["gates"],
        "needs": ["交付清单", "文件存在性", "L1 存在", "L2 实质", "L3 连通", "门禁执行记录",
                  "反模式扫描", "缺陷清单", "严重度", "复评记录", "保留清单"],
        "owners": ["r04"],
    },
    # ── 以下 5 个：契约已声明、数据待接入（占位为空，不算 ready）──
    "product_spec": {
        "name": "产品需求库 / 埋点", "file": "product_spec.json", "schema": ["items"],
        "needs": ["用户主路径", "依赖接口", "任务拆分", "工时", "成功标准", "杀死标准",
                  "落地页要素", "竞品页面", "回滚方案", "监控项"],
        "owners": ["r08"], "status": "contract",
    },
    "design_system": {
        "name": "Figma / 设计令牌库", "file": "design_system.json", "schema": ["tokens"],
        "needs": ["DESIGN 令牌", "物料色值", "前景/背景色", "字号", "Logo 变体", "像素尺寸",
                  "导出尺寸", "格式清单", "版本对比", "评审意见"],
        "owners": ["r10"], "status": "contract",
    },
    "content_platform": {
        "name": "内容平台后台 / 搜索指数", "file": "content_platform.json", "schema": ["items"],
        "needs": ["搜索量", "竞品内容", "大纲", "标题", "核心词", "埋词位置", "禁词表",
                  "声明要求", "选题分", "排期"],
        "owners": ["r11"], "status": "contract",
    },
    "hr_system": {
        "name": "HR 系统（花名册/考勤/薪酬）", "file": "hr_system.json", "schema": ["employees"],
        "needs": ["人均产出", "人力成本", "招聘漏斗", "到岗周期", "岗位薪酬", "市场分位",
                  "合同", "考勤", "社保", "目标", "评分"],
        "owners": ["r16"], "status": "contract",
    },
    "integration_log": {
        "name": "集成平台投递日志", "file": "integration_log.json", "schema": ["events"],
        "needs": ["API 契约", "Webhook 端点", "成功率", "重试记录", "死信", "映射表",
                  "样例数据", "密钥存放", "轮换记录", "补偿脚本", "回放机制"],
        "owners": ["r17"], "status": "contract",
    },
}


def path_of(port: str) -> Path:
    return PORT_DIR / PORTS[port]["file"]


def load(port: str) -> Dict[str, Any] | None:
    p = path_of(port)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    missing = [k for k in PORTS[port]["schema"] if k not in data]
    return None if missing else data


def valid_ports() -> List[str]:
    """只把「有数据」的端口算作可用；契约占位（空表）不算。"""
    return [k for k in PORTS if is_ready(k)]


def declared_ports() -> List[str]:
    """契约已声明但数据未接入的端口。"""
    return [k for k in PORTS if load(k) is not None and not is_ready(k)]


def is_ready(port: str) -> bool:
    data = load(port)
    if not data:
        return False
    key = (PORTS[port].get("schema") or [""])[0]
    val = data.get(key)
    return isinstance(val, list) and len(val) > 0


def available_needs(ports: Iterable[str] | None = None) -> Set[str]:
    out: Set[str] = set()
    for k in (ports if ports is not None else valid_ports()):
        if load(k) is not None:
            out.update(PORTS[k]["needs"])
    return out


def declared_lookup() -> Dict[str, Dict[str, str]]:
    """need → 声明了它的端口（供报告写“等哪个系统”）。"""
    out: Dict[str, Dict[str, str]] = {}
    for k in declared_ports():
        meta = PORTS[k]
        data = load(k) or {}
        for need in meta["needs"]:
            out[need] = {"port": k, "name": meta["name"],
                         "system": str(data.get("system", meta["name"]))}
    return out


def status() -> List[Dict[str, Any]]:
    rows = []
    for k, meta in PORTS.items():
        ready = is_ready(k)
        loaded = load(k) is not None
        rows.append({"port": k, "name": meta["name"],
                     "state": "ready" if ready else ("declared" if loaded else "absent"),
                     "needs": len(meta["needs"]), "owners": meta["owners"]})
    return rows
